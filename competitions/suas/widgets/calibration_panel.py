"""The CALIBRATION tab: five cards to start from, one card that reports back.

The aircraft runs the calibration and says where it is on
suas/calibration/progress; this page only shows that and asks for the next
step. NEXT is only offered while the aircraft is waiting for it, and nothing
can be started while one is running. Nothing here publishes: every click
leaves as a signal and the window sends it on.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from competitions.suas.config import (
    CALIBRATION_ACTION_CANCEL,
    CALIBRATION_ACTION_NEXT,
    CALIBRATION_ACTION_START,
    CALIBRATION_STATES,
    CALIBRATION_TEXT,
)
from competitions.suas.widgets.calibration_card import CalibrationCard
from theme import flush_layout, set_role, set_variant, space_layout
from theme.tokens import (
    ROLE_HINT,
    ROLE_READOUT,
    ROLE_SUBHEADING,
    STATE_IDLE,
    VARIANT_CAUTION,
)
from widgets import Card, StatusPill

# The pill's colour per reported state, keyed by the wire code.
PILL_STATES = {
    CALIBRATION_STATES[name]: state for name, state in CALIBRATION_TEXT["pill_states"].items()
}
ACTIVE_STATES = (CALIBRATION_STATES["running"], CALIBRATION_STATES["waiting"])


class CalibrationPanel(QWidget):
    """One card per calibration on the left, the progress card on the right."""

    # The calibration's wire code and the action's.
    calibration_requested = pyqtSignal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.running_calibration: str | None = None

        page_layout = QHBoxLayout(self)
        space_layout(page_layout)
        cards_layout = QVBoxLayout()
        flush_layout(cards_layout)
        self.cards: list[CalibrationCard] = []
        for calibration_name in CALIBRATION_TEXT["order"]:
            card = CalibrationCard(calibration_name, self)
            card.start_requested.connect(self.start_calibration)
            cards_layout.addWidget(card)
            self.cards.append(card)
        cards_layout.addStretch()
        page_layout.addLayout(cards_layout, CALIBRATION_TEXT["cards_stretch"])
        page_layout.addWidget(self.build_progress_card(), CALIBRATION_TEXT["progress_stretch"])

        self.show_idle()

    def build_progress_card(self) -> Card:
        card = Card(self, CALIBRATION_TEXT["progress_title"])
        self.state_pill = StatusPill(self)
        card.add_header_widget(self.state_pill)

        self.name_label = QLabel(self)
        set_role(self.name_label, ROLE_SUBHEADING)
        card.add_widget(self.name_label)
        # The step is the sentence the operator follows; the detail is whatever
        # number came with it, monospaced so a list of channel ranges lines up.
        self.step_label = QLabel(self)
        self.step_label.setWordWrap(True)
        set_role(self.step_label, ROLE_HINT)
        card.add_widget(self.step_label)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(
            CALIBRATION_TEXT["percent_minimum"], CALIBRATION_TEXT["percent_maximum"]
        )
        card.add_widget(self.progress_bar)
        self.detail_label = QLabel(self)
        self.detail_label.setWordWrap(True)
        set_role(self.detail_label, ROLE_READOUT)
        card.add_widget(self.detail_label)

        button_row = QHBoxLayout()
        flush_layout(button_row)
        self.next_button = QPushButton(CALIBRATION_TEXT["next_text"], self)
        self.next_button.clicked.connect(lambda: self.request_action(CALIBRATION_ACTION_NEXT))
        button_row.addWidget(self.next_button)
        self.cancel_button = QPushButton(CALIBRATION_TEXT["cancel_text"], self)
        set_variant(self.cancel_button, VARIANT_CAUTION)
        self.cancel_button.clicked.connect(lambda: self.request_action(CALIBRATION_ACTION_CANCEL))
        button_row.addWidget(self.cancel_button)
        button_row.addStretch()
        card.add_layout(button_row)
        card.add_stretch()
        return card

    # Operator actions

    def start_calibration(self, calibration: str) -> None:
        self.calibration_requested.emit(calibration, CALIBRATION_ACTION_START)

    def request_action(self, action: str) -> None:
        """NEXT or CANCEL for whichever calibration the aircraft is running."""
        if self.running_calibration is None:
            return
        self.calibration_requested.emit(self.running_calibration, action)

    # Display

    def show_idle(self) -> None:
        self.state_pill.show_status(CALIBRATION_TEXT["idle_pill_text"], STATE_IDLE)
        self.name_label.setText("")
        self.step_label.setText(CALIBRATION_TEXT["idle_text"])
        self.progress_bar.reset()
        self.detail_label.setText("")
        self.set_running(None, waiting=False)

    def show_progress(self, progress: dict) -> None:
        """What the aircraft just reported, as the controller handed it over."""
        state = progress["state"]
        self.state_pill.show_status(state.upper(), PILL_STATES.get(state, STATE_IDLE))
        self.name_label.setText(
            CALIBRATION_TEXT["running_format"].format(calibration=progress["calibration"])
        )
        self.step_label.setText(progress["step"])
        if progress["percent"] is None:
            self.progress_bar.reset()
        else:
            self.progress_bar.setValue(int(progress["percent"]))
        self.detail_label.setText(progress["detail"])

        if state in ACTIVE_STATES:
            running = progress["calibration"]
        else:
            running = None
        self.set_running(running, state == CALIBRATION_STATES["waiting"])

    def set_running(self, calibration: str | None, waiting: bool) -> None:
        """Which buttons make sense right now."""
        self.running_calibration = calibration
        active = calibration is not None
        self.next_button.setEnabled(waiting)
        self.cancel_button.setEnabled(active)
        for card in self.cards:
            card.set_available(not active)
