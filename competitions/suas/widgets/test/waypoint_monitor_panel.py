"""Where the aircraft is in the mission, and which item starts the scan.

The autopilot is flying a mission somebody loaded in Mission Planner. Which item
should start the scan and which should end it is a thing you find out on the day
-- a re-numbered mission, a survey leg moved, a takeoff item added -- so the two
numbers are set from here rather than baked into the aircraft's config.

The banner is why the page exists. The moment the aircraft crosses one of the
two, START or STOP appears with the item it fired on, and it stays there for the
rest of the flight: a trigger that fired and then vanished tells the operator
nothing, and the failure this page is looking for is the one that never fires at
all. Until then the line under it says so in words.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from competitions.suas.config import (
    MISSING_VALUE_TEXT,
    TEST_WAYPOINT_TEXT,
    WAYPOINT_TRIGGER_FINISH,
    WAYPOINT_TRIGGER_START,
)
from competitions.suas.widgets.command_button import command_button
from theme import flush_layout, set_role, set_state
from theme.tokens import (
    ROLE_HINT,
    SCALE_DISPLAY,
    SPACE_MD,
    SPACE_SM,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_IDLE,
    STATE_INFO,
    STATE_NONE,
    STATE_OK,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
)
from widgets import Card, Readout


class WaypointMonitorPanel(Card):
    """The mission count, the two items the scan is armed on, and what fired."""

    set_start_requested = pyqtSignal(int)
    set_finish_requested = pyqtSignal(int)
    clear_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TEST_WAYPOINT_TEXT["title"])

        # Which item the last SET asked for, so the answer can name it. CLEAR
        # names no item and leaves this empty.
        self.requested_index: int | None = None

        self.progress_readout = Readout(TEST_WAYPOINT_TEXT["progress_caption"],
                                        parent=self)
        self.distance_readout = Readout(TEST_WAYPOINT_TEXT["distance_caption"],
                                        parent=self)
        progress_row = QHBoxLayout()
        flush_layout(progress_row, SPACE_MD)
        progress_row.addWidget(self.progress_readout)
        progress_row.addWidget(self.distance_readout)

        self.progress_waiting_label = QLabel(
            TEST_WAYPOINT_TEXT["progress_waiting_text"], self)
        set_role(self.progress_waiting_label, ROLE_HINT)
        self.progress_waiting_label.setWordWrap(True)

        self.add_layout(progress_row)
        self.add_widget(self.progress_waiting_label)

        self.start_input, self.start_armed_label = self.build_arm_row(
            TEST_WAYPOINT_TEXT["start_caption"], self.request_start)
        self.finish_input, self.finish_armed_label = self.build_arm_row(
            TEST_WAYPOINT_TEXT["finish_caption"], self.request_finish)

        clear_button = command_button(TEST_WAYPOINT_TEXT["clear_text"],
                                      VARIANT_GHOST, self)
        clear_button.clicked.connect(self.request_clear)
        self.add_widget(clear_button)

        self.triggered_readout = Readout(TEST_WAYPOINT_TEXT["triggered_caption"],
                                         SCALE_DISPLAY, self)
        self.triggered_label = QLabel(self)
        set_role(self.triggered_label, ROLE_HINT)
        self.triggered_label.setWordWrap(True)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.add_widget(self.triggered_readout)
        self.add_widget(self.triggered_label)
        self.add_widget(self.status_label)
        self.add_stretch()

        self.show_progress(None, None, None)
        self.show_triggered(None)
        self.show_armed(self.start_armed_label, None)
        self.show_armed(self.finish_armed_label, None)
        self.show_status("", STATE_NONE)

    def build_arm_row(self, caption: str, press) -> tuple:
        """A number, the press that arms it, and what the aircraft says about it."""
        caption_label = QLabel(caption, self)

        index_input = QSpinBox(self)
        index_input.setRange(TEST_WAYPOINT_TEXT["minimum_index"],
                             TEST_WAYPOINT_TEXT["maximum_index"])

        set_button = command_button(TEST_WAYPOINT_TEXT["set_text"],
                                    VARIANT_PRIMARY, self)
        set_button.clicked.connect(press)

        armed_label = QLabel(self)
        set_role(armed_label, ROLE_HINT)

        controls = QHBoxLayout()
        flush_layout(controls, SPACE_SM)
        controls.addWidget(index_input)
        controls.addWidget(set_button)
        controls.addWidget(armed_label)
        controls.addStretch()

        row = QWidget(self)
        row_layout = QVBoxLayout(row)
        flush_layout(row_layout, SPACE_SM)
        row_layout.addWidget(caption_label)
        row_layout.addLayout(controls)
        self.add_widget(row)

        return index_input, armed_label

    # The operator's side

    def request_start(self) -> None:
        self.requested_index = self.start_input.value()
        self.set_start_requested.emit(self.requested_index)

    def request_finish(self) -> None:
        self.requested_index = self.finish_input.value()
        self.set_finish_requested.emit(self.requested_index)

    def request_clear(self) -> None:
        self.requested_index = None
        self.clear_requested.emit()

    # What the aircraft says

    def show_progress(self, index, count, distance_metres) -> None:
        """Item N of M and the metres to the next, or the line saying neither."""
        waiting = index is None or count is None
        self.progress_waiting_label.setVisible(waiting)
        if waiting:
            self.progress_readout.set_value(MISSING_VALUE_TEXT)
        else:
            self.progress_readout.set_value(
                TEST_WAYPOINT_TEXT["progress_format"].format(index=index, count=count)
            )

        if distance_metres is None:
            self.distance_readout.set_value(MISSING_VALUE_TEXT)
            return
        self.distance_readout.set_value(
            TEST_WAYPOINT_TEXT["distance_format"].format(metres=distance_metres)
        )

    def show_watch(self, waypoint_watch_state) -> None:
        self.show_armed(self.start_armed_label,
                        waypoint_watch_state.armed_index(WAYPOINT_TRIGGER_START))
        self.show_armed(self.finish_armed_label,
                        waypoint_watch_state.armed_index(WAYPOINT_TRIGGER_FINISH))
        if waypoint_watch_state.has_triggered():
            self.show_triggered(waypoint_watch_state)

    def show_armed(self, armed_label, index) -> None:
        if index is None:
            armed_label.setText(TEST_WAYPOINT_TEXT["not_armed_text"])
            return
        armed_label.setText(TEST_WAYPOINT_TEXT["armed_format"].format(index=index))

    def show_triggered(self, waypoint_watch_state) -> None:
        """The word, the item it fired on, and nothing that takes it away again."""
        if waypoint_watch_state is None:
            self.triggered_readout.set_value(MISSING_VALUE_TEXT)
            self.triggered_readout.set_state(STATE_IDLE)
            self.triggered_label.setText(TEST_WAYPOINT_TEXT["not_triggered_text"])
            return

        if waypoint_watch_state.triggered_start():
            self.triggered_readout.set_value(TEST_WAYPOINT_TEXT["triggered_start_text"])
            self.triggered_readout.set_state(STATE_OK)
        else:
            self.triggered_readout.set_value(TEST_WAYPOINT_TEXT["triggered_finish_text"])
            self.triggered_readout.set_state(STATE_INFO)

        self.triggered_label.setText(
            TEST_WAYPOINT_TEXT["triggered_format"].format(
                index=waypoint_watch_state.triggered_index)
        )

    # What the operator's last press came to

    def show_command_sent(self) -> None:
        self.show_status(TEST_WAYPOINT_TEXT["command_sent_text"], STATE_CAUTION)

    def show_command_accepted(self) -> None:
        if self.requested_index is None:
            self.show_status(TEST_WAYPOINT_TEXT["command_cleared_text"], STATE_OK)
            return
        self.show_status(
            TEST_WAYPOINT_TEXT["command_accepted_format"].format(
                index=self.requested_index),
            STATE_OK,
        )

    def show_command_rejected(self, reason: str) -> None:
        self.show_status(
            TEST_WAYPOINT_TEXT["command_rejected_format"].format(reason=reason),
            STATE_CRITICAL,
        )

    def show_command_timeout(self) -> None:
        self.show_status(TEST_WAYPOINT_TEXT["command_timeout_text"], STATE_CRITICAL)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        self.status_label.setVisible(bool(status))
        set_state(self.status_label, state)
