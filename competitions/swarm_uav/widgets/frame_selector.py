"""The camera view the operator drags a selection box on.

Frames keep arriving while the box is being drawn, so the widget freezes on
the one the box was drawn over: the band has to be measured on the picture the
operator was looking at, not on whatever came in a fifth of a second later.
Clearing the box lets the live view back in.
"""

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget

from theme import set_surface
from theme.tokens import ACCENT, AS_PANEL, BORDER_RAIL, TEXT_MUTED


class FrameSelector(QWidget):
    """Shows one drone's stream and reports the box drawn over it."""

    selection_changed = pyqtSignal()

    def __init__(self, waiting_text: str, parent=None) -> None:
        super().__init__(parent)
        set_surface(self, AS_PANEL)
        self.waiting_text = waiting_text
        self.frame_image = None
        self.frame_pixmap = None
        self.selection = QRect()
        self.drag_origin = None

    # Frames

    def show_frame(self, image) -> None:
        """Take a live frame, unless a box is being drawn or already is."""
        if self.frozen():
            return
        self.frame_image = image
        self.frame_pixmap = QPixmap.fromImage(image)
        self.update()

    def frozen(self) -> bool:
        return self.drag_origin is not None or not self.selection.isNull()

    def clear_selection(self) -> None:
        self.selection = QRect()
        self.drag_origin = None
        self.selection_changed.emit()
        self.update()

    # The box

    def mousePressEvent(self, event) -> None:
        if self.frame_pixmap is None:
            return
        self.drag_origin = event.position().toPoint()
        self.selection = QRect()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_origin is None:
            return
        self.selection = QRect(self.drag_origin, event.position().toPoint()).normalized()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self.drag_origin is None:
            return
        self.drag_origin = None
        self.selection_changed.emit()
        self.update()

    def selected_image_rect(self):
        """The box in the frame's own pixel coordinates, or None when there is none.

        The frame is drawn as large as fits, so a box on screen is several
        picture pixels wide — or a fraction of one, if the window is smaller
        than the stream.
        """
        if self.frame_image is None or self.selection.isNull():
            return None
        drawn = self.frame_rect()
        selected = self.selection.intersected(drawn)
        if selected.isEmpty():
            return None

        horizontal_scale = self.frame_image.width() / drawn.width()
        vertical_scale = self.frame_image.height() / drawn.height()
        return QRect(
            round((selected.x() - drawn.x()) * horizontal_scale),
            round((selected.y() - drawn.y()) * vertical_scale),
            max(1, round(selected.width() * horizontal_scale)),
            max(1, round(selected.height() * vertical_scale)),
        )

    # Painting

    def frame_rect(self) -> QRect:
        """Where the frame is drawn: as large as fits, aspect kept, centred."""
        drawn_size = self.frame_pixmap.size().scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio
        )
        origin = QPoint(
            (self.width() - drawn_size.width()) // 2,
            (self.height() - drawn_size.height()) // 2,
        )
        return QRect(origin, drawn_size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self.frame_pixmap is None:
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.waiting_text)
            return

        painter.drawPixmap(self.frame_rect(), self.frame_pixmap)
        if not self.selection.isNull():
            painter.setPen(QPen(QColor(ACCENT), BORDER_RAIL))
            painter.drawRect(self.selection)
