# Demo guide

A script and a safety net for the pitch. The length (assumed 3:00) and format (live or recorded) are not confirmed by the organizers (D-25); adjust once they are.

## Before you go on stage

1. Fresh clone check passed (`SUBMISSION.md`).
2. `make setup`, then `make check` is green.
3. Close heavy apps. The solver takes up to 30 s and shares the CPU (`10-determinism-and-reproducibility.md`).
4. Run `make demo` once and keep its output open. Confirm headline numbers match the README. A fresh 30 s solve can land lower or higher depending on the laptop's load (the stored run is ₹404,432 and 72.0 % fulfilment; an earlier 30 s solve gave ₹442,214 and 83.0 %); the solver stops at its time limit, so the exact plan is not repeatable. Exact figures always come from the stored run. The live demo stays honest if you say which run you are showing.
5. Start `make serve` and open `http://127.0.0.1:8000`. Click "Open the live demo", then "Run the optimiser" once so a result is already on screen.
6. Have `outputs/demo_backup/` and the CLI scoreboard ready. The API reads only `outputs/<run_id>/`, so to show the backup in the dashboard, copy its directories up first (`cp -r outputs/demo_backup/practice__* outputs/`).

## The story in three minutes

| Time | Show | Say |
|---|---|---|
| 0:00 | Landing page (Problem section) | One sentence of the problem: produce rots because decisions ignore shelf life, demand, and trucks together. |
| 0:30 | Dashboard → "2. Today's plan": route map and truck loading list | Batches, markets, time to spare on each delivery. "We only consider shipments that can still be sold." |
| 1:00 | "1. Results": headline, waterfall and ladder | FIFO against FEFO against FreshRoute, on synthetic data, seed 42. "Same simulator scores all of them." |
| 1:45 | "Independent check" panel (Results), then a reason card (Today's plan) | "Zero rule breaks, checked by an independent package." Open one card: why this market and not the runner-up. |
| 2:15 | Replan: "break it live" | "3. What if something breaks?". Invite a judge to click any road on the map, or one of the road buttons under "Or close a road from this list". That closes the road for 12 h from hour 8. After a few seconds, the road turns red (the replan stopped using it), the batches move, and the narration says what changed against keeping the old plan (other events: pick one and press "Re-plan now"). Say: "Shipments already on the road stay frozen; HiGHS repairs the rest under a 2 s cap, starting from the old plan." |
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
| Numbers differ from README | Expected after a fresh solve (the 30 s limit makes it load-dependent). Do not improvise: quote the README / `demo_backup` figures and say which run they came from, or copy the backup in (step 6) |
