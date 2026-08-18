"""The 45-minute clock, and the most dangerous number on the display.

Rule 3.1.1 gives 45 minutes covering setup, flight and handing the deliverables
over, and 3.7.1 charges 0.5% of mission demonstration points for every second
past it. One minute over is 30% of everything, so the bar changes state well
before the limit rather than at it.

The clock starts on the judge's word, not on software launch, so starting it is
an explicit press. It keeps counting past the limit and shows the overrun,
because at that point the operator needs to know exactly how bad it is getting.

It is the top bar of the window and the largest type in the interface, which is
the display scale of the shared readout — nothing else on screen uses it.
"""

import time

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from competitions.suas.config import (
    CLOCK_CAPTION,
    CLOCK_FORMAT,
    CLOCK_MINIMUM_HEIGHT,
    CLOCK_OVERRUN_FORMAT,
    CLOCK_PHASE_CAPTION,
    CLOCK_PHASE_FORMAT,
    CLOCK_PHASE_UNKNOWN_TEXT,
    CLOCK_RUNNING_TEXT,
    CLOCK_START_TEXT,
    MISSION_CAUTION_SECONDS,
    MISSION_CRITICAL_SECONDS,
    MISSION_SECONDS,
)
from theme import set_scale, set_surface, set_variant, space_layout
from theme.tokens import (
    AS_APP_BAR,
    SCALE_DISPLAY,
    SCALE_LARGE,
    SCALE_TITLE,
    SPACE_LG,
    SPACE_XL,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
    VARIANT_PRIMARY,
)
from widgets import Readout, StatusPill

SECONDS_PER_MINUTE = 60


class MissionClock(QWidget):
    """Elapsed against 45:00, the current phase, and the button that starts it."""

    clock_started = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        set_surface(self, AS_APP_BAR)
        self.setMinimumHeight(CLOCK_MINIMUM_HEIGHT)

        self.start_monotonic: float | None = None

        self.elapsed_reading = Readout(CLOCK_CAPTION, SCALE_DISPLAY, self)
        self.phase_reading = Readout(CLOCK_PHASE_CAPTION, SCALE_TITLE, self)
        self.phase_reading.set_value(CLOCK_PHASE_UNKNOWN_TEXT)
        self.overrun_pill = StatusPill(self, state=STATE_CRITICAL)
        self.overrun_pill.setVisible(False)

        self.start_button = QPushButton(CLOCK_START_TEXT, self)
        set_variant(self.start_button, VARIANT_PRIMARY)
        set_scale(self.start_button, SCALE_LARGE)
        self.start_button.clicked.connect(self.start)

        clock_layout = QHBoxLayout(self)
        space_layout(clock_layout, SPACE_LG, SPACE_XL)
        clock_layout.addWidget(self.elapsed_reading)
        clock_layout.addWidget(self.phase_reading)
        clock_layout.addWidget(self.overrun_pill)
        clock_layout.addStretch()
        clock_layout.addWidget(self.start_button)

        self.refresh()

    # The clock

    def start(self) -> None:
        """The judge says go; nothing before this moment counts."""
        if self.start_monotonic is not None:
            return
        self.start_monotonic = time.monotonic()
        self.start_button.setText(CLOCK_RUNNING_TEXT)
        self.start_button.setEnabled(False)
        self.clock_started.emit()
        self.refresh()

    def is_running(self) -> bool:
        return self.start_monotonic is not None

    def elapsed_seconds(self) -> float:
        if self.start_monotonic is None:
            return 0.0
        return time.monotonic() - self.start_monotonic

    def remaining_seconds(self) -> float:
        return MISSION_SECONDS - self.elapsed_seconds()

    # Display

    def refresh(self) -> None:
        elapsed = self.elapsed_seconds()
        self.elapsed_reading.set_value(
            CLOCK_FORMAT.format(
                minutes=whole_minutes(elapsed),
                seconds=remaining_seconds_of_minute(elapsed),
                limit_minutes=whole_minutes(MISSION_SECONDS),
                limit_seconds=remaining_seconds_of_minute(MISSION_SECONDS),
            )
        )
        self.show_overrun(elapsed)
        self.elapsed_reading.set_state(state_for(elapsed))

    def show_overrun(self, elapsed_seconds: float) -> None:
        overrun = elapsed_seconds - MISSION_SECONDS
        if overrun <= 0:
            self.overrun_pill.setVisible(False)
            return
        self.overrun_pill.setVisible(True)
        self.overrun_pill.set_text(
            CLOCK_OVERRUN_FORMAT.format(
                minutes=whole_minutes(overrun), seconds=remaining_seconds_of_minute(overrun)
            )
        )

    def show_phase(self, phase) -> None:
        if phase is None:
            self.phase_reading.set_value(CLOCK_PHASE_UNKNOWN_TEXT)
            return
        self.phase_reading.set_value(CLOCK_PHASE_FORMAT.format(phase=phase))


def state_for(elapsed_seconds: float) -> str:
    """Past the limit the clock is critical and the overrun chip says by how much."""
    if elapsed_seconds >= MISSION_CRITICAL_SECONDS:
        return STATE_CRITICAL
    if elapsed_seconds >= MISSION_CAUTION_SECONDS:
        return STATE_CAUTION
    return STATE_NONE


def whole_minutes(seconds: float) -> int:
    return int(seconds // SECONDS_PER_MINUTE)


def remaining_seconds_of_minute(seconds: float) -> int:
    return int(seconds % SECONDS_PER_MINUTE)
