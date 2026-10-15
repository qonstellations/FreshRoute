# Demo guide

A script and a safety net for the pitch. The length (assumed 3:00) and format (live or recorded) are not confirmed by the organizers (D-25); adjust once they are.

## Before you go on stage

1. Fresh clone check passed (`SUBMISSION.md`).
2. `make setup`, then `make check` is green.
3. Close heavy apps. The solver takes up to 30 s and shares the CPU (`10-determinism-and-reproducibility.md`).
4. Run `make demo` once and keep its output open. Confirm headline numbers match the README.
5. Start `make serve` and open `http://127.0.0.1:8000`. Run one plan so a result is already on screen.
6. Have `outputs/demo_backup/` and the CLI scoreboard ready.

## The story in three minutes

| Time | Show | Say |
|---|---|---|
| 0:00 | Landing page | One sentence of the problem: produce rots because decisions ignore shelf life, demand, and trucks together. |
| 0:30 | Plan view | Batches, markets, shelf life ticking down. "We only consider shipments that can still be sold." |
| 1:00 | Scoreboard and waterfall | FIFO against FEFO against FreshRoute, on synthetic data, seed 42. "Same simulator scores all of them." |
| 1:45 | Validator panel and a reason card | "Zero violations, checked by an independent package." Open one card: why Pune and not Delhi. |
| 2:15 | Replan: "break it live" | Dashboard → What-if. Invite a judge to click any road on the map, or one of the "Close a road" buttons under it. That closes the road for 12 h from hour 8. After a few seconds, the road turns red (the replan stopped using it), the batches move, and the narration says what changed against keeping the old plan. Say: "Shipments already on the road stay frozen; HiGHS repairs the rest under a 2 s cap, starting from the old plan." |
| 2:45 | Close | Limits and next steps. |

## Say, and do not say

Say: "synthetic", "measured on the practice scenario with seed 42", "the solver decides, the simulator measures".

Do not say: projected rubric scores; "a year" about the ₹5,921 crore tomato loss; any replan time you did not measure that day; that discounts drove the practice result (FreshRoute ships no markdown).

## When things go wrong

| Problem | Do this |
|---|---|
| Solver slow | Wait up to 30 s; if no result, say the fallback exists and show `outputs/demo_backup/` |
| UI blank or crashed | Run `make demo` in the terminal and present the CLI scoreboard |
| Port 8000 busy | Stop the dev API, then rerun `make serve` |
| Wi-Fi gone | Nothing needs it; the demo is fully local |
| Numbers differ from README | Do not improvise; quote the README / `demo_backup` figures and say which run they came from |
