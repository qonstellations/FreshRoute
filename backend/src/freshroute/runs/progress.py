"""Show-while-solving (ARCHITECTURE.md section 16.2): the solver offers every better incumbent;
one worker thread scores the newest offer with the normal pipeline and publishes it only if its
simulated net INR beats the last published plan. The solver thread never waits for scoring."""
from __future__ import annotations

import logging
import threading
import time

log = logging.getLogger(__name__)
MIN_GAIN_INR = 0.01  # same tolerance as the ladder waterfall


class Progressive:
    def __init__(self, score, publish, on_progress) -> None:
        """`score(plan_result) -> bundle` (has .net_inr); `publish(bundle)` writes the run
        directory; `on_progress(dict)` reports {version, net_inr, elapsed_s, final}."""
        self._score, self._publish, self._report = score, publish, on_progress
        self._lock, self._wake = threading.Lock(), threading.Event()
        self._slot, self._stop = None, False
        self._best_profit, self._best_net, self.version = float("-inf"), float("-inf"), 0
        self._t0 = time.perf_counter()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="fr-progress")
        self._thread.start()

    def offer(self, make, profit: float) -> None:
        """Called from the solver thread: keep only the newest improving offer."""
        with self._lock:
            if profit <= self._best_profit + MIN_GAIN_INR:
                return
            self._best_profit, self._slot = profit, make
        self._wake.set()

    def close(self) -> int:
        """Drain the last offer, stop the worker; returns the number of versions published."""
        with self._lock:
            self._stop = True
        self._wake.set()
        self._thread.join()
        return self.version

    def finish(self, bundle) -> None:
        """Publish the solver's final plan as the last version."""
        self._publish(bundle)
        self.version += 1
        self._emit(bundle, final=True)

    def _emit(self, bundle, final: bool) -> None:
        self._report({"version": self.version, "net_inr": bundle.net_inr, "final": final,
                      "elapsed_s": round(time.perf_counter() - self._t0, 1)})

    def _loop(self) -> None:
        while True:
            self._wake.wait()
            self._wake.clear()
            with self._lock:
                make, self._slot, stop = self._slot, None, self._stop
            if make is not None:
                try:
                    result = make()
                    bundle = None if result is None else self._score(result)
                    if bundle is not None and bundle.net_inr > self._best_net + MIN_GAIN_INR:
                        self._publish(bundle)
                        self._best_net, self.version = bundle.net_inr, self.version + 1
                        self._emit(bundle, final=False)
                except Exception:  # noqa: BLE001  a bad incumbent must not kill the run
                    log.exception("progressive publish failed")
            if stop and self._slot is None:
                return
