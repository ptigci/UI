"""Targets on the map, coloured by what is happening to them.

The assignment line from an agent to its target is drawn here too: together
they answer "who is going where" without reading a single number.
"""

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QPen

from competitions.international_uav.config import (
    MAP_ASSIGNMENT_WIDTH,
    MAP_COLORS,
    MAP_LABEL_OFFSET,
    MAP_SELECTED_TARGET_RING,
    MAP_TARGET_COLORS,
    MAP_TARGET_MARKER_RADIUS,
)


def draw_targets(painter, projection, targets, vehicles_by_id, selected_target_id) -> None:
    for target in targets:
        draw_assignment_line(painter, projection, target, vehicles_by_id)
    for target in targets:
        draw_target(painter, projection, target, target.target_id == selected_target_id)


def draw_target(painter, projection, target, selected: bool) -> None:
    if not target.has_position():
        return

    position = projection.to_point(target.latitude, target.longitude)
    color = QColor(target_color(target))

    painter.setPen(QPen(color, 1))
    painter.setBrush(QBrush(color))
    painter.drawEllipse(position, MAP_TARGET_MARKER_RADIUS, MAP_TARGET_MARKER_RADIUS)

    if selected:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(position, MAP_SELECTED_TARGET_RING, MAP_SELECTED_TARGET_RING)

    painter.setPen(QPen(QColor(MAP_COLORS["label"]), 1))
    painter.drawText(
        QPointF(position.x() + MAP_LABEL_OFFSET, position.y() + MAP_LABEL_OFFSET),
        target.target_id,
    )


def draw_assignment_line(painter, projection, target, vehicles_by_id) -> None:
    if target.agent_id is None or not target.has_position():
        return
    agent = vehicles_by_id.get(target.agent_id)
    if agent is None or not agent.has_position():
        return

    painter.setBrush(Qt.BrushStyle.NoBrush)
    pen = QPen(QColor(MAP_COLORS["assignment_line"]), MAP_ASSIGNMENT_WIDTH)
    pen.setStyle(Qt.PenStyle.DashLine)
    painter.setPen(pen)
    painter.drawLine(
        projection.to_point(agent.latitude, agent.longitude),
        projection.to_point(target.latitude, target.longitude),
    )


def target_color(target) -> str:
    color = MAP_TARGET_COLORS.get(target.state)
    if color is None:
        return MAP_COLORS["label"]
    return color
