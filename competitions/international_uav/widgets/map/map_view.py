"""The map: the scanned ground, vehicles, tracks, targets and who flies to what.

It draws whatever the controller has; nothing here talks to MQTT. The view
fits itself to the mission until the operator zooms or pans, and a double
click gives that automatic fit back.

Under everything else is the mosaic the ground station builds out of the
Pasifik's scan, which grows while the aircraft flies. It is what makes the right
button mean something: the operator can see a victim the detector missed, point
at them, and the click comes back out of the projection as a coordinate the
swarm can be sent to.
"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from competitions.international_uav.config import (
    MAP_COLORS,
    MAP_TARGET_MARKER_RADIUS,
    MAP_WAITING_TEXT,
    MAP_ZOOM_STEP,
)
from competitions.international_uav.widgets.map.flight_readout import draw_flight_readout
from competitions.international_uav.widgets.map.map_background import draw_grid, draw_scale_bar
from competitions.international_uav.widgets.map.map_projection import MapProjection
from competitions.international_uav.widgets.map.mission_route import draw_mission_route
from competitions.international_uav.widgets.map.mosaic_layer import MosaicLayer, draw_mosaic
from competitions.international_uav.widgets.map.pending_mark import (
    draw_pending_mark,
    target_answering,
)
from competitions.international_uav.widgets.map.target_markers import draw_targets
from competitions.international_uav.widgets.map.vehicle_markers import draw_vehicles

logger = logging.getLogger(__name__)

# How close to a marker a click counts as hitting it.
TARGET_CLICK_TOLERANCE_PIXELS = MAP_TARGET_MARKER_RADIUS + 6
WHEEL_NOTCH_DEGREES = 120


class MapView(QWidget):
    """Bird's eye view of the mission area."""

    target_clicked = pyqtSignal(str)
    # Where on the ground the operator pointed, when he asks for a target there.
    ground_marked = pyqtSignal(float, float)
    # The target the ground station made of that mark, once it says so.
    mark_answered = pyqtSignal(str)
    # A mark the map had nowhere to put, so the operator is told rather than
    # left watching a right click do nothing.
    mark_refused = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.projection = MapProjection()
        self.mosaic = MosaicLayer()
        self.vehicles: list = []
        self.targets: list = []
        # The Pasifik's mission, and the sequence number of the item it flies to.
        self.waypoints: list = []
        self.current_sequence: int | None = None
        self.selected_target_id: str | None = None
        # Where the operator marked a victim, until the ground station answers.
        self.pending_mark: tuple[float, float] | None = None

        # Automatic fitting stops the moment the operator takes over.
        self.auto_fit = True
        self.drag_origin = None

        self.setMinimumSize(320, 240)
        self.setMouseTracking(False)

    def show_mission(self, vehicles: list, targets: list, waypoints: list, current_sequence) -> None:
        self.vehicles = vehicles
        self.targets = targets
        self.waypoints = waypoints
        self.current_sequence = current_sequence
        self.update()

    def show_map_tile(self, payload: dict) -> None:
        """Take one tile of the growing mosaic and repaint if it is new."""
        if self.mosaic.add_tile(**payload):
            self.update()

    def select_target(self, target_id: str | None) -> None:
        self.selected_target_id = target_id
        self.update()

    def show_pending_mark(self, latitude: float, longitude: float) -> None:
        """Stand a mark where the operator pointed, so the click has an answer.

        It stays there until the ground station replies with a target, which is
        also what says the mark got through: one left on the map is one nobody
        has acted on.
        """
        self.pending_mark = (latitude, longitude)
        self.update()

    def settle_pending_mark(self) -> None:
        """Take the mark down once the target it became is on the map.

        Called when a target message arrives, not on every repaint: a mark is
        only answered by the ground station, never by the interface hoping.
        """
        target = target_answering(self.pending_mark, self.targets, self.projection)
        if target is None:
            return
        self.pending_mark = None
        self.mark_answered.emit(target.target_id)

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

        draw_mosaic(painter, self.projection, self.mosaic)
        draw_grid(painter, self.projection)
        draw_mission_route(
            painter, self.projection, self.waypoints, self.current_sequence, self.vehicles
        )
        draw_targets(
            painter,
            self.projection,
            self.targets,
            {vehicle.vehicle_id: vehicle for vehicle in self.vehicles},
            self.selected_target_id,
        )
        draw_vehicles(painter, self.projection, self.vehicles)
        draw_pending_mark(painter, self.projection, self.pending_mark)
        draw_flight_readout(painter, self.projection, self.vehicles)
        draw_scale_bar(painter, self.projection)
        if self.mosaic.is_empty():
            self.draw_waiting_notice(painter)
        painter.end()

    def draw_waiting_notice(self, painter) -> None:
        """Say the map is waiting, so an empty grid is not read as empty ground."""
        painter.setPen(QColor(MAP_COLORS["label"]))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, MAP_WAITING_TEXT)

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
        coordinates = [(waypoint.latitude, waypoint.longitude) for waypoint in self.waypoints]
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
        coordinates.extend(self.mosaic.corners())
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
        if event.button() == Qt.MouseButton.RightButton:
            self.mark_ground_at(event.position())
            return
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

    def mark_ground_at(self, click_position) -> None:
        """Ask for a target where the operator pointed.

        Refused until the map has an origin, which a tile, a vehicle, a target
        or the mission's waypoints all give it. Before any of them the map is drawn around
        a default centre nobody surveyed, and a target placed on it would send an
        agent to a coordinate nobody chose.
        """
        if not self.projection.origin_set:
            logger.warning("The map has no position yet; there is nothing to mark.")
            self.mark_refused.emit()
            return
        latitude, longitude = self.projection.to_coordinate(click_position)
        self.ground_marked.emit(latitude, longitude)

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
