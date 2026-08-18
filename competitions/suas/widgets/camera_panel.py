"""The live picture, and the one button that decides whether it is being kept.

The picture is what the SIYI A8 mini is looking at, relayed by the ground
services. It never arrives from the aircraft: this application has no video
stack, opens no stream and knows no codec — frames come off the mission bus as
JPEGs like everything else on this screen, already shrunk to something a broker
can carry.

The button is a different thing entirely and it is worth being clear about which
is which. It starts and stops the camera's own recording, onto the card in the
camera body, at full rate. That card is the only copy of a drop that did not go
through a radio, and it is what gets reviewed afterwards. Stopping this
recording does not stop the picture below it, and losing the picture does not
stop the recording.

Which is why the label follows the aircraft and not the click. The command is a
toggle: a button that says STOP because somebody pressed START is a button that
stops a recording that never began.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from competitions.suas.config import (
    CAMERA_COMMAND_REJECTED_FORMAT,
    CAMERA_COMMAND_SENT_TEXT,
    CAMERA_HOLD_HINT_TEXT,
    CAMERA_IDLE_TEXT,
    CAMERA_NO_SIGNAL_TEXT,
    CAMERA_PANEL_TITLE,
    CAMERA_RECORD_TEXT,
    CAMERA_RECORDING_TEXT,
    CAMERA_STOP_TEXT,
    CAMERA_UNKNOWN_TEXT,
    CAMERA_WAITING_TEXT,
    VIDEO_MINIMUM_HEIGHT,
)
from competitions.suas.widgets.hold_button import HoldButton
from theme import set_role, set_state
from theme.tokens import (
    ROLE_HINT,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_PRIMARY,
)
from widgets import Card, CameraView, StatusPill


class CameraPanel(Card):
    """The downlink picture, with the camera's own recording under it."""

    start_recording_requested = pyqtSignal()
    stop_recording_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, CAMERA_PANEL_TITLE)

        # The recording light goes in the title row, where the safety panel puts
        # its link light: the first thing to read about a camera is whether
        # what it is seeing is being kept.
        self.recording_pill = StatusPill(self)
        self.add_header_widget(self.recording_pill)

        self.camera_view = CameraView(self)
        self.camera_view.setMinimumHeight(VIDEO_MINIMUM_HEIGHT)

        self.record_button = HoldButton(CAMERA_RECORD_TEXT, VARIANT_PRIMARY, self)
        self.record_button.held.connect(self.request_recording)

        self.hint_label = QLabel(CAMERA_HOLD_HINT_TEXT, self)
        set_role(self.hint_label, ROLE_HINT)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.add_widget(self.camera_view)
        self.add_widget(self.record_button)
        self.add_widget(self.hint_label)
        self.add_widget(self.status_label)

        self.recording = None
        self.show_recording(None, "")
        self.show_status("", STATE_NONE)

    # The picture

    def show_frame(self, frame: QPixmap) -> None:
        """Draw one preview frame."""
        self.camera_view.show_pixmap(frame)

    def show_no_picture(self, has_had_one: bool) -> None:
        """Say the feed is not live, and say which kind of not live it is.

        Never having had a picture usually means the aircraft is not powered up.
        Having lost one means the link went, and that is worth a different word
        on the screen because it needs a different thing done about it.
        """
        if has_had_one:
            self.camera_view.show_placeholder(CAMERA_NO_SIGNAL_TEXT)
            return
        self.camera_view.show_placeholder(CAMERA_WAITING_TEXT)

    # The recording

    def show_recording(self, recording, reason: str) -> None:
        """Follow the aircraft's word on what the camera is doing.

        Parameters:
            recording (bool or None): ``None`` until the aircraft has said.
            reason (str): Why, when the aircraft had something to add.
        """
        self.recording = recording

        if recording is None:
            self.recording_pill.show_status(CAMERA_UNKNOWN_TEXT, STATE_CAUTION)
            self.record_button.button.setText(CAMERA_RECORD_TEXT)
            self.set_state(STATE_NONE)
        elif recording:
            self.recording_pill.show_status(CAMERA_RECORDING_TEXT, STATE_CRITICAL)
            self.record_button.button.setText(CAMERA_STOP_TEXT)
            self.record_button.set_variant(VARIANT_CAUTION)
            self.set_state(STATE_CRITICAL)
        else:
            self.recording_pill.show_status(CAMERA_IDLE_TEXT, STATE_NONE)
            self.record_button.button.setText(CAMERA_RECORD_TEXT)
            self.record_button.set_variant(VARIANT_PRIMARY)
            self.set_state(STATE_NONE)

        if reason:
            self.show_status(reason, STATE_CAUTION)

    def request_recording(self) -> None:
        """Ask for the opposite of what the camera is doing now.

        With the state unknown this asks to start, which is the safe way round:
        a start on a camera already recording is refused by the aircraft as
        "already in that state" and nothing is lost, where a stop would end a
        recording nobody meant to end.
        """
        if self.recording:
            self.stop_recording_requested.emit()
            return
        self.start_recording_requested.emit()

    def show_command_sent(self) -> None:
        self.show_status(CAMERA_COMMAND_SENT_TEXT, STATE_CAUTION)

    def show_command_accepted(self) -> None:
        self.show_status("", STATE_OK)

    def show_command_rejected(self, reason: str) -> None:
        self.show_status(CAMERA_COMMAND_REJECTED_FORMAT.format(reason=reason),
                         STATE_CRITICAL)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        self.status_label.setVisible(bool(status))
        set_state(self.status_label, state)
