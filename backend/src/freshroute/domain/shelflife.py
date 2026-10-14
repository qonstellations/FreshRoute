"""Shelf-life decay and usable life at arrival (ARCHITECTURE.md section 7, 7.1)."""


def decay(temp_c: float, ref_temp_c: float, q10: float) -> float:
    """Decay multiplier q10 ** ((temp_c - ref_temp_c) / 10)."""
    return q10 ** ((temp_c - ref_temp_c) / 10.0)


def usable_life_at_arrival(
    rsl_h: float,
    wait_h: float,
    travel_h: float,
    handling_h: float,
    store_temp_c: float,
    transit_temp_c: float,
    ref_temp_c: float,
    q10: float,
) -> float:
    """Remaining life (h) at the destination after storage wait, transit and handling.

    May be negative (already expired); callers compare it to min_sell_window_h.
    """
    return (
        rsl_h
        - wait_h * decay(store_temp_c, ref_temp_c, q10)
        - travel_h * decay(transit_temp_c, ref_temp_c, q10)
        - handling_h
    )
