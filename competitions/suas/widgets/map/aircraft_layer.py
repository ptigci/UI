"""The aircraft: where it is, which way it is pointing, where it has been.

Rule 3.0.6 names the UAS position as one of the things the display must show, so
this is drawn last and drawn brightest — nothing else on the map may cover it.
The heading tick matters more than it looks: on a nadir-looking map at mission
scale, a dot alone leaves the operator guessing which way a turn is going.
"""

import math

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPen, QPolygonF

from competitions.suas.config import (
    MAP_AIRCRAFT_HEADING_LENGTH,
    MAP_AIRCRAFT_MARKER_RADIUS,
    MAP_COLORS,
    MAP_TRACK_WIDTH,
)


def draw_aircraft(painter, projection, vehicle) -> None:
    draw_track(painter, projection, vehicle.track)

    position = vehicle.position()
    if position is None:
        return

    point = projection.to_point(position[0], position[1])
    colour = QColor(MAP_COLORS["aircraft"])

    painter.setPen(QPen(colour, MAP_TRACK_WIDTH))
    painter.setBrush(colour)
    painter.drawEllipse(point, MAP_AIRCRAFT_MARKER_RADIUS, MAP_AIRCRAFT_MARKER_RADIUS)

    if vehicle.heading_degrees is not None:
        draw_heading(painter, point, vehicle.heading_degrees, colour)


def draw_heading(painter, point, heading_degrees: float, colour) -> None:
    """A tick from the marker towards where the nose is pointing."""
    heading_radians = math.radians(heading_degrees)
    tip = QPointF(
        point.x() + math.sin(heading_radians) * MAP_AIRCRAFT_HEADING_LENGTH,
        point.y() - math.cos(heading_radians) * MAP_AIRCRAFT_HEADING_LENGTH,
    )
    painter.setPen(QPen(colour, MAP_TRACK_WIDTH))
    painter.drawLine(point, tip)


def draw_track(painter, projection, track: list) -> None:
    if len(track) < 2:
        return
    painter.setPen(QPen(QColor(MAP_COLORS["track"]), MAP_TRACK_WIDTH))
    painter.drawPolyline(
        QPolygonF(
            [projection.to_point(latitude, longitude) for latitude, longitude in track]
        )
    )
