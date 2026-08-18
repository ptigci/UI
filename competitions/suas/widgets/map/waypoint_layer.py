"""The waypoint lap, with each acceptance radius drawn to scale.

Appendix B has the safety inspector check that the waypoint threshold is
configured under 50 ft. A number in a corner satisfies that on paper; a circle
drawn at its true size, next to a boundary drawn at its true size, satisfies it
in a way the inspector can see at a glance. So the radius here is real geometry
scaled by the projection, not a fixed pixel ring.

The radius comes from the autopilot over telemetry, not from our config, because
the value that matters is the one the autopilot is actually using.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen

from competitions.suas.config import (
    MAP_COLORS,
    MAP_LABEL_OFFSET,
    MAP_WAYPOINT_MARKER_RADIUS,
    MAP_WAYPOINT_RADIUS_WIDTH,
)


def draw_waypoints(painter, projection, waypoints: list, reached_index, radius_metres) -> None:
    """Numbered waypoints joined in order, each with its acceptance circle."""
    if not waypoints:
        return

    draw_legs(painter, projection, waypoints)
    for position, (latitude, longitude) in enumerate(waypoints, start=1):
        point = projection.to_point(latitude, longitude)
        if reached_index is not None and position <= reached_index:
            colour = QColor(MAP_COLORS["waypoint_reached"])
        else:
            colour = QColor(MAP_COLORS["waypoint"])
        draw_acceptance_circle(painter, projection, point, radius_metres)
        draw_marker(painter, point, colour, position)


def draw_legs(painter, projection, waypoints: list) -> None:
    painter.setPen(QPen(QColor(MAP_COLORS["waypoint"]), MAP_WAYPOINT_RADIUS_WIDTH))
    previous_point = None
    for latitude, longitude in waypoints:
        point = projection.to_point(latitude, longitude)
        if previous_point is not None:
            painter.drawLine(previous_point, point)
        previous_point = point


def draw_acceptance_circle(painter, projection, point, radius_metres) -> None:
    if radius_metres is None:
        return
    radius_pixels = radius_metres * projection.pixels_per_metre()
    if radius_pixels < 1:
        return
    painter.setPen(QPen(QColor(MAP_COLORS["waypoint_radius"]), MAP_WAYPOINT_RADIUS_WIDTH))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(point, radius_pixels, radius_pixels)


def draw_marker(painter, point, colour, position: int) -> None:
    painter.setPen(QPen(colour, MAP_WAYPOINT_RADIUS_WIDTH))
    painter.setBrush(colour)
    painter.drawEllipse(point, MAP_WAYPOINT_MARKER_RADIUS, MAP_WAYPOINT_MARKER_RADIUS)

    painter.setPen(QPen(QColor(MAP_COLORS["label"])))
    painter.drawText(point.x() + MAP_LABEL_OFFSET, point.y(), str(position))
