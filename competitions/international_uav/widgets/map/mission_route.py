"""The mission the Pasifik is flying: its waypoints joined in order, the one it
is flying to drawn larger, and a dashed leg from the aircraft to that one so
the operator sees where it goes next."""

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QPen, QPolygonF

from competitions.international_uav.config import (
    MAP_COLORS,
    MAP_LEG_WIDTH,
    MAP_NEXT_LEG_WIDTH,
    MAP_WAYPOINT_CURRENT_RADIUS,
    MAP_WAYPOINT_LABEL_OFFSET,
    MAP_WAYPOINT_RADIUS,
)


def draw_mission_route(painter, projection, waypoints: list, current_sequence, vehicles) -> None:
    if not waypoints:
        return
    points = {
        waypoint.sequence: projection.to_point(waypoint.latitude, waypoint.longitude)
        for waypoint in waypoints
    }

    painter.setPen(QPen(QColor(MAP_COLORS["waypoint"]), MAP_LEG_WIDTH))
    painter.drawPolyline(QPolygonF([points[waypoint.sequence] for waypoint in waypoints]))

    draw_next_leg(painter, projection, points.get(current_sequence), vehicles)
    for waypoint in waypoints:
        is_current = waypoint.sequence == current_sequence
        draw_waypoint(painter, points[waypoint.sequence], waypoint.sequence, is_current)


def draw_next_leg(painter, projection, current_point, vehicles) -> None:
    """A dashed line from the Pasifik to the waypoint it is flying to."""
    if current_point is None:
        return
    for vehicle in vehicles:
        if vehicle.is_pasifik and vehicle.has_position():
            pen = QPen(QColor(MAP_COLORS["next_leg"]), MAP_NEXT_LEG_WIDTH)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(projection.to_point(vehicle.latitude, vehicle.longitude), current_point)
            return


def draw_waypoint(painter, point: QPointF, sequence: int, is_current: bool) -> None:
    if is_current:
        color = QColor(MAP_COLORS["waypoint_current"])
        radius = MAP_WAYPOINT_CURRENT_RADIUS
    else:
        color = QColor(MAP_COLORS["waypoint"])
        radius = MAP_WAYPOINT_RADIUS
    painter.setPen(QPen(color, 1))
    painter.setBrush(QBrush(color))
    painter.drawEllipse(point, radius, radius)

    painter.setPen(QPen(QColor(MAP_COLORS["label"]), 1))
    painter.drawText(
        QPointF(point.x() + radius + MAP_WAYPOINT_LABEL_OFFSET, point.y() + radius),
        str(sequence),
    )
