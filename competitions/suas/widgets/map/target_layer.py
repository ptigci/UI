"""The targets the aircraft believes in, and the ground the operator denied.

Each track is a marker with its class and, once decided, its colour says
what the operator said about it. A blacklist zone is a circle at its true
size: a denial closes that ground for that class, and the operator should be
able to see how much ground that was.
"""

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPen

from competitions.suas.config import (
    MAP_BLACKLIST_WIDTH,
    MAP_COLORS,
    MAP_LABEL_OFFSET,
    MAP_TARGET_MARKER_RADIUS,
    TARGET_DECISION_APPROVED,
    TARGET_DECISION_DELIVERED,
    TARGET_DECISION_DENIED,
    TARGET_LABEL_FORMAT,
)


def draw_targets(painter, projection, tracks: list, zones: list) -> None:
    for zone in zones:
        draw_zone(painter, projection, zone)
    for track in tracks:
        draw_track(painter, projection, track)


def draw_zone(painter, projection, zone) -> None:
    radius_pixels = zone.radius_metres * projection.pixels_per_metre()
    if radius_pixels < 1:
        return
    point = projection.to_point(zone.latitude, zone.longitude)
    painter.setPen(QPen(QColor(MAP_COLORS["blacklist"]), MAP_BLACKLIST_WIDTH,
                        Qt.PenStyle.DotLine))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(point, radius_pixels, radius_pixels)


def draw_track(painter, projection, track) -> None:
    point = projection.to_point(track.latitude, track.longitude)
    colour = QColor(colour_for(track.decision))
    painter.setPen(QPen(colour, MAP_BLACKLIST_WIDTH))
    painter.setBrush(colour)
    painter.drawEllipse(point, MAP_TARGET_MARKER_RADIUS, MAP_TARGET_MARKER_RADIUS)

    painter.setPen(QPen(QColor(MAP_COLORS["label"])))
    painter.drawText(
        QPointF(point.x() + MAP_LABEL_OFFSET, point.y() - MAP_LABEL_OFFSET),
        TARGET_LABEL_FORMAT.format(target_class=track.target_class,
                                   track_id=track.track_id, score=track.score),
    )


def colour_for(decision: str) -> str:
    if decision == TARGET_DECISION_APPROVED:
        return MAP_COLORS["target_approved"]
    if decision == TARGET_DECISION_DELIVERED:
        return MAP_COLORS["target_delivered"]
    if decision == TARGET_DECISION_DENIED:
        return MAP_COLORS["target_denied"]
    return MAP_COLORS["target_pending"]
