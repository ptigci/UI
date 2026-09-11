"""The bar across the top: mission state, scan progress, and the way out.

SEND DRONES is the one control here that starts the mission. HOLD, RETREAT and
ABORT are the three that matter when something goes wrong, so they are wide and
they report how many vehicles actually answered. A command nobody acknowledged
is worse than no command, and the operator must see that immediately.

Every button here acts on the click. There is nothing to say yes to: a recall
the operator has to confirm twice is a recall that arrives late.

RECORD asks for the Pasifik's camera to be written to its card. The light beside
it says REC only once the aircraft reports that the recording is running.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget

from competitions.international_uav.config import (
    ABORT_TEXT,
    ACK_CAPTION,
    ACK_COMPLETE_FORMAT,
    ACK_NONE_TEXT,
    ACK_PENDING_FORMAT,
    ACK_TIMEOUT_FORMAT,
    DISPATCH_TEXT,
    ELAPSED_CAPTION,
    ELAPSED_FORMAT,
    HOLD_TEXT,
    MISSION_ACTIVE_STATES,
    MISSION_STATE_PREFIX,
    MISSION_UNKNOWN_STATE_TEXT,
    RECORD_STOP_TEXT,
    RECORD_TEXT,
    RECORDING_OFF_TEXT,
    RECORDING_ON_TEXT,
    RESUME_TEXT,
    RETREAT_TEXT,
    SCAN_CAPTION,
    SCAN_PROGRESS_FORMAT,
    SCAN_WAITING_TEXT,
)
from theme import set_scale, set_surface, set_variant, space_layout
from theme.tokens import (
    AS_APP_BAR,
    SCALE_LARGE,
    SCALE_TITLE,
    SPACE_LG,
    SPACE_XL,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_IDLE,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_DANGER,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
)
from widgets import Readout, StatusPill

SECONDS_PER_MINUTE = 60


class MissionBar(QWidget):
    """Mission state, scan progress, elapsed time, HOLD and ABORT."""

    dispatch_requested = pyqtSignal()
    hold_requested = pyqtSignal()
    resume_requested = pyqtSignal()
    retreat_requested = pyqtSignal()
    abort_requested = pyqtSignal()
    start_recording_requested = pyqtSignal()
    stop_recording_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        set_surface(self, AS_APP_BAR)
        # A bar is as tall as one row of controls; the workspace under it takes
        # every pixel it does not need.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.holding = False
        self.recording = False

        self.state_reading = Readout(MISSION_STATE_PREFIX, SCALE_TITLE, self)
        self.scan_reading = Readout(SCAN_CAPTION, parent=self)
        self.scan_reading.set_value(SCAN_WAITING_TEXT)
        self.elapsed_reading = Readout(ELAPSED_CAPTION, parent=self)
        self.ack_reading = Readout(ACK_CAPTION, parent=self)
        self.recording_pill = StatusPill(self)

        # Quiet on purpose: the recording control sits beside four mission
        # commands and must not look like a fifth one.
        self.recordbtn = self.build_button(RECORD_TEXT, VARIANT_GHOST)
        self.dispatchbtn = self.build_button(DISPATCH_TEXT, VARIANT_PRIMARY)
        self.holdbtn = self.build_button(HOLD_TEXT, VARIANT_CAUTION)
        self.retreatbtn = self.build_button(RETREAT_TEXT, VARIANT_CAUTION)
        self.abortbtn = self.build_button(ABORT_TEXT, VARIANT_DANGER)

        bar_layout = QHBoxLayout(self)
        space_layout(bar_layout, SPACE_LG, SPACE_XL)
        bar_layout.addWidget(self.state_reading)
        bar_layout.addWidget(self.scan_reading)
        bar_layout.addWidget(self.elapsed_reading)
        bar_layout.addWidget(self.ack_reading)
        bar_layout.addStretch()
        bar_layout.addWidget(self.recording_pill)
        bar_layout.addWidget(self.recordbtn)
        bar_layout.addWidget(self.dispatchbtn)
        bar_layout.addWidget(self.holdbtn)
        bar_layout.addWidget(self.retreatbtn)
        bar_layout.addWidget(self.abortbtn)

        self.recordbtn.clicked.connect(self.request_recording)
        self.dispatchbtn.clicked.connect(self.dispatch_requested)
        self.holdbtn.clicked.connect(self.request_hold_or_resume)
        self.retreatbtn.clicked.connect(self.retreat_requested)
        self.abortbtn.clicked.connect(self.abort_requested)

        self.show_mission_state(None)
        self.show_elapsed(0.0)
        self.show_recording(False)

    def build_button(self, text: str, variant: str) -> QPushButton:
        button = QPushButton(text, self)
        set_variant(button, variant)
        set_scale(button, SCALE_LARGE)
        return button

    # Operator actions

    def request_hold_or_resume(self) -> None:
        """One button for both, because the swarm is either held or it is not."""
        if self.holding:
            self.resume_requested.emit()
            return
        self.hold_requested.emit()

    def request_recording(self) -> None:
        """Ask for the opposite of what the ground station is doing now.

        With nothing recorded yet this asks to start, which is the safe way
        round: a second start changes nothing, where a stop would end a
        recording nobody meant to end.
        """
        if self.recording:
            self.stop_recording_requested.emit()
            return
        self.start_recording_requested.emit()

    def set_holding(self, holding: bool) -> None:
        """The same button holds the swarm and lets it go again."""
        self.holding = holding
        if holding:
            self.holdbtn.setText(RESUME_TEXT)
        else:
            self.holdbtn.setText(HOLD_TEXT)

    # Display

    def show_mission_state(self, mission_state: str | None) -> None:
        if mission_state is None:
            state_text = MISSION_UNKNOWN_STATE_TEXT
        else:
            state_text = mission_state
        self.state_reading.set_value(state_text)

        if state_text in MISSION_ACTIVE_STATES:
            self.state_reading.set_state(STATE_OK)
        else:
            self.state_reading.set_state(STATE_IDLE)

    def show_scan_progress(self, percent, legs_done, legs_total) -> None:
        if percent is None or legs_done is None or legs_total is None:
            self.scan_reading.set_value(SCAN_WAITING_TEXT)
            return
        self.scan_reading.set_value(
            SCAN_PROGRESS_FORMAT.format(
                percent=percent, legs_done=legs_done, legs_total=legs_total
            )
        )

    def show_elapsed(self, elapsed_seconds: float) -> None:
        minutes = int(elapsed_seconds // SECONDS_PER_MINUTE)
        seconds = int(elapsed_seconds % SECONDS_PER_MINUTE)
        self.elapsed_reading.set_value(
            ELAPSED_FORMAT.format(minutes=minutes, seconds=seconds)
        )

    def show_recording(self, recording: bool) -> None:
        """The pill and the button follow the ground station, not the click.

        A button that says STOP because somebody pressed RECORD is a button
        that stops a recording that never began.
        """
        self.recording = recording
        if recording:
            self.recording_pill.show_status(RECORDING_ON_TEXT, STATE_OK)
            self.recordbtn.setText(RECORD_STOP_TEXT)
            set_variant(self.recordbtn, VARIANT_CAUTION)
        else:
            self.recording_pill.show_status(RECORDING_OFF_TEXT, STATE_CRITICAL)
            self.recordbtn.setText(RECORD_TEXT)
            set_variant(self.recordbtn, VARIANT_GHOST)

    def show_command_acks(self, command, acknowledged, expected, missing, timed_out) -> None:
        """How many vehicles answered the last HOLD / ABORT / RESUME."""
        if command is None:
            self.ack_reading.set_value(ACK_NONE_TEXT)
            self.ack_reading.set_state(STATE_NONE)
            return
        if timed_out:
            self.ack_reading.set_value(
                ACK_TIMEOUT_FORMAT.format(command=command, missing=", ".join(missing))
            )
            self.ack_reading.set_state(STATE_CRITICAL)
            return
        if acknowledged >= expected:
            self.ack_reading.set_value(ACK_COMPLETE_FORMAT.format(command=command))
            self.ack_reading.set_state(STATE_OK)
            return
        self.ack_reading.set_value(
            ACK_PENDING_FORMAT.format(
                command=command, acknowledged=acknowledged, expected=expected
            )
        )
        self.ack_reading.set_state(STATE_CAUTION)
