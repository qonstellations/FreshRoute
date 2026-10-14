"""Generator knobs and tables (ARCHITECTURE.md section 5, A-47..A-50): every named
coefficient the v3 scenario generator uses, with its source note. SYNTHETIC values."""
from __future__ import annotations

import math

GENERATOR_VERSION = "v3"
PRICE_SOURCE = "static_table_generator_v3"
# [team] modal mandi prices, INR/kg, from published Agmarknet aggregates (Farmer.in CC-BY
# ticker + CEDA series, July 2026; keyless, NOT a data.gov.in snapshot).
STATIC_PRICE_INR_KG = {
    "tomato": 28.0, "spinach": 35.0, "banana": 32.0, "mango": 70.0, "onion": 24.0, "potato": 18.0,
}
PRICE_DAY_VOL = {  # [team] sd of the shared daily market move per commodity; onion swings most
    "tomato": 0.06, "spinach": 0.07, "banana": 0.04, "mango": 0.05, "onion": 0.09, "potato": 0.05,
}
PRICE_SPREAD = {  # [team] (min_ratio, max_ratio) of the day's price band
    "tomato": (0.90, 1.12), "spinach": (0.88, 1.15), "banana": (0.90, 1.12),
    "mango": (0.88, 1.15), "onion": (0.75, 1.30), "potato": (0.85, 1.20),
}
# [team] class, base shelf life h (at ref temp), ref C, q10, min sell window h, handling loss %,
# unit cost, disposal, salvage (INR/kg), elasticity, max discount %. Unit cost ~ 55-60 % of the
# mandi modal price (farm-gate share); shelf lives are ambient Indian supply-chain figures, so
# leafy and soft produce expire inside a 2-3 day horizon while onion and potato do not (A-47).
_COMM = {
    "tomato": ("very_high", 144, 20, 2.5, 24, 3.0, 16, 2, 3, 1.0, 35),
    "spinach": ("very_high", 48, 20, 3.0, 12, 4.0, 20, 2, 1, 1.2, 40),
    "banana": ("high", 168, 20, 2.2, 24, 2.0, 18, 2, 5, 0.8, 30),
    "mango": ("high", 144, 25, 2.5, 24, 3.0, 40, 3, 10, 0.8, 30),
    "onion": ("low", 1440, 25, 1.8, 48, 1.0, 14, 1, 4, 0.5, 20),
    "potato": ("low", 1680, 25, 1.8, 48, 1.0, 10, 1, 4, 0.5, 20),
}
# [team] commodity mix ~ NABCONS production shares (potato/onion heavy; spinach has no NABCONS
# row and stays a minor leafy line). Must sum to 1.
_COMM_W = {"tomato": 0.16, "spinach": 0.06, "banana": 0.20, "mango": 0.12,
           "onion": 0.18, "potato": 0.28}
# [team] where each commodity waits at the hub (C): cold room or ambient shed, drawn per batch
STORAGE_TEMP_C = {"tomato": (22.0, 28.0), "spinach": (8.0, 22.0), "banana": (18.0, 22.0),
                  "mango": (26.0, 30.0), "onion": (28.0, 32.0), "potato": (4.0, 25.0)}
RSL_BETA = (5.0, 2.0)  # [team] remaining-life fraction of base ~ Beta(5, 2): mean 0.71
GRADE_A_MIN_FRAC = 0.6  # [team] grade A iff remaining-life fraction >= this (one variable)
RSL_BAND = (0.08, 0.20)  # [team] p10/p90 = rsl * (1 -/+ U(band))
QTY_LOGNORMAL = (math.log(250.0), 0.6)  # [team] batch kg ~ lognormal, median 250 kg
QTY_CLIP_KG = (40.0, 1500.0)

