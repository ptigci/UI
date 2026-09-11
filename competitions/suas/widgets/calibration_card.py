"""One calibration on the CALIBRATION tab: what it is for, and START."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton

from competitions.suas.config import CALIBRATION_TEXT, CALIBRATIONS
from theme import set_role
from theme.tokens import ROLE_HINT
from widgets import Card


class CalibrationCard(Card):
    """The name, a line saying what to do, and the button that starts it."""

    # Carries the calibration's wire code.
    start_requested = pyqtSignal(str)

    def __init__(self, calibration_name: str, parent=None) -> None:
        super().__init__(parent, CALIBRATION_TEXT["titles"][calibration_name])
        self.calibration = CALIBRATIONS[calibration_name]

        self.start_button = QPushButton(CALIBRATION_TEXT["start_text"], self)
        self.start_button.clicked.connect(lambda: self.start_requested.emit(self.calibration))
        self.add_header_widget(self.start_button)

        hint = QLabel(CALIBRATION_TEXT["hints"][calibration_name], self)
        hint.setWordWrap(True)
        set_role(hint, ROLE_HINT)
        self.add_widget(hint)

    def set_available(self, available: bool) -> None:
        """Only one calibration runs at a time, so START waits for the last one."""
        self.start_button.setEnabled(available)
