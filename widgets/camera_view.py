"""Camera feed display for a single vehicle."""

import time

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from config import (
    CAMERA_STALE_AFTER_MS,
    CAMERA_STALE_CHECK_INTERVAL_MS,
    CAMERA_STALE_TEXT,
    CAMERA_UNAVAILABLE_TEXT,
)
from theme import set_state
from theme.tokens import STATE_NONE, STATE_STALE


class CameraView(QLabel):
    """Shows the incoming MQTT camera stream, or a placeholder when there is none.

    Used as a promoted QLabel in the .ui files and created directly for the
    swarm monitor grid. Frames are stretched to fill the panel, matching the
    original design (scaledContents). Frames arrive as ready QPixmaps — the
    expensive image decoding happens off the UI thread (see MainWindow).

    A stream that stops says so. Nothing else would: the last frame keeps
    sitting there, and a frozen picture of a field looks exactly like a live
    one, so the operator has no way to tell a dead link from a still scene.
    A single saved picture is shown with show_still instead, because a picture
    that was never live cannot go stale.

    A frame never widens the window it arrives in. See minimumSizeHint.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(CAMERA_UNAVAILABLE_TEXT)

        self.last_frame_monotonic = None
        self.stale_timer = QTimer(self)
        self.stale_timer.setInterval(CAMERA_STALE_CHECK_INTERVAL_MS)
        self.stale_timer.timeout.connect(self.check_staleness)

    def show_pixmap(self, frame: QPixmap) -> None:
        self.last_frame_monotonic = time.monotonic()
        set_state(self, STATE_NONE)
        self.paint_pixmap(frame)
        if not self.stale_timer.isActive():
            self.stale_timer.start()

    def show_still(self, picture: QPixmap) -> None:
        """Show one picture that is not part of a stream, so it never ages."""
        self.stale_timer.stop()
        self.last_frame_monotonic = None
        set_state(self, STATE_NONE)
        self.paint_pixmap(picture)

    def show_placeholder(self, text: str) -> None:
        self.stale_timer.stop()
        self.last_frame_monotonic = None
        set_state(self, STATE_NONE)
        self.paint_text(text)

    def set_unavailable(self) -> None:
        self.show_placeholder(CAMERA_UNAVAILABLE_TEXT)

    def check_staleness(self) -> None:
        """Replace the last frame with how long ago it arrived, once it is old.

        The frame goes rather than being labelled over, because a picture that
        is no longer true is worse than no picture at all.
        """
        age_ms = (time.monotonic() - self.last_frame_monotonic) * 1000
        if age_ms < CAMERA_STALE_AFTER_MS:
            return
        set_state(self, STATE_STALE)
        self.paint_text(CAMERA_STALE_TEXT.format(seconds=int(age_ms / 1000)))

    def minimumSizeHint(self) -> QSize:
        """A picture asks for no room of its own; it fits whatever it is given.

        A QLabel holding a pixmap reports the whole picture as its minimum
        size, so the first 640 px frame to arrive pushed the panel, its column
        and the window past the edge of the screen, and the operator had to
        scroll sideways to see the rest of the mission. Frames are scaled into
        the space the layout has, so that minimum was never real. Text still
        asks for the room it needs to be read.
        """
        if self.pixmap().isNull():
            return super().minimumSizeHint()
        return QSize(0, 0)

    def paint_pixmap(self, picture: QPixmap) -> None:
        self.setScaledContents(True)
        self.setPixmap(picture)

    def paint_text(self, text: str) -> None:
        self.setScaledContents(False)
        self.clear()
        self.setText(text)
