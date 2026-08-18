"""The scan area and the route the Pasifik is flying over it."""

from PyQt6.QtGui import QColor, QPen, QPolygonF

from competitions.international_uav.config import (
    MAP_COLORS,
    MAP_LEG_WIDTH,
    MAP_POLYGON_WIDTH,
)


def draw_scan_area(painter, projection, polygon: list, legs: list) -> None:
    """Planned legs first, then the area outline on top of them."""
    if legs:
        painter.setPen(QPen(QColor(MAP_COLORS["scan_leg"]), MAP_LEG_WIDTH))
        painter.drawPolyline(polygon_from(projection, legs))

    if len(polygon) >= 2:
        painter.setPen(QPen(QColor(MAP_COLORS["scan_polygon"]), MAP_POLYGON_WIDTH))
        painter.drawPolygon(polygon_from(projection, polygon))


def polygon_from(projection, coordinates: list) -> QPolygonF:
    return QPolygonF(
        [projection.to_point(latitude, longitude) for latitude, longitude in coordinates]
    )
