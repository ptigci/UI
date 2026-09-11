"""The aircraft: where it is, which way it is pointing, where it is going.

Rule 3.0.6 names the UAS position as one of the things the display must show, so
this is drawn last and drawn brightest — nothing else on the map may cover it.
The heading arrow matters more than it looks: on a nadir-looking map at mission
scale, a dot alone leaves the operator guessing which way a turn is going. The
dashed leg to the waypoint being flown to says where the next turn ends.
"""

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPen, QPolygonF

from competitions.suas.config import (
    MAP_AIRCRAFT_HEADING_LENGTH,
    MAP_AIRCRAFT_HEADING_WIDTH,
    MAP_AIRCRAFT_MARKER_RADIUS,
    MAP_COLORS,
    MAP_NEXT_LEG_WIDTH,
    MAP_TRACK_WIDTH,
)


def draw_aircraft(painter, projection, vehicle, next_waypoint) -> None:
    draw_track(painter, projection, vehicle.track)

    position = vehicle.position()
    if position is None:
        return

    point = projection.to_point(position[0], position[1])
    draw_next_leg(painter, projection, point, next_waypoint)

    colour = QColor(MAP_COLORS["aircraft"])
    painter.setPen(QPen(colour, MAP_TRACK_WIDTH))
    painter.setBrush(colour)
    painter.drawEllipse(point, MAP_AIRCRAFT_MARKER_RADIUS, MAP_AIRCRAFT_MARKER_RADIUS)

    if vehicle.heading_degrees is not None:
        draw_heading(painter, point, vehicle.heading_degrees, colour)


def draw_next_leg(painter, projection, point, next_waypoint) -> None:
    """A dashed line from the aircraft to the waypoint it is flying to."""
    if next_waypoint is None:
        return
    pen = QPen(QColor(MAP_COLORS["next_leg"]), MAP_NEXT_LEG_WIDTH)
    pen.setStyle(Qt.PenStyle.DashLine)
    painter.setPen(pen)
    painter.drawLine(point, projection.to_point(next_waypoint[0], next_waypoint[1]))


def draw_heading(painter, point, heading_degrees: float, colour) -> None:
    """A filled triangle from the marker towards where the nose is pointing."""
    heading_radians = math.radians(heading_degrees)
    along = QPointF(math.sin(heading_radians), -math.cos(heading_radians))
    across = QPointF(-along.y(), along.x())
    tip = point + along * MAP_AIRCRAFT_HEADING_LENGTH
    half_width = MAP_AIRCRAFT_HEADING_WIDTH / 2
    painter.setPen(QPen(colour, MAP_TRACK_WIDTH))
    painter.setBrush(colour)
    painter.drawPolygon(QPolygonF([tip, point + across * half_width, point - across * half_width]))


def draw_track(painter, projection, track: list) -> None:
    if len(track) < 2:
        return
    painter.setPen(QPen(QColor(MAP_COLORS["track"]), MAP_TRACK_WIDTH))
    painter.drawPolyline(
        QPolygonF(
            [projection.to_point(latitude, longitude) for latitude, longitude in track]
        )
    )
