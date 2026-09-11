"""Where the mission is, and the two presses that stand in for a waypoint.

The aircraft starts detection and mapping by itself when the autopilot reports
the survey's start waypoint reached, and ends the scan on the last one. If
either report never comes -- a re-numbered mission, a missed message, a mission
that ends on a loiter -- the operator presses the button for that end and the
aircraft does it where it is. Either way the phase line here says SURVEY
RUNNING the moment the aircraft reports it, so nobody has to guess whether the
cameras are on, and the line under it is the aircraft's own words -- which
waypoint started the scan, and whether detection and mapping are really
running.

Only one of the two is ever pressable, because they belong to different
phases: START SURVEY while the laps are flying, SCAN DONE while the scan is.
That is what keeps a stray click off them -- both do something that cannot be
taken back, and the one that does not belong to the phase on screen is
disabled rather than waiting to be held down.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel

from competitions.suas.config import (
    MISSION_COMMAND_REJECTED_FORMAT,
    MISSION_COMMAND_SENT_TEXT,
    MISSION_COMMAND_TIMEOUT_TEXT,
    MISSION_FINISH_HINT_TEXT,
    MISSION_FINISH_SURVEY_STATES,
    MISSION_FINISH_SURVEY_TEXT,
    MISSION_PANEL_TITLE,
    MISSION_PHASE_CAPTION,
    MISSION_PHASE_TEXTS,
    MISSION_PHASE_TIME_LEFT_FORMAT,
    MISSION_PHASE_UNKNOWN_TEXT,
    MISSION_PROBLEM_STATES,
    MISSION_START_HINT_TEXT,
    MISSION_START_SURVEY_STATES,
    MISSION_START_SURVEY_TEXT,
    MISSION_SURVEY_STATES,
)
from competitions.suas.widgets.command_button import command_button
from theme import set_role, set_state
from theme.tokens import (
    ROLE_HINT,
    SCALE_LARGE,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
)
from widgets import Card, Readout

SECONDS_PER_MINUTE = 60


class MissionPanel(Card):
    """The phase in plain words, and the two survey presses."""

    start_survey_requested = pyqtSignal()
    finish_survey_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, MISSION_PANEL_TITLE)

        self.phase_readout = Readout(MISSION_PHASE_CAPTION, SCALE_LARGE, self)
        self.phase_readout.set_value(MISSION_PHASE_UNKNOWN_TEXT)

        self.detail_label = QLabel(self)
        set_role(self.detail_label, ROLE_HINT)
        self.detail_label.setWordWrap(True)
        self.detail_label.setVisible(False)

        self.start_button = command_button(MISSION_START_SURVEY_TEXT, VARIANT_CAUTION, self)
        self.start_button.clicked.connect(self.start_survey_requested.emit)
        self.start_button.setEnabled(False)

        self.hint_label = QLabel(MISSION_START_HINT_TEXT, self)
        set_role(self.hint_label, ROLE_HINT)
        self.hint_label.setWordWrap(True)

        self.finish_button = command_button(MISSION_FINISH_SURVEY_TEXT,
                                            VARIANT_CAUTION, self)
        self.finish_button.clicked.connect(self.finish_survey_requested.emit)
        self.finish_button.setEnabled(False)

        self.finish_hint_label = QLabel(MISSION_FINISH_HINT_TEXT, self)
        set_role(self.finish_hint_label, ROLE_HINT)
        self.finish_hint_label.setWordWrap(True)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.add_widget(self.phase_readout)
        self.add_widget(self.detail_label)
        self.add_widget(self.start_button)
        self.add_widget(self.hint_label)
        self.add_widget(self.finish_button)
        self.add_widget(self.finish_hint_label)
        self.add_widget(self.status_label)
        self.show_status("", STATE_NONE)

    def show_phase(self, phase, detail="", flight_time_left_s=None) -> None:
        """The aircraft's state, in the words the operator reads.

        ``detail`` is the aircraft's own one line about it -- which waypoint
        started the scan, what is looking at the ground, which mode it was
        taken over in. The phase says what is happening and this says why.
        ``flight_time_left_s`` is the aircraft's flight clock, shown as whole
        minutes on the phase line once the aircraft reports one.
        """
        self.detail_label.setText(detail or "")
        self.detail_label.setVisible(bool(detail))

        if phase is None:
            self.phase_readout.set_value(MISSION_PHASE_UNKNOWN_TEXT)
            self.phase_readout.set_state(STATE_NONE)
            self.start_button.setEnabled(False)
            self.finish_button.setEnabled(False)
            return

        self.phase_readout.set_value(phase_line(phase, flight_time_left_s))
        if phase in MISSION_SURVEY_STATES:
            self.phase_readout.set_state(STATE_OK)
        elif phase in MISSION_PROBLEM_STATES:
            self.phase_readout.set_state(STATE_CRITICAL)
        else:
            self.phase_readout.set_state(STATE_NONE)

        self.start_button.setEnabled(phase in MISSION_START_SURVEY_STATES)
        self.finish_button.setEnabled(phase in MISSION_FINISH_SURVEY_STATES)

    def show_command_sent(self) -> None:
        self.show_status(MISSION_COMMAND_SENT_TEXT, STATE_CAUTION)

    def show_command_accepted(self, accepted_text: str) -> None:
        """Say which of the two presses the aircraft took."""
        self.show_status(accepted_text, STATE_OK)

    def show_command_rejected(self, reason: str) -> None:
        self.show_status(MISSION_COMMAND_REJECTED_FORMAT.format(reason=reason),
                         STATE_CRITICAL)

    def show_command_timed_out(self) -> None:
        self.show_status(MISSION_COMMAND_TIMEOUT_TEXT, STATE_CRITICAL)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        self.status_label.setVisible(bool(status))
        set_state(self.status_label, state)


def phase_line(phase: str, flight_time_left_s) -> str:
    """The phase in the operator's words, with the minutes left when known."""
    text = MISSION_PHASE_TEXTS.get(phase, phase)
    if flight_time_left_s is None:
        return text
    return MISSION_PHASE_TIME_LEFT_FORMAT.format(
        phase=text, minutes=int(flight_time_left_s // SECONDS_PER_MINUTE)
    )
