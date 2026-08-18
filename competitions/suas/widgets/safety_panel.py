"""RTL and TERMINATE, and the state of the link they travel on.

Appendix B requires both to be activatable from the ground control station, and
rule 5.3.5 forbids that capability from depending on anything outside our
control. So these two controls do not publish to MQTT and do not pass through the
Raspberry Pi: they go out over the direct MAVLink link, and the panel shows that
link's health separately so nobody has to guess whether a press could even land.

The acknowledgement comes back from the autopilot, not from the click. A button
that turns green because it was pressed is a lie at the worst possible moment.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel

from competitions.suas.config import (
    SAFETY_ACKNOWLEDGED_TEXT,
    SAFETY_HOLD_HINT_TEXT,
    SAFETY_LINK_DOWN_TEXT,
    SAFETY_PANEL_TITLE,
    SAFETY_RETURN_TEXT,
    SAFETY_SENT_TEXT,
    SAFETY_TERMINATE_TEXT,
    SAFETY_TIMEOUT_TEXT,
)
from competitions.suas.widgets.hold_button import HoldButton
from theme import set_role, set_state
from theme.tokens import (
    ROLE_HINT,
    SPACE_XL,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_DANGER,
)
from widgets import Card, StatusDot


class SafetyPanel(Card):
    """The two controls that matter when something goes wrong."""

    return_to_launch_requested = pyqtSignal()
    terminate_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, SAFETY_PANEL_TITLE)

        # The link light sits in the card's title row: whether a press can even
        # land is the first thing to read here.
        self.link_dot = StatusDot(STATE_CRITICAL, self)
        self.add_header_widget(self.link_dot)

        self.return_button = HoldButton(SAFETY_RETURN_TEXT, VARIANT_CAUTION, self)
        self.terminate_button = HoldButton(SAFETY_TERMINATE_TEXT, VARIANT_DANGER, self)
        self.return_button.held.connect(self.return_to_launch_requested.emit)
        self.terminate_button.held.connect(self.terminate_requested.emit)

        self.hint_label = QLabel(SAFETY_HOLD_HINT_TEXT, self)
        set_role(self.hint_label, ROLE_HINT)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.add_widget(self.return_button)
        # The two are deliberately not side by side. TERMINATE is not a
        # neighbour anyone should reach for by accident.
        self.card_layout.addSpacing(SPACE_XL)
        self.add_widget(self.terminate_button)
        self.add_widget(self.hint_label)
        self.add_widget(self.status_label)
        self.add_stretch()

    def show_link(self, link_is_up: bool) -> None:
        """A safety link that is down is the panel's most important fact."""
        self.return_button.setEnabled(link_is_up)
        self.terminate_button.setEnabled(link_is_up)
        if link_is_up:
            self.link_dot.set_state(STATE_OK)
            return
        self.link_dot.set_state(STATE_CRITICAL)
        self.show_status(SAFETY_LINK_DOWN_TEXT, STATE_CRITICAL)

    def show_command_sent(self, command: str) -> None:
        self.show_status(f"{command} {SAFETY_SENT_TEXT}", STATE_CAUTION)

    def show_command_acknowledged(self, command: str) -> None:
        self.show_status(f"{command} {SAFETY_ACKNOWLEDGED_TEXT}", STATE_NONE)

    def show_command_timed_out(self, command: str) -> None:
        self.show_status(f"{command} {SAFETY_TIMEOUT_TEXT}", STATE_CRITICAL)

    def show_status(self, status: str, state: str) -> None:
        self.status_label.setText(status)
        set_state(self.status_label, state)
