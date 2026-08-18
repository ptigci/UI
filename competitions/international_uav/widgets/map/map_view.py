"""The map: scan area, vehicles, tracks, targets and who is flying to what.

It draws whatever the controller has; nothing here talks to MQTT. The view
fits itself to the mission until the operator zooms or pans, and a double
click gives that automatic fit back.
"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from competitions.international_uav.config import (
    MAP_COLORS,
    MAP_TARGET_MARKER_RADIUS,
    MAP_ZOOM_STEP,
)
from competitions.international_uav.widgets.map.map_background import draw_grid, draw_scale_bar
from competitions.international_uav.widgets.map.map_projection import MapProjection
from competitions.international_uav.widgets.map.scan_overlay import draw_scan_area
from competitions.international_uav.widgets.map.target_markers import draw_targets
from competitions.international_uav.widgets.map.vehicle_markers import draw_vehicles

logger = logging.getLogger(__name__)

# How close to a marker a click counts as hitting it.
TARGET_CLICK_TOLERANCE_PIXELS = MAP_TARGET_MARKER_RADIUS + 6
WHEEL_NOTCH_DEGREES = 120


class MapView(QWidget):
    """Bird's eye view of the mission area."""

    target_clicked = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.projection = MapProjection()
        self.vehicles: list = []
        self.targets: list = []
        self.scan_polygon: list = []
        self.scan_legs: list = []
        self.selected_target_id: str | None = None

        # Automatic fitting stops the moment the operator takes over.
        self.auto_fit = True
        self.drag_origin = None

        self.setMinimumSize(320, 240)
        self.setMouseTracking(False)

    def show_mission(self, vehicles: list, targets: list, scan_polygon: list, scan_legs: list) -> None:
        self.vehicles = vehicles
        self.targets = targets
        self.scan_polygon = scan_polygon
        self.scan_legs = scan_legs
        self.update()

    def select_target(self, target_id: str | None) -> None:
        self.selected_target_id = target_id
        self.update()

    def fit_to_mission(self) -> None:
        self.auto_fit = True
        self.update()

    # Painting

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(MAP_COLORS["background"]))

        self.projection.set_view_size(self.width(), self.height())
        self.prepare_projection()

        draw_grid(painter, self.projection)
        draw_scan_area(painter, self.projection, self.scan_polygon, self.scan_legs)
        draw_targets(
            painter,
            self.projection,
            self.targets,
            {vehicle.vehicle_id: vehicle for vehicle in self.vehicles},
            self.selected_target_id,
        )
        draw_vehicles(painter, self.projection, self.vehicles)
        draw_scale_bar(painter, self.projection)
        painter.end()

    def prepare_projection(self) -> None:
        """Set the origin from the first position seen, then fit if allowed."""
        coordinates = self.mission_coordinates()
        if not coordinates:
            return
        if not self.projection.origin_set:
            first_latitude, first_longitude = coordinates[0]
            self.projection.set_origin(first_latitude, first_longitude)
        if self.auto_fit:
            self.projection.fit(coordinates)

    def mission_coordinates(self) -> list:
        """Everything that has to stay on screen while the map fits itself."""
        coordinates = list(self.scan_polygon)
        coordinates.extend(
            (vehicle.latitude, vehicle.longitude)
            for vehicle in self.vehicles
            if vehicle.has_position()
        )
        coordinates.extend(
            (target.latitude, target.longitude)
            for target in self.targets
            if target.has_position()
        )
        return coordinates

    # Operator input

    def wheelEvent(self, event) -> None:
        notches = event.angleDelta().y() / WHEEL_NOTCH_DEGREES
        if not notches:
            return
        self.auto_fit = False
        self.projection.zoom_by(MAP_ZOOM_STEP ** notches)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        clicked_target_id = self.target_at(event.position())
        if clicked_target_id is not None:
            self.select_target(clicked_target_id)
            self.target_clicked.emit(clicked_target_id)
            return
        self.drag_origin = event.position()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_origin is None:
            return
        movement = event.position() - self.drag_origin
        self.drag_origin = event.position()
        self.auto_fit = False
        self.projection.pan_by(movement.x(), movement.y())
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        self.drag_origin = None

    def mouseDoubleClickEvent(self, event) -> None:
        self.fit_to_mission()

    def target_at(self, click_position):
        """The target under the click, if any is close enough."""
        for target in self.targets:
            if not target.has_position():
                continue
            marker = self.projection.to_point(target.latitude, target.longitude)
            distance = (marker - click_position)
            if distance.manhattanLength() <= TARGET_CLICK_TOLERANCE_PIXELS * 2:
                return target.target_id
        return None
