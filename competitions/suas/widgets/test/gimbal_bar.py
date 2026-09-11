"""Where to point the camera, and where the camera says it is pointing.

The two halves of this bar are never the same number, and keeping them apart is
the point of it. Everything on the right is a reading the gimbal reported; not
one of them is ever filled in from a press. A gimbal with a seized motor answers
every command politely and reports back exactly what it was asked for, so a bar
that showed the commanded angle would pass a camera that is not moving at all.

POINT DOWN is straight down, which is the only angle the survey and the detector
ever want and the one worth its own press. STOP leaves the gimbal wherever it
happens to be, which is what you reach for when it starts walking off on its
own.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from competitions.suas.config import (
    MISSING_VALUE_TEXT,
    TEST_CAMERA_TEXT,
    TEST_CARD_TEXT,
    TEST_GIMBAL_TEXT,
)
from theme import flush_layout, set_role, set_state, set_variant
from theme.tokens import (
    ROLE_READOUT_LABEL,
    SPACE_MD,
    SPACE_XS,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_IDLE,
    STATE_NONE,
    STATE_OK,
    STATE_STALE,
    VARIANT_CAUTION,
)
from widgets import Card, Readout, StatusPill


class GimbalBar(Card):
    """The angles asked for on the left, the ones the camera reports on the right."""

    point_requested = pyqtSignal(float, float)
    zoom_requested = pyqtSignal(float)
    centre_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TEST_GIMBAL_TEXT["title"])

        # Two rows rather than one. Everything here in a single line came to
        # 1857 pixels, which is wider than the laptop this flies from -- and a
        # row that does not fit is a row Qt draws on top of itself. What is
        # asked for goes on the first line, what came back on the second, which
        # is also the order somebody reads them in.
        asked_row = QHBoxLayout()
        flush_layout(asked_row, SPACE_MD)
        self.build_inputs(asked_row)
        self.build_buttons(asked_row)
        asked_row.addStretch()

        reported_row = QHBoxLayout()
        flush_layout(reported_row, SPACE_MD)
        self.build_readings(reported_row)
        self.build_pills(reported_row)
        reported_row.addStretch()

        self.add_layout(asked_row)
        self.add_layout(reported_row)

        # A refused POINT is the one thing on this bar that leaves no trace:
        # the readings simply stay where they were, which is exactly what a
        # gimbal that ignored the command looks like. So the refusal is written
        # out rather than left to be inferred.
        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        self.add_widget(self.status_label)

        self.show_stale()
        self.show_status("", STATE_NONE)

    def build_inputs(self, bar) -> None:
        """The three boxes the operator types an angle or a zoom into."""
        asked_format = TEST_GIMBAL_TEXT["asked_caption_format"]

        self.yaw_input = angle_input(TEST_GIMBAL_TEXT["yaw_minimum_degrees"],
                                     TEST_GIMBAL_TEXT["yaw_maximum_degrees"], self)
        self.pitch_input = angle_input(TEST_GIMBAL_TEXT["pitch_minimum_degrees"],
                                       TEST_GIMBAL_TEXT["pitch_maximum_degrees"], self)

        self.zoom_input = QDoubleSpinBox(self)
        self.zoom_input.setDecimals(TEST_GIMBAL_TEXT["zoom_decimals"])
        self.zoom_input.setRange(TEST_GIMBAL_TEXT["zoom_minimum"],
                                 TEST_GIMBAL_TEXT["zoom_maximum"])
        self.zoom_input.setSingleStep(TEST_GIMBAL_TEXT["zoom_step"])
        self.zoom_input.setSuffix(TEST_GIMBAL_TEXT["zoom_suffix"])
        # Zoom has no button of its own: the camera takes a zoom the moment it
        # is given one, and a step of the box is a deliberate act already.
        self.zoom_input.valueChanged.connect(self.zoom_requested.emit)

        bar.addWidget(labelled_input(asked_format.format(
            caption=TEST_GIMBAL_TEXT["yaw_caption"]), self.yaw_input, self))
        bar.addWidget(labelled_input(asked_format.format(
            caption=TEST_GIMBAL_TEXT["pitch_caption"]), self.pitch_input, self))
        bar.addWidget(labelled_input(asked_format.format(
            caption=TEST_GIMBAL_TEXT["zoom_caption"]), self.zoom_input, self))

    def build_buttons(self, bar) -> None:
        self.point_button = QPushButton(TEST_GIMBAL_TEXT["point_text"], self)
        self.point_button.clicked.connect(self.request_point)

        self.down_button = QPushButton(TEST_GIMBAL_TEXT["down_text"], self)
        self.down_button.clicked.connect(self.request_point_down)

        self.centre_button = QPushButton(TEST_GIMBAL_TEXT["centre_text"], self)
        self.centre_button.clicked.connect(self.centre_requested.emit)

        self.stop_button = QPushButton(TEST_GIMBAL_TEXT["stop_text"], self)
        set_variant(self.stop_button, VARIANT_CAUTION)
        self.stop_button.clicked.connect(self.stop_requested.emit)

        for button in (self.point_button, self.down_button,
                       self.centre_button, self.stop_button):
            bar.addWidget(button)

    def build_readings(self, bar) -> None:
        """What the camera reported. Never touched by a press."""
        reported_format = TEST_GIMBAL_TEXT["reported_caption_format"]

        self.yaw_reading = Readout(reported_format.format(
            caption=TEST_GIMBAL_TEXT["yaw_caption"]), parent=self)
        self.pitch_reading = Readout(reported_format.format(
            caption=TEST_GIMBAL_TEXT["pitch_caption"]), parent=self)
        self.zoom_reading = Readout(reported_format.format(
            caption=TEST_GIMBAL_TEXT["zoom_caption"]), parent=self)

        for reading in (self.yaw_reading, self.pitch_reading, self.zoom_reading):
            bar.addWidget(reading)

    def build_pills(self, bar) -> None:
        self.answer_pill = StatusPill(self)
        self.stream_pill = StatusPill(self)
        self.recording_pill = StatusPill(self)
        self.card_pill = StatusPill(self)
        self.free_pill = StatusPill(self)

        for pill in (self.answer_pill, self.stream_pill, self.recording_pill,
                     self.card_pill, self.free_pill):
            bar.addWidget(pill)

    # The operator's side

    def request_point(self) -> None:
        self.point_requested.emit(self.yaw_input.value(), self.pitch_input.value())

    def request_point_down(self) -> None:
        self.point_requested.emit(TEST_GIMBAL_TEXT["down_yaw_degrees"],
                                  TEST_GIMBAL_TEXT["down_pitch_degrees"])

    # The camera's side

    def show_gimbal(self, gimbal_state) -> None:
        """Draw the camera's last word on itself.

        The boxes above are left alone on purpose. Writing a reading back into
        the box that commanded it would leave the two agreeing whatever the
        gimbal did, and disagreement is the answer this page is looking for.
        """
        self.show_angle(self.yaw_reading, gimbal_state.yaw_degrees)
        self.show_angle(self.pitch_reading, gimbal_state.pitch_degrees)
        self.show_zoom(gimbal_state.zoom)

        if gimbal_state.reachable:
            self.answer_pill.show_status(TEST_GIMBAL_TEXT["reachable_text"], STATE_OK)
        else:
            self.answer_pill.show_status(TEST_GIMBAL_TEXT["unreachable_text"],
                                         STATE_CRITICAL)

        if gimbal_state.stream_up:
            self.stream_pill.show_status(TEST_GIMBAL_TEXT["stream_up_text"], STATE_OK)
        else:
            self.stream_pill.show_status(TEST_GIMBAL_TEXT["stream_down_text"],
                                         STATE_CAUTION)

        if gimbal_state.recording:
            self.recording_pill.show_status(TEST_GIMBAL_TEXT["recording_text"],
                                            STATE_CRITICAL)
        else:
            self.recording_pill.show_status(TEST_GIMBAL_TEXT["idle_text"], STATE_IDLE)

        self.show_card(gimbal_state)

    def show_card(self, gimbal_state) -> None:
        """The camera's own card: what state it is in and how much room is left."""
        chip_format = TEST_GIMBAL_TEXT["chip_format"]

        if gimbal_state.card_state:
            self.card_pill.show_status(
                chip_format.format(caption=TEST_CARD_TEXT["state_caption"],
                                   value=gimbal_state.card_state),
                STATE_NONE,
            )
        else:
            self.card_pill.show_status(
                chip_format.format(caption=TEST_CARD_TEXT["state_caption"],
                                   value=MISSING_VALUE_TEXT),
                STATE_IDLE,
            )

        if gimbal_state.card_free_megabytes is None:
            self.free_pill.show_status(
                chip_format.format(caption=TEST_CARD_TEXT["free_caption"],
                                   value=MISSING_VALUE_TEXT),
                STATE_IDLE,
            )
            return

        self.free_pill.show_status(
            TEST_GIMBAL_TEXT["card_free_format"].format(
                caption=TEST_CARD_TEXT["free_caption"],
                megabytes=gimbal_state.card_free_megabytes,
            ),
            STATE_NONE,
        )

    def show_angle(self, readout, degrees) -> None:
        readout.set_state(STATE_NONE)
        if degrees is None:
            readout.set_value(MISSING_VALUE_TEXT)
            return
        readout.set_value(TEST_GIMBAL_TEXT["angle_format"].format(degrees=degrees))

    def show_zoom(self, zoom) -> None:
        self.zoom_reading.set_state(STATE_NONE)
        if zoom is None:
            self.zoom_reading.set_value(MISSING_VALUE_TEXT)
            return
        self.zoom_reading.set_value(TEST_GIMBAL_TEXT["zoom_format"].format(zoom=zoom))

    def show_stale(self) -> None:
        """Nothing has arrived for a while, so the readings stop claiming to be true."""
        for reading in (self.yaw_reading, self.pitch_reading, self.zoom_reading):
            reading.set_value(MISSING_VALUE_TEXT)
            reading.set_state(STATE_STALE)

        self.answer_pill.show_status(TEST_GIMBAL_TEXT["stale_text"], STATE_STALE)
        self.stream_pill.show_status(TEST_GIMBAL_TEXT["stale_text"], STATE_STALE)
        self.recording_pill.show_status(TEST_GIMBAL_TEXT["idle_text"], STATE_IDLE)
        self.card_pill.show_status(TEST_GIMBAL_TEXT["stale_text"], STATE_STALE)
        self.free_pill.show_status(TEST_GIMBAL_TEXT["stale_text"], STATE_STALE)

    # What the aircraft made of the last press

    def show_command_sent(self) -> None:
        self.show_status(TEST_CAMERA_TEXT["command_sent_text"], STATE_CAUTION)

    def show_command_accepted(self) -> None:
        self.show_status("", STATE_OK)

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


def angle_input(minimum: float, maximum: float, parent) -> QDoubleSpinBox:
    """A degrees box bounded by the travel the A8 mini actually has."""
    box = QDoubleSpinBox(parent)
    box.setDecimals(TEST_GIMBAL_TEXT["angle_decimals"])
    box.setRange(minimum, maximum)
    box.setSingleStep(TEST_GIMBAL_TEXT["angle_step"])
    box.setSuffix(TEST_GIMBAL_TEXT["angle_suffix"])
    return box


def labelled_input(caption: str, input_box, parent) -> QWidget:
    """A box with its caption above it, so it lines up with the readings beside it."""
    column = QWidget(parent)
    column_layout = QVBoxLayout(column)
    flush_layout(column_layout, SPACE_XS)

    caption_label = QLabel(caption, column)
    set_role(caption_label, ROLE_READOUT_LABEL)
    column_layout.addWidget(caption_label)
    column_layout.addWidget(input_box)
    return column
