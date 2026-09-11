"""The SUAS operations window: the map, the clock, the laps and the way out.

Rule 3.0.6 makes the layout a compliance matter rather than a preference. The map
carries the flight boundaries and the aircraft, the ribbon carries ground speed in
knots and altitude in feet AGL, and the GCS judge has to be able to see all of it
at any moment — so the map is never covered. Rule 3.3 pays 200 points for
running the mission with two operators, so everything the GCS Operator needs
in flight is on that one page, the aircraft's own controls included. The
calibrations are on a tab beside it (``dev_tab.py`` builds the tabs), used on
the bench and before takeoff and never in front of a judge; developer mode
adds the DEV and TEST tabs after it.

MQTT arrives on the network thread and the safety link on its own reader thread;
both are hopped onto the Qt thread by the signals below before any widget is
touched.

This file holds the window itself: what it does when data arrives, and what it
keeps ticking over on its own. Two halves live next door and are mixed in below,
because one file was not enough to read them in.

    window_layout.py     which panels exist and how the screen is arranged
    command_control.py   everything the operator sends — RTL, LAND, TERMINATE,
                         the delivery steps, the camera recording — and how each
                         one is confirmed
    aircraft_controls.py the FLIGHT card and the CALIBRATION tab: the mission
                         import, arming, the modes and the calibrations, and
                         what the autopilot says back into the log under the map
"""

import logging
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QEvent, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QMainWindow

from config import BROKER_CONNECTED_TEXT, BROKER_DISCONNECTED_TEXT, WINDOW_TITLE
from competitions.suas.config import (
    FLIGHT_BOUNDARY,
    MAP_FOLLOW_OFF_TEXT,
    MAP_FOLLOW_ON_TEXT,
    REFRESH_INTERVAL_MS,
    RUNWAY_PROFILE,
    active_waypoint_file,
)
from competitions.suas.controller import SafetyLink, SuasController
from competitions.suas.geometry import distance_metres, distance_to_polygon_metres, is_inside_polygon
from competitions.suas.waypoint_plan import read_waypoint_file
from competitions.suas.windows.aircraft_controls import AircraftControlsMixin
from competitions.suas.windows.command_control import CommandControlMixin
from competitions.suas.windows.dev_tab import DevTabMixin
from competitions.suas.windows.test_presses import TestPressesMixin
from competitions.suas.windows.test_tab import TestTabMixin
from competitions.suas.windows.window_layout import WindowLayoutMixin
from widgets.detection_review import Detection

logger = logging.getLogger(__name__)

FORM_PATH = Path(__file__).resolve().parents[1] / "designer" / "main_window.ui"


