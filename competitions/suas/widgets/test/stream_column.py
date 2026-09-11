"""The presses that act on the RTSP picture, down the right of the page.

This column is the 1080p Ethernet stream the Pi reads. START VIDEO and TAKE
PHOTO write on the Pi's own card, not the camera's, so everything this column
produces is a file the mission software can already reach — which is what makes
it worth proving separately from the card column on the other side.

The rate box is for the survey: a photo every so often, at the rate the mapping
pass would use, so a lens that goes soft at speed or a card that cannot keep up
shows itself on the bench rather than over the range.

Nothing here decides anything. A press leaves as a signal and the column waits
to be told what came of it.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton

from competitions.suas.config import CAMERA_TEST_ACTIONS, TEST_CAMERA_TEXT
from theme import flush_layout, set_role, set_state, set_variant
from theme.tokens import (
    ROLE_HINT,
    ROLE_READOUT_LABEL,
    SPACE_SM,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
)
from widgets import Card

START_VIDEO_ACTION = CAMERA_TEST_ACTIONS["stream_start_video"]
STOP_VIDEO_ACTION = CAMERA_TEST_ACTIONS["stream_stop_video"]
TAKE_PHOTO_ACTION = CAMERA_TEST_ACTIONS["stream_take_photo"]
START_TIMER_ACTION = CAMERA_TEST_ACTIONS["stream_start_photo_timer"]
STOP_TIMER_ACTION = CAMERA_TEST_ACTIONS["stream_stop_photo_timer"]


class StreamColumn(Card):
    """Four presses on the stream, and what the aircraft said about the last one."""

    command_requested = pyqtSignal(str)
    # The one press that carries a number with it, so it gets a signal of its
    # own rather than a rate the receiving end has to go and look up.
    photo_timer_requested = pyqtSignal(str, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TEST_CAMERA_TEXT["stream_column_title"])

        hint_label = QLabel(TEST_CAMERA_TEXT["stream_column_hint"], self)
        set_role(hint_label, ROLE_HINT)
        hint_label.setWordWrap(True)

        self.start_video_button = self.build_button(
            TEST_CAMERA_TEXT["start_video_text"], START_VIDEO_ACTION
        )
        self.stop_video_button = self.build_button(
            TEST_CAMERA_TEXT["stop_video_text"], STOP_VIDEO_ACTION
        )
        set_variant(self.stop_video_button, VARIANT_CAUTION)
        self.take_photo_button = self.build_button(
            TEST_CAMERA_TEXT["take_photo_text"], TAKE_PHOTO_ACTION
        )

        self.rate_input = QDoubleSpinBox(self)
        self.rate_input.setDecimals(TEST_CAMERA_TEXT["rate_decimals"])
        self.rate_input.setRange(TEST_CAMERA_TEXT["rate_minimum"],
                                 TEST_CAMERA_TEXT["rate_maximum"])
        self.rate_input.setSingleStep(TEST_CAMERA_TEXT["rate_step"])
        self.rate_input.setValue(TEST_CAMERA_TEXT["rate_default"])
        self.rate_input.setSuffix(TEST_CAMERA_TEXT["rate_suffix"])

        rate_caption = QLabel(TEST_CAMERA_TEXT["rate_caption"], self)
        set_role(rate_caption, ROLE_READOUT_LABEL)
        rate_row = QHBoxLayout()
        flush_layout(rate_row, SPACE_SM)
        rate_row.addWidget(rate_caption)
        rate_row.addWidget(self.rate_input)

        self.start_timer_button = QPushButton(
            TEST_CAMERA_TEXT["start_timer_text"], self
        )
        self.start_timer_button.clicked.connect(self.request_photo_timer)
        self.stop_timer_button = self.build_button(
            TEST_CAMERA_TEXT["stop_timer_text"], STOP_TIMER_ACTION
        )
        set_variant(self.stop_timer_button, VARIANT_CAUTION)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.add_widget(hint_label)
        self.add_widget(self.start_video_button)
        self.add_widget(self.stop_video_button)
        self.add_widget(self.take_photo_button)
        self.add_layout(rate_row)
        self.add_widget(self.start_timer_button)
        self.add_widget(self.stop_timer_button)
        self.add_widget(self.status_label)
        self.add_stretch()

        self.show_status("", STATE_NONE)

    def build_button(self, text: str, action: str) -> QPushButton:
        """A press that sends one action and nothing else with it."""
        button = QPushButton(text, self)
        button.clicked.connect(lambda: self.command_requested.emit(action))
        return button

    def request_photo_timer(self) -> None:
        self.photo_timer_requested.emit(START_TIMER_ACTION, self.rate_input.value())

    # What the aircraft said about the last press

    def show_command_sent(self) -> None:
        self.show_status(TEST_CAMERA_TEXT["command_sent_text"], STATE_CAUTION)

    def show_command_accepted(self) -> None:
        self.show_status(TEST_CAMERA_TEXT["command_accepted_text"], STATE_OK)

    def show_command_rejected(self, reason: str) -> None:
        self.show_status(
            TEST_CAMERA_TEXT["command_rejected_format"].format(reason=reason),
            STATE_CRITICAL,
        )

    def show_command_timeout(self) -> None:
        self.show_status(TEST_CAMERA_TEXT["command_timeout_text"], STATE_CRITICAL)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        self.status_label.setVisible(bool(status))
        set_state(self.status_label, state)
