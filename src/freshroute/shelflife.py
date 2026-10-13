"""Shelf-life decay and usable life at arrival; stub for F-01 (ARCHITECTURE.md section 7)."""


def decay(temp_c: float, ref_temp_c: float, q10: float) -> float:
    """Decay multiplier q10 ** ((temp_c - ref_temp_c) / 10)."""
    raise NotImplementedError


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
    """Remaining life (h) at the destination after storage wait, transit and handling."""
    raise NotImplementedError
