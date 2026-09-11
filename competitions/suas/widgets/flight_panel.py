"""The FLIGHT card: the aircraft's own controls, under the mission panel.

Import a mission and start it, arm the aircraft, pick its mode. Nothing here
publishes: every click leaves as a signal and the window sends it on. The
safe modes and the plain ARM go out at once; the ones that can put the
aircraft somewhere bad ask first, and the dialog says what will happen. The
last line is what the aircraft answered.

Those dialogs are the one place this interface asks a question. They are
worth the moment they cover the map: every one of them is a press made on the
ground or on the safety pilot's word, never in the middle of a lap.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
)

from competitions.suas.config import (
    ACTION_ARM,
    ACTION_FORCE_ARM,
    ACTION_FORCE_DISARM,
    ACTION_START_MISSION,
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

        mission_row = QHBoxLayout()
        flush_layout(mission_row)
        import_button = QPushButton(FLIGHT_TEXT["import_text"], self)
        import_button.clicked.connect(self.choose_mission_file)
        mission_row.addWidget(import_button)
        start_button = QPushButton(FLIGHT_TEXT["start_text"], self)
        set_variant(start_button, VARIANT_PRIMARY)
        start_button.clicked.connect(lambda: self.request_command(ACTION_START_MISSION, "start"))
        mission_row.addWidget(start_button)
        self.add_layout(mission_row)

        arm_row = QHBoxLayout()
        flush_layout(arm_row)
        arm_button = QPushButton(FLIGHT_TEXT["arm_text"], self)
        arm_button.clicked.connect(lambda: self.command_requested.emit(ACTION_ARM))
        arm_row.addWidget(arm_button)
        force_arm_button = QPushButton(FLIGHT_TEXT["force_arm_text"], self)
        set_variant(force_arm_button, VARIANT_CAUTION)
        force_arm_button.clicked.connect(
            lambda: self.request_command(ACTION_FORCE_ARM, "force_arm")
        )
        arm_row.addWidget(force_arm_button)
        force_disarm_button = QPushButton(FLIGHT_TEXT["force_disarm_text"], self)
        set_variant(force_disarm_button, VARIANT_DANGER)
        force_disarm_button.clicked.connect(
            lambda: self.request_command(ACTION_FORCE_DISARM, "force_disarm")
        )
        arm_row.addWidget(force_disarm_button)
        self.add_layout(arm_row)

        mode_grid = QGridLayout()
        flush_layout(mode_grid)
        columns = FLIGHT_TEXT["mode_columns"]
        for index, mode_name in enumerate(FLIGHT_TEXT["mode_order"]):
            mode_button = QPushButton(FLIGHT_TEXT["mode_texts"][mode_name], self)
            mode_button.clicked.connect(lambda checked, name=mode_name: self.request_mode(name))
            mode_grid.addWidget(mode_button, index // columns, index % columns)
        self.add_layout(mode_grid)

        self.result_reading = Readout(FLIGHT_TEXT["result_caption"], parent=self)
        self.result_reading.value_label.setWordWrap(True)
        self.result_reading.set_value(FLIGHT_TEXT["result_none_text"])
        self.add_widget(self.result_reading)

    # Operator actions

    def choose_mission_file(self) -> None:
        path, chosen_filter = QFileDialog.getOpenFileName(
            self, FLIGHT_TEXT["file_dialog_title"], NO_DIRECTORY, FLIGHT_TEXT["file_filter"]
        )
        if path:
            self.mission_file_chosen.emit(path)

    def request_command(self, action: str, confirm_name: str) -> None:
        """A command that is asked about first; the texts are named after it."""
        confirmed = self.confirm(
            FLIGHT_TEXT[f"{confirm_name}_confirm_title"],
            FLIGHT_TEXT[f"{confirm_name}_confirm_question"],
        )
        if confirmed:
            self.command_requested.emit(action)

    def request_mode(self, mode_name: str) -> None:
        mode = FLIGHT_MODES[mode_name]
        if mode_name in FLIGHT_TEXT["confirmed_modes"]:
            confirmed = self.confirm(
                FLIGHT_TEXT["mode_confirm_title"].format(mode=mode),
                FLIGHT_TEXT["mode_confirm_question"],
            )
            if not confirmed:
                return
        self.mode_requested.emit(mode)

    def confirm(self, title: str, question: str) -> bool:
        answer = QMessageBox.question(
            self,
            title,
            question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    # Display

    def show_result(self, text: str, state: str = STATE_NONE) -> None:
        """The newest thing the aircraft said, in the colour of how bad it is."""
        self.result_reading.set_value(text)
        self.result_reading.set_state(state)