class SuasMainWindow(WindowLayoutMixin, CommandControlMixin, AircraftControlsMixin,
                     TestTabMixin, TestPressesMixin, DevTabMixin, QMainWindow):

    # Incoming data arrives off the Qt thread; these carry it across.
    telemetry_received = pyqtSignal()
    mission_changed = pyqtSignal()
    waypoint_changed = pyqtSignal()
    safety_heartbeat_received = pyqtSignal(str)
    safety_command_acknowledged = pyqtSignal(int)
    release_countdown_received = pyqtSignal()
    flight_command_answered = pyqtSignal(str, str)
    # The frame arrives as bytes on the MQTT thread for the same reason a
    # detection crop does: building a QPixmap is a Qt operation.
    video_frame_received = pyqtSignal(object)
    camera_changed = pyqtSignal()
    camera_command_answered = pyqtSignal(str, str)
    mission_command_answered = pyqtSignal(str, str)
    # The mosaic preview crosses as bytes, the same way a video frame does.
    stitch_state_received = pyqtSignal(object)
    route_changed = pyqtSignal()
    targets_changed = pyqtSignal()
    payload_changed = pyqtSignal()
    # The crop arrives as bytes on the MQTT thread; decoding to a QPixmap is
    # a Qt operation and has to happen on the Qt thread, so the bridge
    # carries the raw bytes across and the slot builds the picture.
    detection_received = pyqtSignal(object, object)

    # The FLIGHT and CALIBRATION tabs: the autopilot's words, the answers to
    # their presses, and where a calibration is.
    autopilot_message = pyqtSignal(int, str)
    command_result_received = pyqtSignal(str, bool, str)
    calibration_progressed = pyqtSignal(dict)
    aircraft_command_answered = pyqtSignal(str, str)
    calibration_command_answered = pyqtSignal(str, str)

    # The TEST tab's own reports, on the same hop for the same reason. The
    # sighting carries its crop as bytes, like a detection card's.
    gimbal_changed = pyqtSignal()
    media_list_changed = pyqtSignal()
    transfer_changed = pyqtSignal()
    media_file_saved = pyqtSignal(str, object)
    servos_changed = pyqtSignal()
    waypoint_watch_changed = pyqtSignal()
    mapping_progress_received = pyqtSignal()
    detector_changed = pyqtSignal()
    sighting_received = pyqtSignal(object, object)
    camera_test_answered = pyqtSignal(str, str)
    gimbal_answered = pyqtSignal(str, str)
    watch_answered = pyqtSignal(str, str)
    mapping_test_answered = pyqtSignal(str, str)
    detector_answered = pyqtSignal(str, str)
    route_answered = pyqtSignal(str, str)

    def __init__(self, selection) -> None:
        super().__init__()
        uic.loadUi(FORM_PATH, self)

        self.controller = SuasController()
        self.safety_link = SafetyLink()
        self.pending_safety_command: str | None = None
        self.pending_safety_command_elapsed_ms = 0
        self.pending_flight_command_elapsed_ms: int | None = None
        self.pending_mission_command_elapsed_ms: int | None = None
        # Which of the two survey presses is in the air, so the answer says
        # what the aircraft actually took.
        self.pending_mission_accepted_text: str = ""
        self.developer_mode = selection.developer_mode

        self.setWindowTitle(f"{WINDOW_TITLE} - {selection.competition.label}")
        self.build_layout()
        self.connect_widgets()
        self.connect_controller()
        self.load_waypoints()

        self.broker_status_label = QLabel(self)
        self.statusbar.addPermanentWidget(self.broker_status_label)
        self.broker_connected_shown = None
        self.refresh_broker_status()

        self.safety_link.start()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(REFRESH_INTERVAL_MS)
        self.refresh_timer.timeout.connect(self.refresh_live_values)
        self.refresh_timer.start()

        logger.info(f"SUAS interface ready on flight line profile '{RUNWAY_PROFILE}'.")

    # Construction

    def load_waypoints(self) -> None:
        self.map_view.show_waypoints(read_waypoint_file(active_waypoint_file()))

    # Detections

    def handle_detection(self, image_bytes: bytes, payload: dict) -> None:
        """Put one detection in front of the operator, on the Qt thread."""
        self.detection_column.add_detection(
            Detection(self.crop_pixmap(image_bytes), payload)
        )

    @staticmethod
    def crop_pixmap(image_bytes: bytes) -> QPixmap:
        """The crop as a pixmap, or an empty one when there was no picture.

        An empty pixmap is deliberate rather than a dropped card: the target is
        still real and still deliverable, and the operator can judge it from the
        class and the coordinate if the crop did not survive the link.
        """
        if not image_bytes:
            return QPixmap()
        image = QImage.fromData(image_bytes)
        if image.isNull():
            return QPixmap()
        return QPixmap.fromImage(image)

    def approve_detection(self, detection: Detection) -> None:
        self.controller.approve_detection(detection)

    def reject_detection(self, detection: Detection) -> None:
        self.controller.reject_detection(detection)

    # Operator actions

    def toggle_follow(self) -> None:
        self.map_view.set_following(not self.map_view.following_aircraft)

    def show_follow_state(self, following: bool) -> None:
        if following:
            self.follow_button.setText(MAP_FOLLOW_ON_TEXT)
        else:
            self.follow_button.setText(MAP_FOLLOW_OFF_TEXT)

    # Incoming data, already on the Qt thread

    def handle_telemetry(self) -> None:
        vehicle = self.controller.vehicle
        self.telemetry_ribbon.show_vehicle(vehicle)
        self.map_view.show_vehicle(vehicle)
        self.show_distances(vehicle)
        # The flight mode arrives with telemetry, and the mode is what makes a
        # lap legal (3.7). Leaving this to the next mission message would show
        # "AUTO held" while the pilot was already flying it by hand.
        self.show_autonomy()
        self.refresh_flying_state()

    def handle_mission_changed(self) -> None:
        lap_state = self.controller.lap_state
        self.lap_tracker.show_laps(lap_state)
        self.mission_clock.show_phase(lap_state.mission_phase)
        self.mission_panel.show_phase(lap_state.mission_phase,
                                      lap_state.mission_detail,
                                      lap_state.flight_time_left_s)
        self.show_autonomy()

    def show_autonomy(self) -> None:
        autonomy_held = self.controller.lap_state.autonomy_held(self.controller.vehicle.mode)
        self.lap_tracker.show_autonomy(autonomy_held)

    def handle_waypoint_changed(self) -> None:
        self.lap_tracker.show_progress(
            self.controller.waypoint_index,
            self.controller.waypoint_total,
            self.controller.waypoint_distance_metres,
        )
        self.telemetry_ribbon.show_waypoint_radius(self.controller.acceptance_radius_metres)
        # The autopilot reports the item it is flying TO; the map draws that
        # one larger and the ones before it as reached.
        self.map_view.show_waypoint_progress(
            self.controller.waypoint_index,
            self.controller.waypoint_total,
            self.controller.acceptance_radius_metres,
        )
        self.show_test_waypoint_progress()

    def handle_release_countdown(self) -> None:
        """Draw a fresh countdown the moment it lands, rather than on the next tick."""
        self.refresh_countdown()

    def handle_video_frame(self, image_bytes: bytes) -> None:
        """Draw one preview frame, on the Qt thread.

        A frame that will not decode is dropped rather than blanking the panel.
        The next one usually decodes, and a picture that flickers to NO PICTURE
        on one bad packet is worse than a picture that skips.
        """
        picture = self.crop_pixmap(image_bytes)
        if picture.isNull():
            return

        if self.camera_panel is not None:
            self.camera_panel.show_frame(picture)
        self.show_test_video_frame(picture)

    def handle_camera_changed(self) -> None:
        """Follow the aircraft's word on whether the camera is recording."""
        if self.camera_panel is None:
            return
        camera = self.controller.camera
        self.camera_panel.show_recording(camera.recording, camera.reason)

    def handle_stitch_state(self, image_bytes: bytes) -> None:
        """Draw where the folder stitch stands, on the Qt thread."""
        if self.mapping_panel is None:
            self.show_test_stitch(self.crop_pixmap(image_bytes))
            return
        self.mapping_panel.show_stitch(self.controller.stitch,
                                       self.crop_pixmap(image_bytes))
        self.show_test_stitch(self.crop_pixmap(image_bytes))


    def handle_route_changed(self) -> None:
        """Draw the route the aircraft is about to fly."""
        self.map_view.show_route(self.controller.route)
        self.show_test_route()

    def handle_targets_changed(self) -> None:
        """Draw every track and every denied zone."""
        tracks, zones = self.controller.targets.snapshot()
        self.map_view.show_targets(tracks, zones)

    def handle_payload_changed(self) -> None:
        self.payload_panel.show_stations(self.controller.payload)
        if self.drop_test_panel is not None:
            self.drop_test_panel.show_stations(self.controller.payload)
        self.show_test_stations()

    def show_distances(self, vehicle) -> None:
        """How far from the boundary, and how far from home."""
        position = vehicle.position()
        if position is None:
            return

        latitude, longitude = position
        self.telemetry_ribbon.show_boundary_distance(
            distance_to_polygon_metres(latitude, longitude, FLIGHT_BOUNDARY),
            is_inside_polygon(latitude, longitude, FLIGHT_BOUNDARY),
        )

        home = vehicle.home_position()
        if home is None:
            return
        self.telemetry_ribbon.show_home_distance(
            distance_metres(latitude, longitude, home[0], home[1])
        )

    # Periodic refresh

    def refresh_live_values(self) -> None:
        """The clock, the link ages and the ack timers keep moving with no new data."""
        self.mission_clock.refresh()
        self.refresh_links()
        self.refresh_safety_command()
        self.refresh_flight_command()
        self.refresh_mission_command()
        self.refresh_countdown()
        self.refresh_camera()
        self.refresh_broker_status()
        self.refresh_mapping_clock()
        self.refresh_test_pages()

    def refresh_links(self) -> None:
        safety_is_up = self.controller.links.safety_is_up()
        mission_is_up = self.controller.links.mission_is_up()
        self.telemetry_ribbon.show_links(safety_is_up, mission_is_up)
        self.safety_panel.show_link(safety_is_up)
        if self.drop_test_panel is not None:
            self.drop_test_panel.show_link(safety_is_up)

    def refresh_mapping_clock(self) -> None:
        """The stitch clock keeps counting between messages."""
        if self.mapping_panel is None:
            return
        self.mapping_panel.refresh_clock(self.controller.stitch)

    def refresh_countdown(self) -> None:
        """A countdown that stopped arriving stops being shown as a live number."""
        if self.drop_test_panel is None:
            return
        self.drop_test_panel.show_countdown(self.controller.release)

    def refresh_camera(self) -> None:
        """A feed that stopped arriving stops looking like a feed.

        Nothing tells us the link went -- frames simply stop. So the panel is
        asked on every tick whether the last one is still recent enough to be
        called live, and a frozen picture is replaced rather than left there.
        """
        camera = self.controller.camera
        if camera.picture_is_live():
            return

        self.show_test_no_picture(camera.has_had_a_picture())
        if self.camera_panel is None:
            return
        self.camera_panel.show_no_picture(camera.has_had_a_picture())

    def refresh_broker_status(self) -> None:
        connected = self.controller.mqtt_client.is_connected
        if connected == self.broker_connected_shown:
            return
        self.broker_connected_shown = connected
        if connected:
            self.broker_status_label.setText(BROKER_CONNECTED_TEXT)
        else:
            self.broker_status_label.setText(BROKER_DISCONNECTED_TEXT)

    def changeEvent(self, event) -> None:
        # The judge has to be able to see this window, so it is never minimised
        # in flight; the timer still stops if someone does it on the bench.
        super().changeEvent(event)
        if event.type() != QEvent.Type.WindowStateChange:
            return
        if self.isMinimized():
            self.refresh_timer.stop()
        elif not self.refresh_timer.isActive():
            self.refresh_timer.start()

    def closeEvent(self, event) -> None:
        self.safety_link.stop()
        super().closeEvent(event)
        self.stop_developer_sessions()
        self.close_test_logs()
