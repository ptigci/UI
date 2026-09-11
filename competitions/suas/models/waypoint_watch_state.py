"""Which mission items start and end the scan, and which one last fired.

The autopilot flies a mission somebody loaded in Mission Planner, and which item
should start the scan is a thing you find out on the day. So the two numbers are
armed from the ground and the aircraft says here what it is armed on, where it
has got to, and which of the two it crossed.

The trigger is kept for the whole flight rather than cleared once it is read.
A trigger that fired and then vanished tells the operator nothing, and a monitor
opened afterwards still has to be able to say whether it fired at all.
"""

from competitions.suas.config import (
    KEY_WATCH_FINISH_INDEX,
    KEY_WATCH_REASON,
    KEY_WATCH_START_INDEX,
    KEY_WATCH_TRIGGERED,
    KEY_WATCH_TRIGGERED_AT,
    KEY_WATCH_TRIGGERED_INDEX,
    KEY_WATCH_WAYPOINT_COUNT,
    KEY_WATCH_WAYPOINT_INDEX,
    WAYPOINT_TRIGGER_FINISH,
    WAYPOINT_TRIGGER_START,
)


class WaypointWatchState:
    """The last waypoint_watch message, one field per fact."""

    def __init__(self) -> None:
        self.start_index: int | None = None
        self.finish_index: int | None = None
        self.waypoint_index: int | None = None
        self.waypoint_count: int | None = None
        self.triggered: str | None = None
        self.triggered_index: int | None = None
        self.triggered_at: float | None = None
        self.reason: str = ""

    def update_from(self, payload: dict) -> None:
        self.start_index = index_or_none(payload.get(KEY_WATCH_START_INDEX))
        self.finish_index = index_or_none(payload.get(KEY_WATCH_FINISH_INDEX))
        self.waypoint_index = index_or_none(payload.get(KEY_WATCH_WAYPOINT_INDEX))
        self.waypoint_count = index_or_none(payload.get(KEY_WATCH_WAYPOINT_COUNT))
        self.triggered = payload.get(KEY_WATCH_TRIGGERED) or None
        self.triggered_index = index_or_none(payload.get(KEY_WATCH_TRIGGERED_INDEX))
        self.triggered_at = number_or_none(payload.get(KEY_WATCH_TRIGGERED_AT))
        self.reason = payload.get(KEY_WATCH_REASON) or ""

    def armed_index(self, trigger: str) -> int | None:
        """The item one of the two is armed on, or None while it is not armed."""
        if trigger == WAYPOINT_TRIGGER_START:
            return self.start_index
        return self.finish_index

    def is_armed(self, trigger: str) -> bool:
        return self.armed_index(trigger) is not None

    def has_triggered(self) -> bool:
        return self.triggered in (WAYPOINT_TRIGGER_START, WAYPOINT_TRIGGER_FINISH)

    def triggered_start(self) -> bool:
        """Whether the one that fired was the start of the scan rather than its end."""
        return self.triggered == WAYPOINT_TRIGGER_START


def index_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def number_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
