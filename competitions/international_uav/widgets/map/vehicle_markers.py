"""Vehicles on the map: where they have been, where they are, where they point."""

import math

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QBrush, QColor, QPen, QPolygonF

from competitions.international_uav.config import (
    MAP_COLORS,
    MAP_LABEL_OFFSET,
    MAP_TRACK_WIDTH,
    MAP_VEHICLE_HEADING_LENGTH,
    MAP_VEHICLE_MARKER_RADIUS,
)


def draw_vehicles(painter, projection, vehicles) -> None:
    for vehicle in vehicles:
        draw_track(painter, projection, vehicle)
    for vehicle in vehicles:
        draw_vehicle(painter, projection, vehicle)


def draw_track(painter, projection, vehicle) -> None:
    track = vehicle.track_points()
    if len(track) < 2:
        return
    painter.setPen(QPen(QColor(MAP_COLORS["track"]), MAP_TRACK_WIDTH))
    painter.drawPolyline(
        QPolygonF([projection.to_point(latitude, longitude) for latitude, longitude in track])
    )


def draw_vehicle(painter, projection, vehicle) -> None:
    if not vehicle.has_position():
        return

    position = projection.to_point(vehicle.latitude, vehicle.longitude)
    color = QColor(vehicle_color(vehicle))

    painter.setPen(QPen(color, 1))
    painter.setBrush(QBrush(color))
    painter.drawEllipse(position, MAP_VEHICLE_MARKER_RADIUS, MAP_VEHICLE_MARKER_RADIUS)

    if vehicle.heading is not None:
        painter.drawLine(position, heading_point(position, vehicle.heading))

    painter.setPen(QPen(QColor(MAP_COLORS["label"]), 1))
    painter.drawText(
        QPointF(position.x() + MAP_LABEL_OFFSET, position.y() - MAP_LABEL_OFFSET), vehicle.title
    )


def vehicle_color(vehicle) -> str:
    if vehicle.is_stale():
        return MAP_COLORS["vehicle_stale"]
    if vehicle.is_pasifik:
        return MAP_COLORS["pasifik"]
    return MAP_COLORS["agent"]


def heading_point(position: QPointF, heading_degrees: float) -> QPointF:
    """Tip of the heading line: 0° is north, angles grow clockwise."""
    heading_radians = math.radians(heading_degrees)
    return QPointF(
        position.x() + math.sin(heading_radians) * MAP_VEHICLE_HEADING_LENGTH,
        position.y() - math.cos(heading_radians) * MAP_VEHICLE_HEADING_LENGTH,
    )
