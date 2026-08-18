"""Metric on the wire, imperial on the judge's display.

Rule 3.0.6 specifies ground speed in knots and altitude in feet AGL, and
Appendix B wants the waypoint threshold in feet. Everything the aircraft sends
is metric, so the conversion happens once, here, and no widget multiplies by
3.28 on its own.

These are unit definitions, not settings, so they stay in code — the same way
map_projection.py keeps the earth's radius.
"""

FEET_PER_METRE = 3.280839895013123
KNOTS_PER_METRE_PER_SECOND = 1.9438444924406046
MILES_PER_METRE = 0.0006213711922373339


def metres_to_feet(metres: float) -> float:
    return metres * FEET_PER_METRE


def feet_to_metres(feet: float) -> float:
    return feet / FEET_PER_METRE


def metres_per_second_to_knots(metres_per_second: float) -> float:
    return metres_per_second * KNOTS_PER_METRE_PER_SECOND


def metres_to_miles(metres: float) -> float:
    return metres * MILES_PER_METRE
