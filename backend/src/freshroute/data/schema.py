"""Column-name constants for every input table (DATABASE.md section 3), plus the
declarative rules io.py checks at load time (DATABASE.md section 7)."""

COMMODITIES = (
    "commodity", "perishability_class", "base_shelf_life_h", "ref_temp_c", "q10",
    "min_sell_window_h", "handling_loss_pct", "unit_cost_inr_kg", "disposal_cost_inr_kg",
    "salvage_value_inr_kg", "price_elasticity", "max_discount_pct",
)
BATCHES = (
    "batch_id", "commodity", "origin_hub", "qty_kg", "remaining_shelf_life_h", "rsl_p10_h",
    "rsl_p90_h", "storage_temp_c", "quality_grade", "available_from_h",
)
DESTINATIONS = (
    "dest_id", "name", "type", "receive_cap_kg_day", "handling_time_h", "handling_cost_inr_kg",
    "window_open_h", "window_close_h",
)
DEMAND = (
    "dest_id", "commodity", "day", "demand_kg_p50", "demand_kg_p10", "demand_kg_p90",
    "event_flag",
)
PRICES = ("dest_id", "commodity", "day", "price_inr_kg", "price_min", "price_max")
LANES = (
    "origin", "dest_id", "mode", "travel_h_p50", "travel_h_p90", "cost_fixed_inr_trip",
    "cost_var_inr_kg", "transit_temp_c", "departure_slots",
)
VEHICLES = ("vehicle_id", "origin", "mode", "capacity_kg", "available_from_h", "max_trips_day")
EVENTS = ("event_id", "type", "target", "magnitude", "at_h")
GEO = ("node_id", "node_type", "name", "lat", "lon")  # optional, UI only

# required tables: name -> columns
TABLES = {
    "commodities": COMMODITIES, "batches": BATCHES, "destinations": DESTINATIONS,
    "demand": DEMAND, "prices": PRICES, "lanes": LANES, "vehicles": VEHICLES, "events": EVENTS,
}
OPTIONAL_TABLES = {"geo": GEO}
# columns that may be blank
OPTIONAL_COLUMNS = {
    "batches": ("quality_grade",), "demand": ("event_flag",), "lanes": ("departure_slots",),
}
PKS = {
    "commodities": ("commodity",), "batches": ("batch_id",), "destinations": ("dest_id",),
    "demand": ("dest_id", "commodity", "day"), "prices": ("dest_id", "commodity", "day"),
    "lanes": ("origin", "dest_id", "mode"), "vehicles": ("vehicle_id",),
    "events": ("event_id",), "geo": ("node_id",),
}
ENUMS = {
    ("commodities", "perishability_class"): {"very_high", "high", "low"},
    ("destinations", "type"): {"mandi", "retail_DC", "HoReCa", "processor"},
    ("lanes", "mode"): {"reefer", "ambient", "rail"},
    ("vehicles", "mode"): {"reefer", "ambient", "rail"},
    ("events", "type"): {
        "route_delay", "capacity_drop", "demand_spike", "new_order", "price_shock",
    },
}
# (child table, child column, parent table, parent column)
FKS = (
    ("batches", "commodity", "commodities", "commodity"),
    ("demand", "dest_id", "destinations", "dest_id"),
    ("demand", "commodity", "commodities", "commodity"),
    ("prices", "dest_id", "destinations", "dest_id"),
    ("prices", "commodity", "commodities", "commodity"),
    ("lanes", "dest_id", "destinations", "dest_id"),
)
# (table, low column, high column): low <= high
ORDERED = (
    ("batches", "rsl_p10_h", "remaining_shelf_life_h"),
    ("batches", "remaining_shelf_life_h", "rsl_p90_h"),
    ("demand", "demand_kg_p10", "demand_kg_p50"),
    ("demand", "demand_kg_p50", "demand_kg_p90"),
    ("lanes", "travel_h_p50", "travel_h_p90"),
    ("prices", "price_min", "price_inr_kg"),
    ("prices", "price_inr_kg", "price_max"),
)
NONNEG = (  # (table, column) must be >= 0
    ("batches", "remaining_shelf_life_h"), ("batches", "available_from_h"),
    ("demand", "day"), ("prices", "day"), ("vehicles", "available_from_h"),
    ("vehicles", "max_trips_day"), ("destinations", "receive_cap_kg_day"),
)
POSITIVE = (  # (table, column) must be > 0
    ("batches", "qty_kg"), ("vehicles", "capacity_kg"), ("lanes", "travel_h_p50"),
    ("prices", "price_inr_kg"), ("commodities", "base_shelf_life_h"), ("commodities", "q10"),
)
# percent columns -> fraction columns (conversion happens in io.py only)
PCT_TO_FRAC = {
    "handling_loss_pct": "handling_loss_frac", "max_discount_pct": "max_discount_frac",
}
