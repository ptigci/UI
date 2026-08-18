"""Lap counting, and what the laps are currently worth.

Section 3.2.2 makes a lap count only if it is complete, flown in order, fully
autonomous, with no intermediate manual takeover or landing. Section 3.7 sends
the aircraft back to the start of the lap on any transition to manual flight.
Section 3.2.2 also freezes the count the moment the aircraft enters the Search
Boundary for a task.

The aircraft counts the laps; this holds what it reported so the widgets can
show it and so a disputed count has something behind it. The scoring arithmetic
lives here too, because the operator's only real in-flight decision is whether
another lap is worth the clock.
"""

from competitions.suas.config import (
    ENDURANCE_LAP_DIVISOR,
    ENDURANCE_MAXIMUM_POINTS,
    KEY_LAP_INVALID_REASON,
    KEY_LAP_VALID,
    KEY_LAP_WAYPOINT_INDEX,
    KEY_LAPS_COMPLETED,
    KEY_LAPS_LOCKED,
    KEY_MISSION_STATE,
    MAXIMUM_LAPS,
    MODE_AUTONOMOUS,
)


class LapState:
    """Completed laps, the lap in progress, and whether it still counts."""

    def __init__(self) -> None:
        self.laps_completed = 0
        self.lap_waypoint_index: int | None = None
        self.lap_valid = True
        self.lap_invalid_reason: str | None = None
        self.laps_locked = False
        self.mission_phase: str | None = None

    def update_from(self, payload: dict) -> None:
        if KEY_LAPS_COMPLETED in payload:
            self.laps_completed = int_or_zero(payload[KEY_LAPS_COMPLETED])
        if KEY_LAP_WAYPOINT_INDEX in payload:
            self.lap_waypoint_index = int_or_none(payload[KEY_LAP_WAYPOINT_INDEX])
        if KEY_LAP_VALID in payload:
            self.lap_valid = bool(payload[KEY_LAP_VALID])
        if KEY_LAP_INVALID_REASON in payload:
            self.lap_invalid_reason = text_or_none(payload[KEY_LAP_INVALID_REASON])
        if KEY_LAPS_LOCKED in payload:
            self.laps_locked = bool(payload[KEY_LAPS_LOCKED])
        if KEY_MISSION_STATE in payload:
            self.mission_phase = text_or_none(payload[KEY_MISSION_STATE])

    def lap_in_progress(self) -> int:
        """The number of the lap being flown, which is the next one to complete."""
        return self.laps_completed + 1

    def endurance_points(self) -> float:
        return endurance_points_for(self.laps_completed)

    def points_for_one_more_lap(self) -> float:
        """What the next lap adds. The curve is quadratic, so this grows."""
        if self.laps_completed >= MAXIMUM_LAPS:
            return 0.0
        return endurance_points_for(self.laps_completed + 1) - self.endurance_points()

    def autonomy_held(self, mode: str | None) -> bool:
        """A lap is only legal while the autopilot is flying it."""
        if mode is None:
            return False
        return mode == MODE_AUTONOMOUS


def endurance_points_for(laps: int) -> float:
    """3.2.3: 200 * (laps / 10)^2, and no more than ten laps score."""
    counted_laps = min(laps, MAXIMUM_LAPS)
    if counted_laps <= 0:
        return 0.0
    return ENDURANCE_MAXIMUM_POINTS * (counted_laps / ENDURANCE_LAP_DIVISOR) ** 2


def int_or_zero(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def text_or_none(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text
