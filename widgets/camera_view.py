"""Camera feed display for a single vehicle."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from config import CAMERA_UNAVAILABLE_TEXT


class CameraView(QLabel):
    """Shows the incoming MQTT camera stream, or a placeholder when there is none.

    Used as a promoted QLabel in the .ui files and created directly for the
    swarm monitor grid. Frames are stretched to fill the panel, matching the
    original design (scaledContents). Frames arrive as ready QPixmaps — the
    expensive image decoding happens off the UI thread (see MainWindow).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(CAMERA_UNAVAILABLE_TEXT)

    def show_pixmap(self, frame: QPixmap) -> None:
        self.setScaledContents(True)
        self.setPixmap(frame)

    def show_placeholder(self, text: str) -> None:
        self.setScaledContents(False)
        self.clear()
        self.setText(text)

    def set_unavailable(self) -> None:
        self.show_placeholder(CAMERA_UNAVAILABLE_TEXT)
