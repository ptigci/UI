"""The delivery test: the countdown to a release, and the presses that drive one.

Two mechanisms, two ways of flying them, one panel — because the operator asks
the same question of both and the aircraft answers it the same way.

The winch is flown by hand, four presses in order. GO TO DROP ZONE plans the
route to the next target and hovers over it; RELEASE runs the winch on the
target underneath; RTL or LAND ends the test. Nothing happens between presses,
which is the point: a mechanism being proved for the first time should not also
be deciding when to fire.

There is one RELEASE per bay, because each bay has its own servo and proving
that one button opens one bay is most of what a delivery test is for. The bays
come from the payload state the aircraft publishes rather than from a list
here, so they are whatever it says it is carrying, and one already spent greys
out. In the winch flow the target decides which bay opens, so a press for the
other one is refused by the aircraft with the reason.

Beside each RELEASE is the press that goes the other way. The aircraft drives
no servo when it starts up -- a bay that closed on its own would close on the
hand loading it, and on the winch rig the clamp is the cutter -- so nothing
grips a payload until HOLD is pressed. HOLD is the name of the clamp closing,
not of a button that has to be held: every press on this panel fires on one
click.

The winged release is not flown by hand at all. The aircraft is on the mission
that was loaded in Mission Planner and nothing here touches it — all the
operator can do is watch the metres to the release point come down and see
whether the pass is going to work. So the two delivery buttons come off; RTL and
LAND stay, because ending the flight is always the operator's.

RTL and LAND go out over the direct MAVLink link, not the mission bus. They are
the same call the safety panel makes and they are repeated here so the sequence
reads in the order it is flown — a press that puts the aircraft on the ground
has no business travelling through the Raspberry Pi when there is a link that
does not need it.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from competitions.suas.config import (
    DROP_COUNTDOWN_CAPTION,
    DROP_COUNTDOWN_FORMAT,
    DROP_COUNTDOWN_READY_TEXT,
    DROP_GEOMETRY_CAPTION,
    DROP_GEOMETRY_FORMAT,
    DROP_GOTO_TEXT,
    DROP_HOLD_FORMAT,
    DROP_LAND_TEXT,
    DROP_PANEL_TITLE,
    DROP_RELEASE_FORMAT,
    DROP_RELEASE_WAITING_TEXT,
    DROP_RETURN_TEXT,
    DROP_TARGET_CAPTION,
    DROP_TARGET_FORMAT,
    DROP_WAITING_TEXT,
    DROP_WATCH_ONLY_TEXT,
    MISSING_VALUE_TEXT,
    STATION_STATE_SPENT,
)
from competitions.suas.widgets.command_button import command_button
from theme import flush_layout, set_role, set_state
from theme.tokens import (
    ROLE_HINT,
    SCALE_DISPLAY,
    SPACE_LG,
    SPACE_XS,
    STATE_CAUTION,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_PRIMARY,
)
from widgets import Card, Readout

# How the two presses of one bay share the row they sit in.
RELEASE_BUTTON_WIDTH_SHARE = 2
HOLD_BUTTON_WIDTH_SHARE = 1


class DropTestPanel(Card):
    """What the aircraft is about to drop, and the presses that make it."""

    goto_target_requested = pyqtSignal()
    # Which bay to open: each has its own servo, so each has its own button.
    release_requested = pyqtSignal(str)
    # And which bay to clamp shut on the payload that has just gone into it.
    hold_requested = pyqtSignal(str)
    return_to_launch_requested = pyqtSignal()
    land_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, DROP_PANEL_TITLE)

        # The one number the operator is watching, at the size that means they
        # can read it without looking away from the aircraft for long.
        self.countdown_reading = Readout(DROP_COUNTDOWN_CAPTION, SCALE_DISPLAY, self)
        self.target_reading = Readout(DROP_TARGET_CAPTION, parent=self)
        self.geometry_reading = Readout(DROP_GEOMETRY_CAPTION, parent=self)

        # Why it is not releasing. On a pass that fails this is the whole
        # diagnosis, so it wraps rather than being cut off.
        self.reason_label = QLabel(self)
        set_role(self.reason_label, ROLE_HINT)
        self.reason_label.setWordWrap(True)

        self.goto_button = command_button(DROP_GOTO_TEXT, VARIANT_PRIMARY, self)
        self.return_button = command_button(DROP_RETURN_TEXT, VARIANT_CAUTION, self)
        self.land_button = command_button(DROP_LAND_TEXT, VARIANT_CAUTION, self)

        self.goto_button.clicked.connect(self.goto_target_requested.emit)
        self.return_button.clicked.connect(self.return_to_launch_requested.emit)
        self.land_button.clicked.connect(self.land_requested.emit)

        # One row of two buttons per bay, added when the aircraft says what it
        # is carrying. Until then there is a line saying so, because a RELEASE
        # that names no bay is not a button worth offering.
        self.release_buttons: dict = {}
        self.hold_buttons: dict = {}
        # Whether the aircraft takes a delivery press at all, remembered so a
        # bay reported after the countdown gets the same answer as the rest.
        self.deliveries_commandable = True
        self.station_area = QWidget(self)
        self.station_layout = QVBoxLayout(self.station_area)
        flush_layout(self.station_layout, SPACE_XS)
        self.station_waiting_label = QLabel(DROP_RELEASE_WAITING_TEXT, self)
        set_role(self.station_waiting_label, ROLE_HINT)
        self.station_waiting_label.setWordWrap(True)
        self.station_layout.addWidget(self.station_waiting_label)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.add_widget(self.countdown_reading)
        self.add_widget(self.target_reading)
        self.add_widget(self.geometry_reading)
        self.add_widget(self.reason_label)
        self.add_widget(self.goto_button)
        self.add_widget(self.station_area)
        # The two that end the flight are not neighbours of the two that run it.
        self.card_layout.addSpacing(SPACE_LG)
        self.add_widget(self.return_button)
        self.add_widget(self.land_button)
        self.add_widget(self.status_label)
        self.add_stretch()

        self.show_countdown(None)
        self.show_status("", STATE_NONE)

    # What the aircraft is doing

    def show_countdown(self, release_state) -> None:
        """Draw the last countdown, or say there is no delivery being set up."""
        if release_state is None or not release_state.is_live():
            self.clear_countdown()
            return

        self.show_metres(release_state)
        self.show_target(release_state)
        self.show_geometry(release_state)
        self.reason_label.setText(release_state.reason)
        self.show_delivery_buttons(not release_state.is_watch_only())

    def clear_countdown(self) -> None:
        """No delivery in progress. The numbers go away rather than going stale."""
        self.countdown_reading.set_value(MISSING_VALUE_TEXT)
        self.countdown_reading.set_state(STATE_NONE)
        self.target_reading.set_value(MISSING_VALUE_TEXT)
        self.geometry_reading.set_value(MISSING_VALUE_TEXT)
        self.reason_label.setText(DROP_WAITING_TEXT)
        self.show_delivery_buttons(True)

    def show_metres(self, release_state) -> None:
        """The metres left, or the word that says it is going now."""
        if release_state.release_allowed:
            self.countdown_reading.set_value(DROP_COUNTDOWN_READY_TEXT)
            self.countdown_reading.set_state(STATE_OK)
            return

        if release_state.metres_to_release is None:
            self.countdown_reading.set_value(MISSING_VALUE_TEXT)
            self.countdown_reading.set_state(STATE_NONE)
            return

        self.countdown_reading.set_value(
            DROP_COUNTDOWN_FORMAT.format(metres=release_state.metres_to_release)
        )
        self.countdown_reading.set_state(STATE_CAUTION)

    def show_target(self, release_state) -> None:
        if release_state.track_id is None or release_state.target_class is None:
            self.target_reading.set_value(MISSING_VALUE_TEXT)
            return
        self.target_reading.set_value(
            DROP_TARGET_FORMAT.format(
                target_class=release_state.target_class,
                track_id=release_state.track_id,
            )
        )

    def show_geometry(self, release_state) -> None:
        """The throw and how far the nose is off it — the winged mode's two gates."""
        if release_state.throw_metres is None:
            self.geometry_reading.set_value(MISSING_VALUE_TEXT)
            return

        heading_error = release_state.heading_error_degrees
        if heading_error is None:
            heading_error = 0.0

        self.geometry_reading.set_value(
            DROP_GEOMETRY_FORMAT.format(
                throw=release_state.throw_metres, heading=heading_error
            )
        )

    def show_delivery_buttons(self, commandable: bool) -> None:
        """Hide the presses the winged release has no use for.

        Disabling them would be a lie of a different shape: the buttons are not
        unavailable, they are meaningless, and a greyed-out control reads as
        something that will come back.

        HOLD stays either way. It clamps a bay on its payload rather than
        flying anything, and a winged flight is loaded like every other one.
        """
        self.deliveries_commandable = commandable
        self.goto_button.setVisible(commandable)
        for button in self.release_buttons.values():
            button.setVisible(commandable)
        if commandable:
            return
        self.reason_label.setText(DROP_WATCH_ONLY_TEXT)

    def show_stations(self, payload_state) -> None:
        """One row of presses per bay the aircraft says it has.

        A spent bay keeps its buttons and loses its presses: it says what
        happened to that payload, which buttons that vanished would not. There
        is nothing left in it to release and nothing left in it to hold.
        """
        if not payload_state.stations:
            return
        self.station_waiting_label.setVisible(False)

        for station in payload_state.stations:
            if station.name not in self.release_buttons:
                self.build_station_row(station.name)
            loaded = station.state != STATION_STATE_SPENT
            self.release_buttons[station.name].setEnabled(loaded)
            self.hold_buttons[station.name].setEnabled(loaded)

    def build_station_row(self, station_name: str) -> None:
        """Add one bay's two presses, side by side and named for that bay."""
        # "water_bottle" is a config name; the buttons say WATER BOTTLE.
        label = station_name.replace("_", " ").upper()

        release_button = command_button(DROP_RELEASE_FORMAT.format(station=label),
                                        VARIANT_CAUTION, self)
        release_button.clicked.connect(
            lambda: self.release_requested.emit(station_name))
        release_button.setVisible(self.deliveries_commandable)

        hold_button = command_button(DROP_HOLD_FORMAT.format(station=label),
                                     VARIANT_PRIMARY, self)
        hold_button.clicked.connect(
            lambda: self.hold_requested.emit(station_name))

        # RELEASE keeps most of the row: it is the press being proved, and HOLD
        # is the one that puts the bay back the way it started.
        row = QWidget(self)
        row_layout = QHBoxLayout(row)
        flush_layout(row_layout, SPACE_XS)
        row_layout.addWidget(release_button, RELEASE_BUTTON_WIDTH_SHARE)
        row_layout.addWidget(hold_button, HOLD_BUTTON_WIDTH_SHARE)

        self.release_buttons[station_name] = release_button
        self.hold_buttons[station_name] = hold_button
        self.station_layout.addWidget(row)

    # What the operator's last press came to

    def show_link(self, link_is_up: bool) -> None:
        """RTL and LAND ride the safety link, so a dead link takes them away."""
        self.return_button.setEnabled(link_is_up)
        self.land_button.setEnabled(link_is_up)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        set_state(self.status_label, state)
