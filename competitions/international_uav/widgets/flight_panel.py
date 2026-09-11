"""The FLIGHT card: the Pasifik's own controls.

Import a mission and start it, arm the aircraft, pick its mode. Nothing here
moves an agent, and nothing here publishes: every click leaves as a signal and
the window sends it on, on the click and with nothing to say yes to. The last
line is what the aircraft answered.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QGridLayout, QPushButton

from competitions.international_uav.config import (
    AIRCRAFT_COMMAND_ARM,
    AIRCRAFT_COMMAND_FORCE_ARM,
    AIRCRAFT_COMMAND_FORCE_DISARM,
    AIRCRAFT_COMMAND_START_MISSION,
    FLIGHT_MODES,
    FLIGHT_TEXT,
)
from theme import flush_layout, set_variant
from theme.tokens import STATE_NONE, VARIANT_CAUTION, VARIANT_DANGER, VARIANT_PRIMARY
from widgets import Card, Readout

NO_DIRECTORY = ""


class FlightPanel(Card):
    """IMPORT MISSION, START MISSION, arming, the modes, and the last answer."""

    mission_file_chosen = pyqtSignal(str)
    command_requested = pyqtSignal(str)
    mode_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, FLIGHT_TEXT["title"])

        import_button = QPushButton(FLIGHT_TEXT["import_text"], self)
        import_button.clicked.connect(self.choose_mission_file)
        start_button = QPushButton(FLIGHT_TEXT["start_text"], self)
        set_variant(start_button, VARIANT_PRIMARY)
        start_button.clicked.connect(
            lambda: self.command_requested.emit(AIRCRAFT_COMMAND_START_MISSION)
        )
        self.add_button_rows([import_button, start_button], FLIGHT_TEXT["mission_columns"])

        arm_button = QPushButton(FLIGHT_TEXT["arm_text"], self)
        arm_button.clicked.connect(lambda: self.command_requested.emit(AIRCRAFT_COMMAND_ARM))
        force_arm_button = QPushButton(FLIGHT_TEXT["force_arm_text"], self)
        set_variant(force_arm_button, VARIANT_CAUTION)
        force_arm_button.clicked.connect(
            lambda: self.command_requested.emit(AIRCRAFT_COMMAND_FORCE_ARM)
        )
        force_disarm_button = QPushButton(FLIGHT_TEXT["force_disarm_text"], self)
        set_variant(force_disarm_button, VARIANT_DANGER)
        force_disarm_button.clicked.connect(
            lambda: self.command_requested.emit(AIRCRAFT_COMMAND_FORCE_DISARM)
        )
        self.add_button_rows(
            [arm_button, force_arm_button, force_disarm_button], FLIGHT_TEXT["arm_columns"]
        )

        mode_buttons = []
        for mode_name in FLIGHT_TEXT["mode_order"]:
            mode_button = QPushButton(FLIGHT_TEXT["mode_texts"][mode_name], self)
            mode_button.clicked.connect(
                lambda checked, name=mode_name: self.mode_requested.emit(FLIGHT_MODES[name])
            )
            mode_buttons.append(mode_button)
        self.add_button_rows(mode_buttons, FLIGHT_TEXT["mode_columns"])

        self.result_reading = Readout(FLIGHT_TEXT["result_caption"], parent=self)
        self.result_reading.value_label.setWordWrap(True)
        self.result_reading.set_value(FLIGHT_TEXT["result_none_text"])
        self.add_widget(self.result_reading)

    def add_button_rows(self, buttons: list, columns: int) -> None:
        """Lay one group of buttons out in rows; the last takes the rest of its row.

        A grid rather than a row, because the card is as wide as the side
        column and a row of three labels does not fit in it unclipped.
        """
        grid = QGridLayout()
        flush_layout(grid)
        for index, button in enumerate(buttons):
            row, column = divmod(index, columns)
            span = 1
            if index == len(buttons) - 1:
                span = columns - column
            grid.addWidget(button, row, column, 1, span)
        self.add_layout(grid)

    # Operator actions

    def choose_mission_file(self) -> None:
        path, chosen_filter = QFileDialog.getOpenFileName(
            self, FLIGHT_TEXT["file_dialog_title"], NO_DIRECTORY, FLIGHT_TEXT["file_filter"]
        )
        if path:
            self.mission_file_chosen.emit(path)

    # Display

    def show_result(self, text: str, state: str = STATE_NONE) -> None:
        """The newest thing the aircraft said, in the colour of how bad it is."""
        self.result_reading.set_value(text)
        self.result_reading.set_state(state)
