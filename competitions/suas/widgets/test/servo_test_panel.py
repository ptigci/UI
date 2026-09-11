"""One button, one bay, and proof that the servo behind it actually moved.

This is the bench half of the delivery test, so the countdown, RTL and LAND are
not here -- they belong to the mission screen, and a mechanism being proved on a
table has no flight to end. What is left is the pair of presses per bay: HOLD
clamps it shut on the payload that has just gone in, RELEASE opens it.

The payloads come from the config so the presses are there the moment the page
opens -- this is where a servo is proved, and a page that stayed empty until a
link came up could prove nothing. The aircraft's word still wins: one it does
not mention keeps its buttons, a spent one loses RELEASE and keeps HOLD, and a
press for something it is not carrying is refused with the reason, which on a
bench is worth seeing. The mission's own delivery panel is stricter and builds
only from what the aircraft says, because there a button for a payload that is
not aboard is a button that wastes a press on the clock.

The list is from the payload state the aircraft publishes rather than from a
list here, so they are whatever it says it is carrying, and one already spent
stays on the page -- it says what happened to that payload, which a row that
vanished would not. A spent bay keeps HOLD because HOLD is how the next
payload goes in: it is the press that says one has, and the aircraft loads the
bay again on it.

Under the presses is the point of the page. A button that lights up says the
message left the laptop; only the servo monitor says the horn went anywhere. A
station nobody has pressed reports UNKNOWN, and that is a real answer rather
than a missing one: the aircraft drives no servo when it starts, because a bay
that closed on its own would close on the hand loading it.

The other half of the page is the drop on a place the operator names, which is
its own widget beside this one. Its three signals are repeated here so that
everything the page can ask for is reached the same way.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from competitions.suas.config import (
    MISSING_VALUE_TEXT,
    SERVO_STATE_UNKNOWN,
    STATION_STATE_SPENT,
    TEST_DROP_TEXT,
    TEST_LAYOUT,
)
from competitions.suas.widgets.command_button import command_button
from competitions.suas.widgets.test.place_drop_row import PlaceDropRow, bay_label
from theme import flush_layout, set_role, set_state
from theme.tokens import (
    ROLE_HINT,
    ROLE_SUBHEADING,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_IDLE,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_PRIMARY,
)
from widgets import Card, Readout, StatusPill

# How the two presses of one bay share the row they sit in. RELEASE keeps most
# of it: it is the press being proved, and HOLD only puts the bay back.
RELEASE_BUTTON_WIDTH_SHARE = 2
HOLD_BUTTON_WIDTH_SHARE = 1


class ServoMonitorRow(QWidget):
    """One servo's four readings, named for the bay they belong to."""

    def __init__(self, station_name: str, parent=None) -> None:
        super().__init__(parent)

        name_label = QLabel(bay_label(station_name), self)
        set_role(name_label, ROLE_SUBHEADING)

        self.simulated_pill = StatusPill(self, TEST_DROP_TEXT["simulated_text"],
                                         STATE_CAUTION)
        self.simulated_pill.setVisible(False)

        self.state_readout = Readout(TEST_DROP_TEXT["state_caption"], parent=self)
        self.position_readout = Readout(TEST_DROP_TEXT["position_caption"], parent=self)
        self.pin_readout = Readout(TEST_DROP_TEXT["pin_caption"], parent=self)
        self.moved_readout = Readout(TEST_DROP_TEXT["moved_caption"], parent=self)

        heading = QHBoxLayout()
        flush_layout(heading, SPACE_SM)
        heading.addWidget(name_label)
        heading.addWidget(self.simulated_pill)
        heading.addStretch()

        readings = QHBoxLayout()
        flush_layout(readings, SPACE_MD)
        readings.addWidget(self.state_readout)
        readings.addWidget(self.position_readout)
        readings.addWidget(self.pin_readout)
        readings.addWidget(self.moved_readout)

        row_layout = QVBoxLayout(self)
        flush_layout(row_layout, SPACE_XS)
        row_layout.addLayout(heading)
        row_layout.addLayout(readings)

    def show_servo(self, servo, seconds_since_moved) -> None:
        self.state_readout.set_value(state_text(servo.state))
        self.state_readout.set_state(state_colour(servo.state))
        self.position_readout.set_value(position_text(servo.position))
        self.pin_readout.set_value(pin_text(servo.servo_output))
        self.moved_readout.set_value(moved_text(seconds_since_moved))
        self.simulated_pill.setVisible(servo.simulated)


