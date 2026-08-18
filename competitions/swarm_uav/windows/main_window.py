"""Main window, loaded from designer/main_window.ui.

Builds the vehicle tabs dynamically from the selected counts and routes MQTT
traffic between the controller and the panels. The look (stylesheet, tab
design) lives in the .ui file — edit it with Qt Designer.
"""

import logging
from datetime import datetime
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QEvent, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QDialog, QLabel, QMainWindow

from config import (
    BROKER_CONNECTED_TEXT,
    BROKER_DISCONNECTED_TEXT,
    CONNECTION_REFRESH_INTERVAL_MS,
    TERMINAL_TIME_FORMAT,
    WINDOW_TITLE,
)
from widgets.detection_review import Detection, DetectionReviewPanel
from windows.selection_window import SelectionResult
from competitions.swarm_uav.config import PLAN_TEXT
from competitions.swarm_uav.controller.drone_controller import DroneController
from competitions.swarm_uav.widgets.drone_panel import DronePanel
from competitions.swarm_uav.widgets.swarm_panel import SwarmPanel
from competitions.swarm_uav.windows.mission_plan_window import MissionPlanWindow
from theme import fade_in, set_state
from theme.tokens import STATE_OK, STATE_STALE

logger = logging.getLogger(__name__)

FORM_PATH = Path(__file__).resolve().parents[1] / "designer" / "main_window.ui"


