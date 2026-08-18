"""The empty map: a metre grid and a scale bar.

There is no online tile layer on purpose — a mission cannot depend on the
internet — so this is what sits under the mission until the ground station's
stitched mosaic arrives.
"""

import math

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPen

from competitions.international_uav.config import (
    MAP_COLORS,
    MAP_GRID_SPACING_METRES,
    MAP_SCALE_BAR_WIDTH_PIXELS,
)

SCALE_BAR_MARGIN = 16
SCALE_BAR_TICK_HEIGHT = 5
SCALE_BAR_TEXT_OFFSET = 6


def draw_grid(painter, projection) -> None:
    """A grid every few tens of metres, so distance on the map is readable."""
    spacing_pixels = MAP_GRID_SPACING_METRES * projection.pixels_per_metre
    if spacing_pixels < 8:
        return  # zoomed too far out to mean anything

    painter.setPen(QPen(QColor(MAP_COLORS["grid"]), 1))

    first_east = math.floor(
        (projection.centre_east - projection.view_width / 2 / projection.pixels_per_metre)
        / MAP_GRID_SPACING_METRES
    )
    last_east = math.ceil(
        (projection.centre_east + projection.view_width / 2 / projection.pixels_per_metre)
        / MAP_GRID_SPACING_METRES
    )
    for step in range(first_east, last_east + 1):
        x = projection.metres_to_point(step * MAP_GRID_SPACING_METRES, 0).x()
        painter.drawLine(QPointF(x, 0), QPointF(x, projection.view_height))

    first_north = math.floor(
        (projection.centre_north - projection.view_height / 2 / projection.pixels_per_metre)
        / MAP_GRID_SPACING_METRES
    )
    last_north = math.ceil(
        (projection.centre_north + projection.view_height / 2 / projection.pixels_per_metre)
        / MAP_GRID_SPACING_METRES
    )
    for step in range(first_north, last_north + 1):
        y = projection.metres_to_point(0, step * MAP_GRID_SPACING_METRES).y()
        painter.drawLine(QPointF(0, y), QPointF(projection.view_width, y))


def draw_scale_bar(painter, projection) -> None:
    """A bar of a round number of metres, in the bottom left corner."""
    if projection.pixels_per_metre <= 0:
        return

    rough_metres = MAP_SCALE_BAR_WIDTH_PIXELS / projection.pixels_per_metre
    metres = round_to_readable(rough_metres)
    bar_pixels = metres * projection.pixels_per_metre

    bottom = projection.view_height - SCALE_BAR_MARGIN
    left = SCALE_BAR_MARGIN
    right = left + bar_pixels

    painter.setPen(QPen(QColor(MAP_COLORS["scale_bar"]), 2))
    painter.drawLine(QPointF(left, bottom), QPointF(right, bottom))
    painter.drawLine(QPointF(left, bottom), QPointF(left, bottom - SCALE_BAR_TICK_HEIGHT))
    painter.drawLine(QPointF(right, bottom), QPointF(right, bottom - SCALE_BAR_TICK_HEIGHT))
    painter.drawText(
        QPointF(left, bottom - SCALE_BAR_TICK_HEIGHT - SCALE_BAR_TEXT_OFFSET), f"{metres:g} m"
    )


def round_to_readable(metres: float) -> float:
    """Nearest 1, 2 or 5 times a power of ten, so the label stays a round number."""
    if metres <= 0:
        return 1.0
    power = 10 ** math.floor(math.log10(metres))
    for step in (1, 2, 5):
        if metres <= step * power:
            return step * power
    return 10 * power
