"""Draws the step arrows for a number field, because Qt will not draw both.

Fusion paints its own arrows only while the up and down buttons are unstyled.
Give either of them a shape — even one rounded corner — and Qt takes the
subcontrol over and paints nothing inside it. Rounded buttons therefore have to
bring their own glyph, and a stylesheet can only point at a file.

So the two triangles are painted here, from the same token as every other piece
of text, and cached next to the running application. The colour still lives in
config/theme.toml: these are derived at load time like the hover and pressed
shades, not assets somebody has to keep in step with the palette.
"""

from pathlib import Path

from PyQt6.QtCore import QPoint, QStandardPaths, Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap, QPolygon

from theme.tokens import SPIN_ARROW_SIZE, TEXT_PRIMARY

POINTING_UP = "up"
POINTING_DOWN = "down"

# Drawn at several times the final size and scaled down, which is the cheapest
# way to get a clean edge on a shape this small.
SUPERSAMPLE = 4


def arrow_path(direction: str) -> str:
    """Write the arrow if it is not there yet, and give back its file path."""
    cache_directory = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
    )
    cache_directory.mkdir(parents=True, exist_ok=True)
    # The colour is in the name, so a rebranded theme never reads a stale arrow.
    file_path = cache_directory / f"spin-{direction}-{TEXT_PRIMARY.lstrip('#')}.png"
    if not file_path.exists():
        draw_arrow(direction).save(str(file_path))
    # Qt reads a stylesheet url with forward slashes on every platform.
    return file_path.as_posix()


def draw_arrow(direction: str) -> QPixmap:
    size = SPIN_ARROW_SIZE * SUPERSAMPLE
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(Qt.GlobalColor.transparent))

    if direction == POINTING_UP:
        corners = [QPoint(0, size), QPoint(size, size), QPoint(size // 2, 0)]
    else:
        corners = [QPoint(0, 0), QPoint(size, 0), QPoint(size // 2, size)]

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(TEXT_PRIMARY))
    painter.drawPolygon(QPolygon(corners))
    painter.end()

    return pixmap.scaled(
        SPIN_ARROW_SIZE,
        SPIN_ARROW_SIZE,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
