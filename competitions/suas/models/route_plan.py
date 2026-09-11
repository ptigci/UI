"""The route the aircraft is about to fly, as it announced it.

The aircraft plans its own way to each target and publishes the plan before it
uploads it, so the operator sees where the aircraft is going before it goes.
This holds the last plan: the waypoints in order, where it will stop, and
where a fly-through would let go.

A route the operator asked for on a place of their own also carries how far it
has got -- proposed, approved, flying, thrown away or delivered -- because
nothing flies until somebody has looked at it and said yes.
"""

from competitions.suas.config import (
    KEY_ROUTE_ESTIMATED_TIME,
    KEY_ROUTE_HOVER_POINT,
    KEY_ROUTE_ID,
    KEY_ROUTE_LENGTH,
    KEY_ROUTE_POINT_LATITUDE,
    KEY_ROUTE_POINT_LONGITUDE,
    KEY_ROUTE_REASON,
    KEY_ROUTE_RELEASE_POINT,
    KEY_ROUTE_RELEASE_STYLE,
    KEY_ROUTE_STATE,
    KEY_ROUTE_STATION,
    KEY_ROUTE_TARGET_CLASS,
    KEY_ROUTE_TRACK_ID,
    KEY_ROUTE_WAYPOINTS,
)


class RoutePlan:
    """The last route the aircraft said it would fly."""

    def __init__(self) -> None:
        self.route_id: str = ""
        self.track_id = None
        self.target_class: str = ""
        self.release_style: str = ""
        self.waypoints: list[tuple[float, float]] = []
        self.hover_point: tuple[float, float] | None = None
        self.release_point: tuple[float, float] | None = None
        self.length_metres: float = 0.0
        self.estimated_time_seconds: float = 0.0
        self.state: str = ""
        self.reason: str = ""
        self.station: str = ""

    def update_from(self, payload: dict) -> None:
        self.route_id = str(payload.get(KEY_ROUTE_ID, ""))
        self.track_id = payload.get(KEY_ROUTE_TRACK_ID)
        self.target_class = str(payload.get(KEY_ROUTE_TARGET_CLASS, ""))
        self.release_style = str(payload.get(KEY_ROUTE_RELEASE_STYLE, ""))
        self.waypoints = [
            point for point in
            (coordinate_of(waypoint) for waypoint in payload.get(KEY_ROUTE_WAYPOINTS) or [])
            if point is not None
        ]
        self.hover_point = coordinate_of(payload.get(KEY_ROUTE_HOVER_POINT))
        self.release_point = coordinate_of(payload.get(KEY_ROUTE_RELEASE_POINT))
        self.length_metres = number_or_zero(payload.get(KEY_ROUTE_LENGTH))
        self.estimated_time_seconds = number_or_zero(payload.get(KEY_ROUTE_ESTIMATED_TIME))
        self.state = payload.get(KEY_ROUTE_STATE) or ""
        self.reason = payload.get(KEY_ROUTE_REASON) or ""
        self.station = payload.get(KEY_ROUTE_STATION) or ""

    def has_route(self) -> bool:
        return len(self.waypoints) > 1

    def clear(self) -> None:
        self.waypoints = []
        self.hover_point = None
        self.release_point = None
        self.state = ""


def coordinate_of(point) -> tuple[float, float] | None:
    """A ``(latitude, longitude)`` pair out of one point of the plan, or nothing."""
    if not isinstance(point, dict):
        return None
    try:
        return (float(point[KEY_ROUTE_POINT_LATITUDE]),
                float(point[KEY_ROUTE_POINT_LONGITUDE]))
    except (KeyError, TypeError, ValueError):
        return None


def number_or_zero(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