# [team] outlet type -> daily receiving window (hour of day), price premium vs mandi, demand
# scale, receiving headroom over mean daily demand, handling h, handling INR/kg
DEST_TYPE = {
    "mandi": ((2.0, 14.0), 1.00, 1.5, 1.6, 1.0, 1.0),
    "retail_DC": ((4.0, 20.0), 1.20, 1.0, 1.25, 2.0, 1.5),
    "HoReCa": ((6.0, 16.0), 1.35, 0.4, 1.2, 1.0, 2.0),
    "processor": ((0.0, 24.0), 0.75, 0.8, 1.5, 3.0, 0.6),
}
ROAD_FACTOR = 1.3  # [team] road km / great-circle km
ROAD_SPEED_KMH = 40.0  # [team] loaded truck average incl. city stretches
ROAD_LOAD_H = 0.5  # [team] loading + gate time per trip
RAIL_MIN_KM = 200.0  # [team] rail lanes only to destinations this far (great circle)
RAIL_FACTOR, RAIL_SPEED_KMH, RAIL_DWELL_H = 1.2, 45.0, 6.0  # [team] parcel-van service
RAIL_SLOTS = "18|22"
TRAVEL_P90_RATIO = {"road": (1.15, 1.40), "rail": (1.20, 1.60)}  # [team] p90 / p50 draw
TRANSIT_TEMP_C = {"reefer": 12.0, "ambient": 30.0, "rail": 28.0}  # [team] mixed-load reefer
# [team] lane cost: fixed INR/trip = base + per road km; variable INR/kg = base + per road km
LANE_COST = {"reefer": (800.0, 40.0, 0.5, 0.004), "ambient": (500.0, 26.0, 0.4, 0.003),
             "rail": (2500.0, 0.0, 0.9, 0.0015)}
LANE_COST_NOISE = (0.9, 1.1)
VEHICLE_CAP_KG = (1000.0, 3000.0, 5000.0, 9000.0)  # [team] tempo, LCV, 5 t, 9 t truck
VEHICLE_CAP_P = (0.20, 0.35, 0.30, 0.15)
DUTY_H = 16.0  # [team] two-shift day; trips/day = floor(DUTY_H / round trip), at least 1
RAIL_CAP_KG, RAIL_TRIPS_DAY = 10000.0, 1  # one parcel-van booking per hub per day
# [team] demand: total p50 ~ U(ratio) x supply per commodity; destination share ~ type scale x
# lognormal(0, sd), capped at DEST_SHARE_CAP when at least 3 outlets take the commodity;
# daily multiplier AR(1) around 1.
DEMAND_SUPPLY_RATIO = (0.9, 1.1)
DEST_SHARE_SD = 0.35
DEST_SHARE_CAP = 0.35
DEMAND_AR = (0.5, 0.08)  # (persistence, shock sd)
_Q = {"very_high": (0.70, 1.35), "high": (0.75, 1.30), "low": (0.85, 1.15)}  # p10/p90 ratios
# [team] held-out hidden-style seeds: never tune against these; practice/small use seed 42.
HIDDEN_SEEDS = (101, 102, 103, 104, 201, 202, 203, 204, 205, 206)

# name -> (seed, n_batches, n_dests, days, n_vehicles, event rows)
COMMITTED = {
    "practice": (42, 200, 8, 3, 6, None),
    "small": (42, 30, 3, 2, 2, None),
    # hidden-style suite: scale ladder, one scenario per event type, edge cases as data
    "hidden_small": (101, 30, 3, 2, 2, None),
    "hidden_practice": (102, 200, 8, 3, 4, None),
    "hidden_3x": (103, 600, 8, 3, 8, None),
    "hidden_10x": (104, 2000, 8, 3, 30, None),
    "hidden_ev_delay": (201, 200, 8, 3, 4, [("EV1", "route_delay", "HUB1|D1|reefer", 6.0, 8.0)]),
    "hidden_ev_capacity": (202, 200, 8, 3, 4, [("EV1", "capacity_drop", "vehicle:V1", 0.5, 8.0)]),
    "hidden_ev_demand": (203, 200, 8, 3, 4, [("EV1", "demand_spike", "dest:D2|*", 1.5, 8.0)]),
    "hidden_ev_price": (204, 200, 8, 3, 4, [("EV1", "price_shock", "dest:D3|tomato", 0.8, 8.0)]),
    "hidden_ev_order": (205, 200, 8, 3, 4, [("EV1", "new_order", "dest:D2|mango", 500.0, 8.0)]),
    "hidden_edge": (206, 30, 3, 2, 2, None),
}
