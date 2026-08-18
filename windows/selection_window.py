"""Startup dialog, loaded from designer/selector.ui.

Competition choice and vehicle counts live on the same screen. Only the
count fields the chosen competition needs are shown, and the continue
button stays disabled until a competition is picked.

The buttons take their text from the competition list in config, so a
competition is named in one place and appears here by itself.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QButtonGroup, QDialog, QSizePolicy

from config import (
    COMPETITIONS,
    Competition,
    DRONE_COUNT_DEFAULT,
    DRONE_COUNT_MAX,
    DRONE_COUNT_MIN,
    SELECTION_CONTINUE_TEXT,
    SELECTION_DRONE_COUNT_TEXT,
    SELECTION_SUBTITLE,
    SELECTION_TITLE,
    SELECTION_VEHICLES_TITLE,
    SELECTION_VTOL_COUNT_TEXT,
    VTOL_COUNT_DEFAULT,
    VTOL_COUNT_MAX,
    VTOL_COUNT_MIN,
    WINDOW_TITLE,
)
from theme import fade_in, space_layout
from theme.tokens import SPACE_LG, SPACE_XL

logger = logging.getLogger(__name__)

FORM_PATH = Path(__file__).resolve().parents[1] / "designer" / "selector.ui"

# selector.ui button object name -> competition key in config/selection.toml
BUTTON_COMPETITION_KEYS = {
    "btn_suru": "suru_iha",
    "btn_suas": "suas",
    "btn_uluslararasi": "uluslararasi",
}


@dataclass
class SelectionResult:
    competition: Competition
    drone_count: int
    vtol_count: int


class SelectionWindow(QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        uic.loadUi(FORM_PATH, self)
        self.setWindowTitle(f"{WINDOW_TITLE} - Competition Selection")
        self.selected_competition: Competition | None = None

        self.build_texts()
        self.build_spacing()
        self.build_competition_buttons()

        self.build_count_field(self.dronecountSpinBox, DRONE_COUNT_MIN, DRONE_COUNT_MAX)
        self.dronecountSpinBox.setValue(DRONE_COUNT_DEFAULT)
        self.build_count_field(self.vtolcountSpinBox, VTOL_COUNT_MIN, VTOL_COUNT_MAX)
        self.vtolcountSpinBox.setValue(VTOL_COUNT_DEFAULT)
        self.align_count_fields()

        # both count rows stay hidden until the competition decides what is needed
        self.set_counts_visible(drones_visible=False, vtols_visible=False)
        self.continuebtn.clicked.connect(self.accept)

    # Construction

    def build_texts(self) -> None:
        self.titlelabel.setText(SELECTION_TITLE)
        self.subtitlelabel.setText(SELECTION_SUBTITLE)
        self.countsheading.setText(SELECTION_VEHICLES_TITLE)
        self.dronecountlabel.setText(SELECTION_DRONE_COUNT_TEXT)
        self.vtolcountlabel.setText(SELECTION_VTOL_COUNT_TEXT)
        self.continuebtn.setText(SELECTION_CONTINUE_TEXT)

    def build_spacing(self) -> None:
        space_layout(self.dialoglayout, SPACE_XL, SPACE_LG)
        space_layout(self.competitionlayout)
        space_layout(self.countslayout)

    def build_count_field(self, count_field, minimum: int, maximum: int) -> None:
        """A count is two digits; letting it stretch across the card looks broken."""
        count_field.setRange(minimum, maximum)
        count_field.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def align_count_fields(self) -> None:
        """The two ranges have different digit counts, so their boxes would
        otherwise sit at different widths one under the other."""
        count_fields = (self.dronecountSpinBox, self.vtolcountSpinBox)
        widest = max(field.sizeHint().width() for field in count_fields)
        for field in count_fields:
            field.setFixedWidth(widest)

    def build_competition_buttons(self) -> None:
        self.competition_buttons = QButtonGroup(self)
        for button_name, competition_key in BUTTON_COMPETITION_KEYS.items():
            button = getattr(self, button_name)
            button.setText(self.label_for(competition_key))
            self.competition_buttons.addButton(button)
            button.clicked.connect(
                lambda checked, key=competition_key: self.on_competition_selected(key)
            )

    def label_for(self, competition_key: str) -> str:
        competition = self.competition_for(competition_key)
        if competition is None:
            return competition_key
        return competition.label

    def competition_for(self, competition_key: str) -> Competition | None:
        return next((entry for entry in COMPETITIONS if entry.key == competition_key), None)

    # Selection

    def selection(self) -> SelectionResult:
        """Only valid after the dialog was accepted."""
        competition = self.selected_competition
        if competition.uses_drones:
            drone_count = self.dronecountSpinBox.value()
        else:
            drone_count = 0
        if competition.uses_vtols:
            vtol_count = self.vtolcountSpinBox.value()
        else:
            vtol_count = 0
        return SelectionResult(competition, drone_count, vtol_count)

    def on_competition_selected(self, competition_key: str) -> None:
        competition = self.competition_for(competition_key)
        if competition is None:
            logger.error(f"Competition '{competition_key}' is missing from config/selection.toml.")
            return
        self.selected_competition = competition
        self.set_counts_visible(
            drones_visible=competition.uses_drones,
            vtols_visible=competition.uses_vtols,
        )
        self.continuebtn.setEnabled(True)

    def set_counts_visible(self, drones_visible: bool, vtols_visible: bool) -> None:
        self.dronecountlabel.setVisible(drones_visible)
        self.dronecountSpinBox.setVisible(drones_visible)
        self.vtolcountlabel.setVisible(vtols_visible)
        self.vtolcountSpinBox.setVisible(vtols_visible)
        # An empty card is worse than no card, so the whole thing goes.
        self.countscard.setVisible(drones_visible or vtols_visible)
        self.adjustSize()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        fade_in(self)
