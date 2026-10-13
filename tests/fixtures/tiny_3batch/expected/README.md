# tiny_3batch: hand-computed expected outputs (F-04)

Rules used: ARCHITECTURE section 7 (cost model, usable life), section 13 (simulator), DECISIONS "Default rule"
(absolute windows, dispatch_h 5, carry-over valued 0, origin handling 0, no markdown => empty `discounts.csv`).
Files here: `plan.csv`, `trips.csv`, `discounts.csv` (header only), `metrics.json` (machine-readable numbers).
Tomato spoilage cost per kg = 15 + 2 - 3 = 14. Onion = 12 + 1 - 4 = 9.

## 1. Feasibility (usable life = RSL - wait*decay(20C) - travel*decay(10C) - handling)
decay(20C) = 1 (ref 20C); decay(10C) = 2^((10-20)/10) = 0.5; wait = 5 - 0 = 5 h; handling = 2 h; min sell window 24 h.

| Shipment | Batch -> Dest | RSL | travel | calc | usable | >= 24 |
|---|---|---|---|---|---|---|
| S0001 | B1 -> D1 | 100 | 12 | 100 - 5 - 6 - 2 | 87 | yes |
| S0002 | B3 -> D1 | 400 | 12 | 400 - 5 - 6 - 2 | 387 | yes |
| S0003 | B2 -> D2 | 60 | 18 | 60 - 5 - 9 - 2 | 44 | yes |
| S0004 | B3 -> D2 | 400 | 18 | 400 - 5 - 9 - 2 | 384 | yes |

Arrival: D1 5 + 12 = 17 h, D2 5 + 18 = 23 h, both inside window [0, 72]; both day 0.
Trips: D1 700 kg, D2 600 kg (both <= 2000 kg); 2 trips <= max_trips_day 2; receiving 700 <= 2000, 600 <= 1500.
Batches: B1 400/1000, B2 350/500, B3 300+250 = 550/800, all within qty.

## 2. Simulation (horizon 3 days, only day 0 has stock; each lot is sold out on day 0)
handling_loss = frac x arrived; sold = min(arrived - loss, demand p50 of day 0) and demand >= on-hand everywhere.

| Lot | arrived | loss | on hand = sold | price | gross |
|---|---|---|---|---|---|
| D1 tomato (B1) | 400 | 2.5% = 10 | 390 | 30 | 11700 |
| D1 onion (B3) | 300 | 1% = 3 | 297 | 20 | 5940 |
| D2 tomato (B2) | 350 | 2.5% = 8.75 | 341.25 | 32 | 10920 |
| D2 onion (B3) | 250 | 1% = 2.5 | 247.5 | 22 | 5445 |

Sold = 390 + 297 + 341.25 + 247.5 = 1275.75. Handling loss = 10 + 3 + 8.75 + 2.5 = 24.25.
Gross = 11700 + 5940 + 10920 + 5445 = 34005; discount_cost 0; revenue 34005.

## 3. Origin stock (horizon end = 72 h)
Unshipped: B1 600, B2 150, B3 250 (total 1000). Origin expiry = available_from + RSL/decay(20C) = RSL:
B1 100 > 72 carry-over; B2 60 <= 72 **expired 150**; B3 400 > 72 carry-over. Carry-over = 600 + 250 = 850.
Spoiled = 24.25 + 0 + 150 = 174.25 kg. Mass: 1275.75 + 174.25 + 850 = 2300 = supply (1300 shipped + 1000 unshipped).
spoilage_pct = 174.25 / 2300 x 100 = 7.5760869...

## 4. Economics
- Transport = fixed 2000 + 2500 = 4500; variable 700 x 2.0 + 600 x 2.5 = 1400 + 1500 = 2900; total **7400**.
- Handling = 700 x 1.0 + 600 x 1.5 = 700 + 900 = **1600** (on delivered kg, loss included).
- Spoilage cost: tomato kg 10 + 8.75 + 150 = 168.75 x 14 = 2362.5; onion 3 + 2.5 = 5.5 x 9 = 49.5; total **2412**.
- Net = 34005 - 7400 - 1600 - 2412 = **22593**.

## 5. Service metrics
Base demand over 3 days: D1 tomato 1200, D1 onion 900, D2 tomato 1050, D2 onion 750 = 3900.
Fulfillment = 1275.75 / 3900 = 32.7115...%. D1 fill = (390 + 297)/2100 = 32.7143%; D2 fill = (341.25 + 247.5)/1800 = 32.7083% (min).
Trips: utilization 700/2000 = 35%, 600/2000 = 30%, mean 32.5%.
Shipment margin_inr_kg (informational) = price - cost_var - handling_cost; priority_score = kg x price / usable life.
