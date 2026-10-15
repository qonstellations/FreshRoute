# 03 · Shelf life and the feasibility pre-filter

This is the central trick of the project. Understand it and the optimizer, the validator and the reason cards all make sense. Formulas: `ARCHITECTURE.md` §7 and §8.

## Shelf life is consumed faster when it is warm

Each batch carries a **remaining shelf life (RSL)** in hours, measured at a reference temperature. Produce ages faster when hot. We model this with a Q10 rule:

```
decay(T) = q10 ^ ((T − ref_temp) / 10)
```

One hour at temperature T uses up `decay(T)` hours of life. With the default `q10 = 2`, ten degrees warmer doubles the ageing speed. A reefer truck at 10 °C against a 20 °C reference ages the load at half speed; an ambient truck at 30 °C ages it at double speed.

`q10 = 2` is a common modelling convention, **not** something we verified per commodity (A-10). That is why the sensitivity run varies it and the UI exposes it as a slider.

## Usable life at arrival

```
usable_life = RSL − wait_h × decay(T_store) − travel_h × decay(T_transit) − handling_h
```

A shipment is acceptable only if `usable_life` is at least the commodity's minimum sell window (so the shop can actually sell it) and the arrival time falls inside the destination's delivery window.

The worked example in `ARCHITECTURE.md` §7.1 is unit-tested. It shows the same batch going to the same destination: fine by reefer, fine by short ambient route, and rejected by long ambient route because only 13 hours of life would remain against a 24-hour window.

## Why we filter before optimizing

We could write "usable life ≥ minimum" as a constraint inside the solver. We do not. `build_arcs` enumerates candidate shipments and deletes the infeasible ones *before* the model exists. This gives three benefits:

1. **Smaller model.** Fewer variables means HiGHS finds a good incumbent in the time limit.
2. **Feasibility by construction.** A shipment that cannot work has no variable, so the solver cannot choose it.
3. **Explanations for free.** Rejected arcs stay in the table with a reason code (`NO_LANE`, `NOT_AVAILABLE`, `RAIL_SLOT`, `WINDOW`, `SHELF_LIFE`, `BEYOND_HORIZON`). The reason cards read those rows to say why a market was *not* chosen.

The price of this approach is that planning uses the median travel time (`travel_h_p50`). Real-world delay is handled afterwards by the stress test (see `08`), not inside the plan.

## What the filter checks

For each (batch, destination, vehicle, day):

1. The batch's origin hub matches the vehicle's origin and a lane exists for that mode.
2. Dispatch is not before the batch or vehicle is available; rail trips snap to the next departure slot.
3. Arrival is within the horizon.
4. Arrival is inside the destination's delivery window (absolute hours, or hour-of-day in `daily` mode).
5. Usable life is at least the minimum sell window.

## Gotchas

- `shelflife.py` and the validator each have their own copy of the usable-life formula on purpose (see `07`). A randomized test checks they agree; if you change one, change both.
- The delivery-window mode (`absolute` vs `daily`) is an open question for the organizers (see `DECISIONS.md`). Both are implemented.
- Dispatch happens at 05:00 by default (`DISPATCH_HOUR`, A-02).
