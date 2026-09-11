"""The spot the operator right-clicked, until the ground station answers it.

Marking a victim is a round trip: the coordinate goes out on ui/targets/manual
and comes back as a target of its own. Nothing stood on the map in between, so a
mark the operator had to wait for looked exactly like one that was lost. This is
what stands there until the answer arrives, and what recognises the answer when
it does.
"""

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPen

from competitions.international_uav.config import (
    MAP_COLORS,
    MAP_MARK_MATCH_RADIUS_METRES,
    MAP_PENDING_MARK_RADIUS,
    MAP_PENDING_MARK_WIDTH,
)


def draw_pending_mark(painter, projection, mark) -> None:
    """A ring and a cross where the operator pointed, over everything else."""
    if mark is None:
        return

    latitude, longitude = mark
    position = projection.to_point(latitude, longitude)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(MAP_COLORS["pending_mark"]), MAP_PENDING_MARK_WIDTH))
    painter.drawEllipse(position, MAP_PENDING_MARK_RADIUS, MAP_PENDING_MARK_RADIUS)
    painter.drawLine(
        QPointF(position.x() - MAP_PENDING_MARK_RADIUS, position.y()),
        QPointF(position.x() + MAP_PENDING_MARK_RADIUS, position.y()),
    )
    painter.drawLine(
        QPointF(position.x(), position.y() - MAP_PENDING_MARK_RADIUS),
        QPointF(position.x(), position.y() + MAP_PENDING_MARK_RADIUS),
    )


def target_answering(mark, targets, projection):
    """The target the ground station made of this mark, or None while it waits.

    The mark is answered by the target standing on it, which is the nearest one
    inside the match radius — the ground station puts a marked target at the
    coordinate it was sent, so its own is far closer than any neighbour. A vetoed
    target never answers: the operator dropped that one, and the mark is a new
    victim in the same place.
    """
    if mark is None:
        return None

    mark_east, mark_north = projection.to_metres(*mark)
    answering = None
    shortest_distance = MAP_MARK_MATCH_RADIUS_METRES
    for target in targets:
        if not target.has_position() or target.is_vetoed():
            continue
        east, north = projection.to_metres(target.latitude, target.longitude)
        distance = math.hypot(east - mark_east, north - mark_north)
        if distance <= shortest_distance:
            answering = target
            shortest_distance = distance
    return answering
