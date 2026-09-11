"""The map. Rule 3.0.6 makes this widget the reason we are allowed to fly.

It shows the flight boundary, both search boundaries, the runways, the waypoint
lap with its acceptance radii, and the aircraft with its track — always, with
nothing covering it and no way to tab it away. If the judge cannot see it we are
told to land, so this widget has no modes, no dialogs and no full-screen states.

Imagery comes from a local MBTiles file and nowhere else. Panning releases the
follow-the-aircraft behaviour instead of fighting the operator, and says so, so
the aircraft is never quietly off screen.
"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from competitions.suas.config import (
    FLIGHT_BOUNDARY,
    MAP_COLORS,
    MAP_TILES_MISSING_TEXT,
    MAP_ZOOM_STEP,
    tile_file_path,
)
from competitions.suas.widgets.map.aircraft_layer import draw_aircraft
from competitions.suas.widgets.map.boundary_layer import draw_boundaries
from competitions.suas.widgets.map.flight_readout import draw_flight_readout
from competitions.suas.widgets.map.map_projection import MapProjection
from competitions.suas.widgets.map.route_layer import draw_route
from competitions.suas.widgets.map.target_layer import draw_targets
from competitions.suas.widgets.map.tile_layer import TileLayer, draw_tiles
from competitions.suas.widgets.map.waypoint_layer import draw_waypoints
from theme import set_surface
from theme.tokens import AS_MAP

logger = logging.getLogger(__name__)

WHEEL_DEGREES_PER_STEP = 120.0
TILE_WARNING_MARGIN = 12

# A press and release further apart than this was a pan, not a click on a place.
CLICK_TOLERANCE_PIXELS = 4


class MapView(QWidget):
    """Draws the mission. Owns the projection; owns no mission state."""

    coordinate_clicked = pyqtSignal(float, float)
    follow_changed = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        set_surface(self, AS_MAP)
        self.setMouseTracking(True)

        self.projection = MapProjection()
        self.tile_layer = TileLayer(tile_file_path())

        self.vehicle = None
        self.waypoints: list = []
        # The mission item the autopilot is flying to, and how many there are.
        self.current_waypoint_index: int | None = None
        self.waypoint_total: int | None = None
        self.acceptance_radius_metres: float | None = None
        self.route = None
        self.tracks: list = []
        self.zones: list = []

        self.following_aircraft = True
        self.fitted_once = False
        self.drag_origin = None
        self.press_origin = None

    # What to draw

    def show_vehicle(self, vehicle) -> None:
        self.vehicle = vehicle
        if self.following_aircraft and vehicle is not None and vehicle.has_position():
            self.projection.set_centre(vehicle.latitude, vehicle.longitude)
        self.update()

    def show_waypoints(self, waypoints: list) -> None:
        self.waypoints = waypoints
        self.update()

    def show_waypoint_progress(self, current_index, total, acceptance_radius_metres) -> None:
        self.current_waypoint_index = current_index
        self.waypoint_total = total
        self.acceptance_radius_metres = acceptance_radius_metres
        self.update()

    def current_waypoint(self):
        """The place the aircraft is flying to, if the lap has such an item."""
        if self.current_waypoint_index is None:
            return None
        position = self.current_waypoint_index - 1
        if position < 0 or position >= len(self.waypoints):
            return None
        return self.waypoints[position]

    def show_route(self, route) -> None:
        """The route the aircraft announced it is about to fly."""
        self.route = route
        self.update()

    def show_targets(self, tracks: list, zones: list) -> None:
        """Every target the aircraft believes in, and the ground it may not use."""
        self.tracks = tracks
        self.zones = zones
        self.update()

    def set_following(self, following: bool) -> None:
        self.following_aircraft = following
        self.follow_changed.emit(following)
        if following:
            self.recentre_on_aircraft()

    def recentre_on_aircraft(self) -> None:
        if self.vehicle is not None and self.vehicle.has_position():
            self.projection.set_centre(self.vehicle.latitude, self.vehicle.longitude)
        self.update()

    def fit_flight_boundary(self) -> None:
        self.projection.fit(FLIGHT_BOUNDARY)
        self.update()

    # Painting

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(MAP_COLORS["background"]))

        self.projection.set_view_size(self.width(), self.height())
        if not self.fitted_once and self.width() > 0:
            # Open on the whole flight area, so the first thing anyone sees is
            # the boundary they are being judged against.
            self.projection.fit(FLIGHT_BOUNDARY)
            self.fitted_once = True

        tiles_drawn = draw_tiles(painter, self.projection, self.tile_layer)
        draw_boundaries(painter, self.projection)
        draw_waypoints(
            painter,
            self.projection,
            self.waypoints,
            self.current_waypoint_index,
            self.acceptance_radius_metres,
        )
        draw_targets(painter, self.projection, self.tracks, self.zones)
        draw_route(painter, self.projection, self.route)
        if self.vehicle is not None:
            draw_aircraft(painter, self.projection, self.vehicle, self.current_waypoint())
        draw_flight_readout(
            painter, self.projection, self.vehicle,
            self.current_waypoint_index, self.waypoint_total,
        )

        if tiles_drawn == 0:
            self.draw_tile_warning(painter)
        painter.end()

    def draw_tile_warning(self, painter) -> None:
        """No imagery is a flight-blocking problem, so it is said on the map itself.

        This fires for a missing file and equally for a file that simply has
        nothing at this zoom level — the second is the one that would otherwise
        pass for a working map with an empty background.
        """
        painter.setPen(QColor(MAP_COLORS["flight_boundary"]))
        painter.drawText(
            TILE_WARNING_MARGIN,
            TILE_WARNING_MARGIN + painter.fontMetrics().ascent(),
            MAP_TILES_MISSING_TEXT,
        )

    # Operator input

    def wheelEvent(self, event) -> None:
        steps = event.angleDelta().y() / WHEEL_DEGREES_PER_STEP
        self.projection.zoom_by(steps * MAP_ZOOM_STEP)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.drag_origin = event.position()
        self.press_origin = event.position()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_origin is None:
            return
        movement = event.position() - self.drag_origin
        self.drag_origin = event.position()
        self.projection.pan_by(movement.x(), movement.y())
        # Panning is the operator saying they want to look elsewhere. Follow
        # releases rather than snapping the view back a moment later.
        if self.following_aircraft:
            self.set_following(False)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        press_origin = self.press_origin
        self.drag_origin = None
        self.press_origin = None
        if press_origin is None or event.button() != Qt.MouseButton.LeftButton:
            return

        # A release that ended a pan is not a click on a place. Only a press and
        # release in roughly the same spot means "here".
        travelled = event.position() - press_origin
        if abs(travelled.x()) > CLICK_TOLERANCE_PIXELS:
            return
        if abs(travelled.y()) > CLICK_TOLERANCE_PIXELS:
            return

        latitude, longitude = self.projection.to_coordinate(event.position())
        self.coordinate_clicked.emit(latitude, longitude)
