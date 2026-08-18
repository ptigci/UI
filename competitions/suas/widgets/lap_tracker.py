"""Laps, and whether they still count.

Up to 250 points are arbitrated by a judge sitting next to this screen, so this
widget's job is to be auditable rather than decorative. Section 3.2.2 counts a
lap only if it is complete, in order and fully autonomous; 3.7.6 sends the
aircraft back to the start of the lap on any transition to manual flight. So the
"AUTO held" line is not a nicety — it is the condition that makes the lap legal,
and when it breaks the widget says so in words instead of quietly counting on.

The points line is here because the operator's one real in-flight decision is
whether another lap is worth the clock, and the curve is quadratic.
"""

from PyQt6.QtWidgets import QLabel

from competitions.suas.config import (
    LAP_AUTO_HELD_TEXT,
    LAP_AUTO_LOST_TEXT,
    LAP_CURRENT_MARK,
    LAP_DONE_MARK,
    LAP_INVALID_FORMAT,
    LAP_LOCKED_TEXT,
    LAP_MARKS_CAPTION,
    LAP_NEXT_LAP_FORMAT,
    LAP_PANEL_TITLE,
    LAP_POINTS_FORMAT,
    LAP_PROGRESS_CAPTION,
    LAP_PROGRESS_FORMAT,
    LAP_PROGRESS_WAITING_TEXT,
    LAP_TODO_MARK,
    MAXIMUM_LAPS,
)
from competitions.suas.units import metres_to_feet
from theme import set_role, set_state
from theme.tokens import (
    ROLE_HINT,
    SCALE_TITLE,
    STATE_CRITICAL,
    STATE_OK,
)
from widgets import Card, Readout, StatusPill


class LapTracker(Card):
    """Completed laps, the lap in progress, autonomy, and what it is all worth."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent, LAP_PANEL_TITLE)

        self.autonomy_pill = StatusPill(self)
        self.add_header_widget(self.autonomy_pill)

        self.laps_reading = Readout(LAP_MARKS_CAPTION, SCALE_TITLE, self)
        self.progress_reading = Readout(LAP_PROGRESS_CAPTION, parent=self)
        self.progress_reading.set_value(LAP_PROGRESS_WAITING_TEXT)

        self.points_label = QLabel(self)
        self.next_lap_label = QLabel(self)
        set_role(self.next_lap_label, ROLE_HINT)

        self.invalid_label = QLabel(self)
        set_role(self.invalid_label, ROLE_HINT)
        set_state(self.invalid_label, STATE_CRITICAL)
        self.invalid_label.setWordWrap(True)

        self.add_widget(self.laps_reading)
        self.add_widget(self.progress_reading)
        self.add_widget(self.points_label)
        self.add_widget(self.next_lap_label)
        self.add_widget(self.invalid_label)
        self.add_stretch()

        self.show_autonomy(True)
        self.show_invalid_reason("")

    def show_laps(self, lap_state) -> None:
        self.laps_reading.set_value(
            lap_marks(lap_state.laps_completed, lap_state.laps_locked)
        )
        self.points_label.setText(
            LAP_POINTS_FORMAT.format(
                laps=lap_state.laps_completed, points=lap_state.endurance_points()
            )
        )
        self.next_lap_label.setText(
            LAP_NEXT_LAP_FORMAT.format(points=lap_state.points_for_one_more_lap())
        )
        self.show_invalidation(lap_state)

    def show_progress(self, waypoint_index, waypoint_total, distance_metres) -> None:
        """Distance in feet, because that is the unit the rules and the judge use."""
        if waypoint_index is None or waypoint_total is None or distance_metres is None:
            self.progress_reading.set_value(LAP_PROGRESS_WAITING_TEXT)
            return
        self.progress_reading.set_value(
            LAP_PROGRESS_FORMAT.format(
                index=waypoint_index,
                total=waypoint_total,
                feet=metres_to_feet(distance_metres),
            )
        )

    def show_autonomy(self, autonomy_held: bool) -> None:
        """Losing AUTO is what stops a lap counting, so the whole card says so."""
        if autonomy_held:
            self.autonomy_pill.show_status(LAP_AUTO_HELD_TEXT, STATE_OK)
            self.set_state(STATE_OK)
        else:
            self.autonomy_pill.show_status(LAP_AUTO_LOST_TEXT, STATE_CRITICAL)
            self.set_state(STATE_CRITICAL)

    def show_invalidation(self, lap_state) -> None:
        """A lap that stopped counting is said out loud, never swallowed."""
        if lap_state.lap_valid:
            self.show_invalid_reason("")
            return
        reason = lap_state.lap_invalid_reason
        if reason is None:
            reason = LAP_AUTO_LOST_TEXT
        self.show_invalid_reason(
            LAP_INVALID_FORMAT.format(lap=lap_state.lap_in_progress(), reason=reason)
        )

    def show_invalid_reason(self, reason: str) -> None:
        self.invalid_label.setText(reason)
        self.invalid_label.setVisible(bool(reason))


def lap_marks(laps_completed: int, laps_locked: bool) -> str:
    """One mark per lap: done, in progress, or still available."""
    marks = []
    for lap_number in range(1, MAXIMUM_LAPS + 1):
        if lap_number <= laps_completed:
            marks.append(LAP_DONE_MARK)
        elif lap_number == laps_completed + 1 and not laps_locked:
            marks.append(LAP_CURRENT_MARK)
        else:
            marks.append(LAP_TODO_MARK)

    line = " ".join(marks)
    if laps_locked:
        return f"{line}   {LAP_LOCKED_TEXT}"
    return line