class MainWindow(QMainWindow):

    # incoming MQTT data arrives on the network thread; these signals
    # hop it over to the Qt thread
    telemetry_received = pyqtSignal(int, object)
    camera_frame_received = pyqtSignal(int, object)
    state_received = pyqtSignal(int, str)
    health_received = pyqtSignal(int, object)
    clock_received = pyqtSignal(int, object)
    plan_status_received = pyqtSignal(int, object)
    qr_content_received = pyqtSignal(object)
    color_zone_received = pyqtSignal(object)
    detection_frame_received = pyqtSignal(object, object)
    esp_message_received = pyqtSignal(object)

    def __init__(self, selection: SelectionResult) -> None:
        super().__init__()
        uic.loadUi(FORM_PATH, self)

        self.drone_count = selection.drone_count
        self.vtol_count = selection.vtol_count
        drone_ids, vtol_ids = self.vehicle_ids()

        self.controller = DroneController(drone_ids, vtol_ids)
        self.vehicle_panels: dict[int, DronePanel] = {}
        self.swarm_panel: SwarmPanel | None = None
        self.detection_panel: DetectionReviewPanel | None = None
        self.camera_streams_seen: set[int] = set()
        self.disabled_cameras: set[int] = set()

        self.setWindowTitle(f"{WINDOW_TITLE} - {selection.competition.label} Mode")
        # Connected once, here: build_tabs runs again whenever the drone count
        # changes, and a second connection would fade the page twice.
        self.dronecontroltabs.currentChanged.connect(self.reveal_tab)
        self.build_tabs(drone_ids, vtol_ids)

        # the decode callbacks run on the MQTT network thread so the UI
        # thread only receives ready QImages and paints them
        self.controller.on_telemetry = self.telemetry_received.emit
        self.controller.on_camera_frame = self.decode_camera_frame
        self.controller.on_state = self.state_received.emit
        self.controller.on_health = self.health_received.emit
        self.controller.on_clock = self.clock_received.emit
        self.controller.on_plan_status = self.plan_status_received.emit
        self.controller.on_qr_content = self.qr_content_received.emit
        self.controller.on_color_zone = self.color_zone_received.emit
        self.controller.on_detection_frame = self.decode_detection_frame
        self.controller.on_esp_message = self.esp_message_received.emit
        self.telemetry_received.connect(self.handle_telemetry)
        self.camera_frame_received.connect(self.handle_camera_frame)
        self.state_received.connect(self.handle_state)
        self.health_received.connect(self.handle_health)
        self.clock_received.connect(self.handle_clock)
        self.plan_status_received.connect(self.handle_plan_status)
        self.qr_content_received.connect(self.handle_qr_content)
        self.color_zone_received.connect(self.handle_color_zone)
        self.detection_frame_received.connect(self.handle_detection_frame)
        self.esp_message_received.connect(self.handle_esp_message)

        # Broker indicator in the status bar; colours reuse the
        # connectionState styling from the main window stylesheet.
        self.broker_status_label = QLabel(self)
        self.statusbar.addPermanentWidget(self.broker_status_label)
        self.broker_connected_shown = None
        self.refresh_broker_status()

        self.connection_timer = QTimer(self)
        self.connection_timer.setInterval(CONNECTION_REFRESH_INTERVAL_MS)
        self.connection_timer.timeout.connect(self.refresh_connection_ages)
        self.connection_timer.start()

        logger.info(f"Main window ready: {len(drone_ids)} drone(s), {len(vtol_ids)} VTOL(s).")

    # Tab construction

    def vehicle_ids(self) -> tuple[list[int], list[int]]:
        """Drones take IDs 1..N, VTOLs continue the sequence."""
        drone_ids = list(range(1, self.drone_count + 1))
        first_vtol_id = self.drone_count + 1
        vtol_ids = list(range(first_vtol_id, first_vtol_id + self.vtol_count))
        return drone_ids, vtol_ids

    def build_tabs(self, drone_ids: list[int], vtol_ids: list[int]) -> None:
        if drone_ids:
            drones = [(drone_id, self.controller.vehicle_name(drone_id)) for drone_id in drone_ids]
            self.swarm_panel = SwarmPanel(drones, self.drone_count)
            self.connect_swarm_panel(self.swarm_panel)
            self.dronecontroltabs.addTab(self.swarm_panel, "SWARM")

        # the first VTOL tab hosts the object-detection browser
        if vtol_ids:
            detection_host_id = vtol_ids[0]
        else:
            detection_host_id = None

        for vehicle_id in drone_ids + vtol_ids:
            vehicle_name = self.controller.vehicle_name(vehicle_id)
            panel = DronePanel(vehicle_name, with_detection=vehicle_id == detection_host_id)
            self.connect_vehicle_panel(panel, vehicle_id)
            self.vehicle_panels[vehicle_id] = panel
            self.dronecontroltabs.addTab(panel, vehicle_name.upper())

            if panel.detection_panel is not None:
                self.detection_panel = panel.detection_panel
                self.detection_panel.approve_requested.connect(
                    lambda detection, vid=vehicle_id: self.show_result(
                        self.controller.approve_detection(detection), vid
                    )
                )
                self.detection_panel.reject_requested.connect(
                    lambda detection, vid=vehicle_id: self.show_result(
                        self.controller.cancel_detection(detection), vid
                    )
                )

        self.dronecontroltabs.setCurrentIndex(0)

    def reveal_tab(self, tab_index: int) -> None:
        """Bring the page up rather than snapping it in — one tab looks much
        like the next, and the fade says which one just arrived."""
        page = self.dronecontroltabs.widget(tab_index)
        if page is not None:
            fade_in(page)

    def apply_refresh(self, new_drone_count: int, simulation_enabled: bool) -> None:
        """Re-announce the vehicle count and mode, resize the UI to match."""
        self.show_result(self.controller.set_simulation(simulation_enabled))

        if new_drone_count == self.drone_count:
            self.show_result(self.controller.publish_vehicle_count())
            return

        self.drone_count = new_drone_count
        drone_ids, vtol_ids = self.vehicle_ids()
        confirmation = self.controller.set_vehicle_ids(drone_ids, vtol_ids)

        # tear the old tabs down and rebuild them for the new counts;
        # the detection browser dies with its host VTOL panel
        self.dronecontroltabs.clear()
        for panel in self.vehicle_panels.values():
            panel.deleteLater()
        if self.swarm_panel is not None:
            self.swarm_panel.deleteLater()
        self.vehicle_panels = {}
        self.swarm_panel = None
        self.detection_panel = None
        self.camera_streams_seen.clear()
        self.disabled_cameras.clear()

        self.build_tabs(drone_ids, vtol_ids)
        logger.info(f"UI rebuilt for {len(drone_ids)} drone(s), {len(vtol_ids)} VTOL(s).")
        self.show_result(confirmation)

    # Signal wiring

    def connect_vehicle_panel(self, panel: DronePanel, vehicle_id: int) -> None:
        controller = self.controller

        panel.arm_requested.connect(
            lambda vid=vehicle_id: self.show_result(controller.arm(vid), vid)
        )
        panel.force_arm_requested.connect(
            lambda vid=vehicle_id: self.show_result(controller.force_arm(vid), vid)
        )
        panel.disarm_requested.connect(
            lambda vid=vehicle_id: self.show_result(controller.disarm(vid), vid)
        )
        panel.force_disarm_requested.connect(
            lambda vid=vehicle_id: self.show_result(controller.force_disarm(vid), vid)
        )
        panel.takeoff_requested.connect(
            lambda altitude, vid=vehicle_id: self.show_result(
                controller.takeoff(vid, altitude), vid
            )
        )
        panel.move_requested.connect(
            lambda x, y, z, vid=vehicle_id: self.show_result(controller.move(vid, x, y, z), vid)
        )
        panel.land_requested.connect(
            lambda vid=vehicle_id: self.show_result(controller.land(vid), vid)
        )
        panel.free_requested.connect(
            lambda vid=vehicle_id: self.show_result(controller.free(vid), vid)
        )
        # The two calibrations and the PPS clock are swarm-drone features;
        # VTOL tabs hide them.
        if vehicle_id in controller.vtol_ids:
            panel.taubtn.setVisible(False)
            panel.latencybtn.setVisible(False)
            panel.clocklbl.setVisible(False)
        else:
            panel.tau_calibration_requested.connect(
                lambda vid=vehicle_id: self.show_result(
                    controller.calibrate_tau(vid), vid
                )
            )
            panel.latency_calibration_requested.connect(
                lambda props_removed, vid=vehicle_id: self.show_result(
                    controller.calibrate_latency(vid, props_removed), vid
                )
            )
        panel.emergency_requested.connect(
            lambda: self.show_result(controller.emergency_stop())
        )
        panel.camera_toggle_requested.connect(
            lambda enabled, vid=vehicle_id: self.set_camera_enabled(vid, enabled)
        )

    def connect_swarm_panel(self, panel: SwarmPanel) -> None:
        controller = self.controller

        panel.arm_requested.connect(
            lambda: self.show_result(controller.arm(controller.drone_ids))
        )
        panel.force_arm_requested.connect(
            lambda: self.show_result(controller.force_arm(controller.drone_ids))
        )
        panel.disarm_requested.connect(
            lambda: self.show_result(controller.disarm(controller.drone_ids))
        )
        panel.force_disarm_requested.connect(
            lambda: self.show_result(controller.force_disarm(controller.drone_ids))
        )
        panel.takeoff_requested.connect(
            lambda altitude: self.show_result(controller.takeoff(controller.drone_ids, altitude))
        )
        panel.move_requested.connect(
            lambda x, y, z: self.show_result(controller.move(controller.drone_ids, x, y, z))
        )
        panel.land_requested.connect(
            lambda: self.show_result(controller.land(controller.drone_ids))
        )
        panel.free_requested.connect(
            lambda: self.show_result(controller.free(controller.drone_ids))
        )
        panel.emergency_requested.connect(
            lambda: self.show_result(controller.emergency_stop())
        )

        panel.formation_requested.connect(
            lambda code, distance, angle, yaw, pitch, roll: self.show_result(
                controller.formation(code, distance, angle, yaw, pitch, roll)
            )
        )

        def start_mission1(drone_id: int) -> None:
            # spinbox value 0 = AUTO: the QR payload names the leaving drone
            if drone_id > 0:
                leaving_drone_id = drone_id
            else:
                leaving_drone_id = None
            self.show_result(controller.mission1(leaving_drone_id))

        panel.mission1_requested.connect(start_mission1)
        panel.mission2_requested.connect(
            lambda active: self.show_result(controller.mission2(active))
        )
        panel.plan_upload_requested.connect(self.open_mission_plan_window)
        panel.plan_execute_requested.connect(
            lambda: self.show_result(controller.execute_mission_plan())
        )
        panel.refresh_requested.connect(self.apply_refresh)
        panel.camera_toggle_requested.connect(self.set_camera_enabled)
        panel.set_plan_uploaded(bool(controller.mission_plan_steps))

    # Mission plan

    def open_mission_plan_window(self) -> None:
        """Edit the mission plan and upload it when the operator saves.

        Cancelling changes nothing: the swarm keeps the plan it already has.
        """
        plan_window = MissionPlanWindow(self.controller.mission_plan_steps, self)
        if plan_window.exec() != QDialog.DialogCode.Accepted:
            self.show_result(PLAN_TEXT["upload_cancelled"])
            return

        self.show_result(self.controller.upload_mission_plan(plan_window.plan_steps))
        if self.swarm_panel is not None:
            self.swarm_panel.set_plan_uploaded(True)

    def handle_plan_status(self, vehicle_id: int, payload: dict) -> None:
        """Show one drone's plan progress in the terminals."""
        status_line = self.controller.plan_status_line(payload)
        if status_line is None:
            return
        vehicle_name = self.controller.vehicle_name(vehicle_id)
        self.show_result(f"{vehicle_name} | {status_line}", vehicle_id)

    # Incoming data (already on the Qt thread here)

    def handle_telemetry(self, vehicle_id: int, payload: dict) -> None:
        panel = self.vehicle_panels.get(vehicle_id)
        if panel is None:
            return  # message from a vehicle outside the selected counts

        position = self.controller.positions.get(vehicle_id, {})
        x = position.get("x", 0.0)
        y = position.get("y", 0.0)
        z = position.get("z", 0.0)
        velocity = position.get("v", 0.0)

        # Positions land in the panel displays only; logging every update
        # would bury the mission messages in the terminals.
        panel.update_position(x, y, z, velocity)
        if self.swarm_panel is not None:
            self.swarm_panel.update_position(vehicle_id, x, y, z, velocity)

    def handle_state(self, vehicle_id: int, state_text: str) -> None:
        panel = self.vehicle_panels.get(vehicle_id)
        if panel is not None:
            panel.set_state(state_text)
        if self.swarm_panel is not None:
            self.swarm_panel.set_state(vehicle_id, state_text)
        vehicle_name = self.controller.vehicle_name(vehicle_id)
        self.show_result(f"{vehicle_name} | state | {state_text}", vehicle_id)

    def handle_health(self, vehicle_id: int, payload: dict) -> None:
        vehicle_name = self.controller.vehicle_name(vehicle_id)
        healthy = payload.get("healthy")
        details = (
            f"fix={payload.get('fix_type')} hdop={payload.get('hdop')} "
            f"sats={payload.get('satellites')}{self.clock_detail(payload)}"
        )
        if healthy:
            self.show_result(f"{vehicle_name} | GPS healthy | {details}", vehicle_id)
        else:
            self.show_result(
                f"{vehicle_name} | GPS WARNING — NOT FLIGHT READY | {details}", vehicle_id
            )

    def handle_clock(self, vehicle_id: int, payload: dict) -> None:
        disciplined = bool(payload.get("disciplined"))
        error_ms = payload.get("error_ms")
        panel = self.vehicle_panels.get(vehicle_id)
        if panel is not None:
            panel.set_clock_status(disciplined, error_ms)
        if self.swarm_panel is not None:
            self.swarm_panel.set_clock_status(vehicle_id, disciplined, error_ms)

    @staticmethod
    def clock_detail(payload: dict) -> str:
        """Clock readiness suffix for the health line; empty when the drone
        reports no clock status (synchronization off or a non-PPS clock)."""
        if "clock_disciplined" not in payload:
            return ""
        if not payload.get("clock_disciplined"):
            return " clock=NOT DISCIPLINED"
        clock_error_ms = payload.get("clock_error_ms")
        if clock_error_ms is None:
            return " clock=ok"
        return f" clock={clock_error_ms:.2f}ms"

    def handle_qr_content(self, payload: dict) -> None:
        qr_id = payload.get("qr_id")
        if self.swarm_panel is not None:
            self.swarm_panel.qr_panel.show_qr(
                qr_id, payload.get("payload"), payload.get("source_drone")
            )
        self.show_result(f"QR {qr_id} | content received from drone {payload.get('source_drone')}")

    def handle_color_zone(self, payload: dict) -> None:
        color_name = payload.get("color")
        self.show_result(
            f"Colored zone detected | color={color_name} | drone {payload.get('source_drone')} "
            f"| lat={payload.get('lat')}, lon={payload.get('lon')}",
            color=color_name,
        )

    # Frame decoding (called on the MQTT network thread)

    def decode_camera_frame(self, vehicle_id: int, image_bytes) -> None:
        if vehicle_id in self.disabled_cameras:
            return
        if image_bytes is None:
            self.camera_frame_received.emit(vehicle_id, None)
            return

        image = QImage.fromData(image_bytes)
        if image.isNull():
            logger.warning(
                f"{self.controller.vehicle_name(vehicle_id)} sent a camera frame "
                "that could not be decoded."
            )
            return
        self.camera_frame_received.emit(vehicle_id, image)

    def decode_detection_frame(self, image_bytes, payload) -> None:
        image = QImage.fromData(image_bytes)
        if image.isNull():
            logger.warning("Received an object-detection frame that could not be decoded.")
            return
        self.detection_frame_received.emit(image, payload)

    # Frame display (back on the Qt thread)

    def handle_camera_frame(self, vehicle_id: int, image: QImage | None) -> None:
        panel = self.vehicle_panels.get(vehicle_id)
        if panel is None:
            return
        vehicle_name = self.controller.vehicle_name(vehicle_id)

        if image is None:
            panel.camera_view.set_unavailable()
            if self.swarm_panel is not None:
                self.swarm_panel.set_camera_unavailable(vehicle_id)
            self.camera_streams_seen.discard(vehicle_id)
            self.show_result(f"{vehicle_name} | camera | module not available", vehicle_id)
            return

        frame = QPixmap.fromImage(image)
        panel.camera_view.show_pixmap(frame)
        if self.swarm_panel is not None:
            self.swarm_panel.show_camera_frame(vehicle_id, frame)

        # announce the stream once, not once per frame
        if vehicle_id not in self.camera_streams_seen:
            self.camera_streams_seen.add(vehicle_id)
            self.show_result(f"{vehicle_name} | camera | stream active", vehicle_id)

    def handle_detection_frame(self, image: QImage, payload: dict) -> None:
        if self.detection_panel is None:
            return
        self.detection_panel.add_detection(Detection(QPixmap.fromImage(image), payload))
        self.show_result("VTOL | object detection | frame received")

    def handle_esp_message(self, payload: dict) -> None:
        mesh_topic = payload.get("topic", "?")
        mesh_payload = payload.get("payload", {})
        self.show_result(f"ESP TX | {mesh_topic} | {mesh_payload}")

    def set_camera_enabled(self, vehicle_id: int, enabled: bool) -> None:
        """Add or remove one camera output; display-only, nothing is published."""
        if enabled:
            self.disabled_cameras.discard(vehicle_id)
        else:
            self.disabled_cameras.add(vehicle_id)
            # re-announce the stream when the camera comes back
            self.camera_streams_seen.discard(vehicle_id)

        panel = self.vehicle_panels.get(vehicle_id)
        if panel is not None:
            panel.set_camera_enabled(enabled)
        if self.swarm_panel is not None:
            self.swarm_panel.set_camera_enabled(vehicle_id, enabled)

    def refresh_connection_ages(self) -> None:
        for vehicle_id, panel in self.vehicle_panels.items():
            age_milliseconds = self.controller.milliseconds_since_last_message(vehicle_id)
            panel.set_connection_age(age_milliseconds)
            if self.swarm_panel is not None:
                self.swarm_panel.set_connection_age(vehicle_id, age_milliseconds)
        self.refresh_broker_status()

    def refresh_broker_status(self) -> None:
        connected = self.controller.mqtt_client.is_connected
        if connected == self.broker_connected_shown:
            return
        self.broker_connected_shown = connected
        if connected:
            status_text = BROKER_CONNECTED_TEXT
            connection_state = STATE_OK
        else:
            status_text = BROKER_DISCONNECTED_TEXT
            connection_state = STATE_STALE
        self.broker_status_label.setText(status_text)
        set_state(self.broker_status_label, connection_state)

    def changeEvent(self, event) -> None:
        # nobody reads the connection ages while the window is minimised,
        # so stop the refresh timer instead of waking up 10 times a second
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self.connection_timer.stop()
            elif not self.connection_timer.isActive():
                self.connection_timer.start()

    # Terminal helpers

    def show_result(
        self, message: str, vehicle_id: int | None = None, color: str | None = None
    ) -> None:
        line = self.timestamped(message)

        panel = self.vehicle_panels.get(vehicle_id)
        if panel is not None:
            panel.terminal.append_line(line, color)

        if self.swarm_panel is not None:
            self.swarm_panel.swarmterminal.append_line(line, color)
        elif vehicle_id is None:
            # no swarm tab (VTOL-only mode): global messages go to every panel
            for vehicle_panel in self.vehicle_panels.values():
                vehicle_panel.terminal.append_line(line, color)

    def timestamped(self, text: str) -> str:
        now = datetime.now()
        timestamp = f"{now.strftime(TERMINAL_TIME_FORMAT)}.{now.microsecond // 1000:03d}"
        return f"{timestamp} | {text}"