class ServoTestPanel(Card):
    """The presses per bay, and where each servo was last driven."""

    hold_requested = pyqtSignal(str)
    release_requested = pyqtSignal(str)
    plan_requested = pyqtSignal(float, float, float, str, float)
    plan_and_drop_requested = pyqtSignal(float, float, float, str, float)
    approve_requested = pyqtSignal(str)
    reject_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TEST_DROP_TEXT["title"])

        hint_label = QLabel(TEST_DROP_TEXT["hint_text"], self)
        set_role(hint_label, ROLE_HINT)
        hint_label.setWordWrap(True)

        self.release_buttons: dict = {}
        self.button_area = QWidget(self)
        self.button_layout = QVBoxLayout(self.button_area)
        flush_layout(self.button_layout, SPACE_XS)

        self.waiting_label = QLabel(TEST_DROP_TEXT["waiting_text"], self)
        set_role(self.waiting_label, ROLE_HINT)
        self.waiting_label.setWordWrap(True)
        self.button_layout.addWidget(self.waiting_label)

        # The presses exist from the start, from the config's list. The
        # aircraft replaces the list the moment it says what it is carrying.
        for station_name in TEST_DROP_TEXT["stations"]:
            self.build_station_row(station_name)

        self.place_row = PlaceDropRow(self)
        self.place_row.plan_requested.connect(self.plan_requested)
        self.place_row.plan_and_drop_requested.connect(self.plan_and_drop_requested)
        self.place_row.approve_requested.connect(self.approve_requested)
        self.place_row.reject_requested.connect(self.reject_requested)

        monitor_label = QLabel(TEST_DROP_TEXT["monitor_title"], self)
        set_role(monitor_label, ROLE_SUBHEADING)

        self.monitor_rows: dict = {}
        self.monitor_area = QWidget(self)
        self.monitor_area.setMinimumHeight(TEST_LAYOUT["monitor_minimum_height"])
        self.monitor_layout = QVBoxLayout(self.monitor_area)
        flush_layout(self.monitor_layout, SPACE_MD)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.add_widget(hint_label)
        self.add_widget(self.button_area)
        self.add_widget(self.place_row)
        self.add_widget(monitor_label)
        self.add_widget(self.monitor_area)
        self.add_widget(self.status_label)
        self.add_stretch()

        self.show_status("", STATE_NONE)

    # What the aircraft says it has

    def show_stations(self, payload_state) -> None:
        """One row of presses per payload, and no presses left on a spent one.

        A payload the aircraft does not mention keeps its buttons rather than
        losing them. On this page that is deliberate: pressing one and being
        refused says the aircraft is not carrying it, which is a better answer
        than a button that quietly went away.
        """
        if not payload_state.stations:
            return
        self.waiting_label.setVisible(False)
        self.place_row.show_stations(payload_state)

        for station in payload_state.stations:
            if station.name not in self.release_buttons:
                self.build_station_row(station.name)
            # RELEASE goes with the payload: a spent bay has nothing to drop.
            # HOLD does not. It is the press that says a payload has been put
            # back in, so it is exactly the press a spent bay needs -- greyed
            # out there, a bench session was one release long and nothing on
            # this page could start the next one.
            loaded = station.state != STATION_STATE_SPENT
            self.release_buttons[station.name].setEnabled(loaded)

    def build_station_row(self, station_name: str) -> None:
        label = bay_label(station_name)

        release_button = command_button(
            TEST_DROP_TEXT["release_format"].format(station=label), VARIANT_CAUTION, self
        )
        release_button.clicked.connect(
            lambda: self.release_requested.emit(station_name))

        hold_button = command_button(
            TEST_DROP_TEXT["hold_format"].format(station=label), VARIANT_PRIMARY, self
        )
        hold_button.clicked.connect(lambda: self.hold_requested.emit(station_name))

        row = QWidget(self)
        row_layout = QHBoxLayout(row)
        flush_layout(row_layout, SPACE_XS)
        row_layout.addWidget(release_button, RELEASE_BUTTON_WIDTH_SHARE)
        row_layout.addWidget(hold_button, HOLD_BUTTON_WIDTH_SHARE)

        self.release_buttons[station_name] = release_button
        self.button_layout.addWidget(row)

    def show_servos(self, servo_state) -> None:
        """Where every servo the aircraft knows about was last driven."""
        for servo in servo_state.stations:
            if servo.station not in self.monitor_rows:
                row = ServoMonitorRow(servo.station, self)
                self.monitor_rows[servo.station] = row
                self.monitor_layout.addWidget(row)
            self.monitor_rows[servo.station].show_servo(
                servo, servo_state.seconds_since_moved(servo.station)
            )

    def show_route(self, route_plan) -> None:
        self.place_row.show_route(route_plan)

    # What the operator's last press came to

    def show_command_sent(self) -> None:
        self.show_status(TEST_DROP_TEXT["command_sent_text"], STATE_CAUTION)

    def show_command_accepted(self) -> None:
        self.show_status(TEST_DROP_TEXT["command_accepted_text"], STATE_OK)

    def show_command_rejected(self, reason: str) -> None:
        self.show_status(
            TEST_DROP_TEXT["command_rejected_format"].format(reason=reason),
            STATE_CRITICAL,
        )

    def show_command_timeout(self) -> None:
        self.show_status(TEST_DROP_TEXT["command_timeout_text"], STATE_CRITICAL)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        self.status_label.setVisible(bool(status))
        set_state(self.status_label, state)


def state_text(state: str) -> str:
    if state == SERVO_STATE_UNKNOWN:
        return TEST_DROP_TEXT["unknown_state_text"]
    return state.upper()


def state_colour(state: str) -> str:
    """Grey until something has driven it, then the colour of a plain reading."""
    if state == SERVO_STATE_UNKNOWN:
        return STATE_IDLE
    return STATE_NONE


def position_text(position) -> str:
    if position is None:
        return MISSING_VALUE_TEXT
    return TEST_DROP_TEXT["position_format"].format(position=position)


def pin_text(servo_output) -> str:
    if servo_output is None:
        return MISSING_VALUE_TEXT
    return str(int(servo_output))


def moved_text(seconds_since_moved) -> str:
    if seconds_since_moved is None:
        return TEST_DROP_TEXT["never_moved_text"]
    return TEST_DROP_TEXT["moved_format"].format(seconds=seconds_since_moved)
