"""The route the aircraft is about to fly, drawn before it flies it.

The aircraft plans its own way to each target -- a leg out of the hover, an
arc, a straight run-in -- and says so before it uploads it. Drawing the plan
is how the operator sees, ahead of time, that the aircraft is about to head
for the right place and not for the fence.
"""

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPen

from competitions.suas.config import (
    MAP_COLORS,
    MAP_LABEL_OFFSET,
    MAP_ROUTE_MARKER_RADIUS,
    MAP_ROUTE_WIDTH,
    ROUTE_HOVER_LABEL,
    ROUTE_RELEASE_LABEL,
)


def draw_route(painter, projection, route) -> None:
    """The planned legs, the hover point and the release point."""
    if route is None or not route.has_route():
        return

    painter.setPen(QPen(QColor(MAP_COLORS["route"]), MAP_ROUTE_WIDTH,
                        Qt.PenStyle.DashLine))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    previous_point = None
    for latitude, longitude in route.waypoints:
        point = projection.to_point(latitude, longitude)
        if previous_point is not None:
            painter.drawLine(previous_point, point)
        previous_point = point

    draw_point(painter, projection, route.hover_point,
               MAP_COLORS["route_hover"], ROUTE_HOVER_LABEL)
    draw_point(painter, projection, route.release_point,
               MAP_COLORS["route_release"], ROUTE_RELEASE_LABEL)


def draw_point(painter, projection, coordinate, colour: str, label: str) -> None:
    if coordinate is None:
        return
    point = projection.to_point(coordinate[0], coordinate[1])
    painter.setPen(QPen(QColor(colour), MAP_ROUTE_WIDTH))
    painter.setBrush(QColor(colour))
    painter.drawEllipse(point, MAP_ROUTE_MARKER_RADIUS, MAP_ROUTE_MARKER_RADIUS)
    painter.setPen(QPen(QColor(MAP_COLORS["label"])))
    painter.drawText(QPointF(point.x() + MAP_LABEL_OFFSET, point.y()), label)
