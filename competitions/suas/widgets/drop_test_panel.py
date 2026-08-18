"""The delivery test: the countdown to a release, and the presses that drive one.

Two mechanisms, two ways of flying them, one panel — because the operator asks
the same question of both and the aircraft answers it the same way.

The winch is flown by hand, four presses in order. GO TO DROP ZONE plans the
route to the next target and hovers over it; RELEASE runs the winch on the
target underneath; RTL or LAND ends the test. Nothing happens between presses,
which is the point: a mechanism being proved for the first time should not also
be deciding when to fire.

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
from PyQt6.QtWidgets import QLabel

from competitions.suas.config import (
    DROP_COUNTDOWN_CAPTION,
    DROP_COUNTDOWN_FORMAT,
    DROP_COUNTDOWN_READY_TEXT,
    DROP_GEOMETRY_CAPTION,
    DROP_GEOMETRY_FORMAT,
    DROP_GOTO_TEXT,
    DROP_HOLD_HINT_TEXT,
    DROP_LAND_TEXT,
    DROP_PANEL_TITLE,
    DROP_RELEASE_TEXT,
    DROP_RETURN_TEXT,
    DROP_TARGET_CAPTION,
    DROP_TARGET_FORMAT,
    DROP_WAITING_TEXT,
    DROP_WATCH_ONLY_TEXT,
    MISSING_VALUE_TEXT,
)
from competitions.suas.widgets.hold_button import HoldButton
from theme import set_role, set_state
from theme.tokens import (
    ROLE_HINT,
    SCALE_DISPLAY,
    SPACE_LG,
    STATE_CAUTION,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_PRIMARY,
)
from widgets import Card, Readout


class DropTestPanel(Card):
    """What the aircraft is about to drop, and the presses that make it."""

    goto_target_requested = pyqtSignal()
    release_requested = pyqtSignal()
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

        self.goto_button = HoldButton(DROP_GOTO_TEXT, VARIANT_PRIMARY, self)
        self.release_button = HoldButton(DROP_RELEASE_TEXT, VARIANT_CAUTION, self)
        self.return_button = HoldButton(DROP_RETURN_TEXT, VARIANT_CAUTION, self)
        self.land_button = HoldButton(DROP_LAND_TEXT, VARIANT_CAUTION, self)

        self.goto_button.held.connect(self.goto_target_requested.emit)
        self.release_button.held.connect(self.release_requested.emit)
        self.return_button.held.connect(self.return_to_launch_requested.emit)
        self.land_button.held.connect(self.land_requested.emit)

        self.hint_label = QLabel(DROP_HOLD_HINT_TEXT, self)
        set_role(self.hint_label, ROLE_HINT)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.add_widget(self.countdown_reading)
        self.add_widget(self.target_reading)
        self.add_widget(self.geometry_reading)
        self.add_widget(self.reason_label)
        self.add_widget(self.goto_button)
        self.add_widget(self.release_button)
        # The two that end the flight are not neighbours of the two that run it.
        self.card_layout.addSpacing(SPACE_LG)
        self.add_widget(self.return_button)
        self.add_widget(self.land_button)
        self.add_widget(self.hint_label)
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
        """Hide the two presses the winged release has no use for.

        Disabling them would be a lie of a different shape: the buttons are not
        unavailable, they are meaningless, and a greyed-out control reads as
        something that will come back.
        """
        self.goto_button.setVisible(commandable)
        self.release_button.setVisible(commandable)
        if commandable:
            return
        self.reason_label.setText(DROP_WATCH_ONLY_TEXT)

    # What the operator's last press came to

    def show_link(self, link_is_up: bool) -> None:
        """RTL and LAND ride the safety link, so a dead link takes them away."""
        self.return_button.setEnabled(link_is_up)
        self.land_button.setEnabled(link_is_up)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        set_state(self.status_label, state)
