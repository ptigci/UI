"""The Pasifik's flight numbers in a corner of the map.

Ground speed, airspeed, altitude and the waypoint it is flying to, drawn over
the picture so the operator reads them without looking away from it. A value
the aircraft has not reported is a dash, never a zero.
"""

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QBrush, QColor, QPen

from competitions.international_uav.config import (
    MAP_COLORS,
    MAP_READOUT,
    MISSING_VALUE_TEXT,
)
from theme.fonts import mono_font

LEFT_CORNER_SUFFIX = "left"
TOP_CORNER_PREFIX = "top"


def draw_flight_readout(painter, projection, vehicles) -> None:
    for vehicle in vehicles:
        if vehicle.is_pasifik:
            draw_readout_box(painter, projection, readout_lines(vehicle))
            return


def draw_readout_box(painter, projection, lines: list[str]) -> None:
    painter.save()
    painter.setFont(mono_font())
    metrics = painter.fontMetrics()
    padding = MAP_READOUT["padding"]
    line_spacing = MAP_READOUT["line_spacing"]
    width = max(metrics.horizontalAdvance(line) for line in lines) + 2 * padding
    height = len(lines) * metrics.height() + (len(lines) - 1) * line_spacing + 2 * padding
    left, top = box_origin(projection, width, height)
    box = QRectF(left, top, width, height)

    painter.setPen(QPen(QColor(MAP_COLORS["readout_border"]), 1))
    painter.setBrush(QBrush(QColor(MAP_COLORS["readout_background"])))
    painter.drawRect(box)

    painter.setPen(QPen(QColor(MAP_COLORS["readout_text"]), 1))
    baseline = top + padding + metrics.ascent()
    for line in lines:
        painter.drawText(QPointF(left + padding, baseline), line)
        baseline += metrics.height() + line_spacing
    painter.restore()


def box_origin(projection, width: float, height: float) -> tuple[float, float]:
    """Top left of the box, from the corner named in the config."""
    margin = MAP_READOUT["margin"]
    corner = MAP_READOUT["corner"]
    if corner.endswith(LEFT_CORNER_SUFFIX):
        left = margin
    else:
        left = projection.view_width - width - margin
    if corner.startswith(TOP_CORNER_PREFIX):
        top = margin
    else:
        top = projection.view_height - height - margin
    return left, top


def readout_lines(pasifik) -> list[str]:
    return [
        MAP_READOUT["ground_speed_format"].format(value=number_text(pasifik.ground_speed)),
        MAP_READOUT["airspeed_format"].format(value=number_text(pasifik.airspeed)),
        MAP_READOUT["altitude_format"].format(value=number_text(pasifik.altitude_agl)),
        MAP_READOUT["waypoint_format"].format(
            current=count_text(pasifik.waypoint), total=count_text(pasifik.waypoint_total)
        ),
    ]


def number_text(value) -> str:
    if value is None:
        return MISSING_VALUE_TEXT
    return MAP_READOUT["number_format"].format(value=value)


def count_text(value) -> str:
    if value is None:
        return MISSING_VALUE_TEXT
    return str(value)
