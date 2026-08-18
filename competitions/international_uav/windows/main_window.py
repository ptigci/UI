"""Main operations window of the Uluslararası İHA interface.

Three columns under a mission bar: the vehicles and their links on the left,
the map and the log in the middle, the targets and the detection review on the
right. Everything that arrives from MQTT lands here first, on the Qt thread,
and is handed to the widget that shows it.
"""

import logging
import time
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QEvent, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QMainWindow, QSplitter, QVBoxLayout, QWidget

from config import (
    BROKER_CONNECTED_TEXT,
    BROKER_DISCONNECTED_TEXT,
    WINDOW_TITLE,
)
from widgets.detection_review import Detection
from competitions.international_uav.config import (
    AGENT_TITLE_FORMAT,
    CENTRE_COLUMN_STRETCH,
    DETECTION_APPROVED_FORMAT,
    DETECTION_COLUMN_WIDTH,
    DETECTION_PANEL_STRETCH,
    DETECTION_REJECTED_FORMAT,
    LEFT_COLUMN_STRETCH,
    LINK_HEALTH_STRETCH,
    LOG_STRETCH,
    MAP_STRETCH,
    PASIFIK_TITLE,
    REFRESH_INTERVAL_MS,
    RIGHT_COLUMN_STRETCH,
    SIDE_COLUMN_WIDTH,
    TARGET_PANEL_STRETCH,
    VEHICLE_LIST_STRETCH,
)
from competitions.international_uav.controller import PASIFIK_VEHICLE_ID, MissionController
from competitions.international_uav.models import VehicleState
from competitions.international_uav.widgets.detection_column import DetectionColumn
from competitions.international_uav.widgets.link_health_panel import LinkHealthPanel
from competitions.international_uav.widgets.log_panel import LogPanel
from competitions.international_uav.widgets.map import MapView
from competitions.international_uav.widgets.mission_bar import MissionBar
from competitions.international_uav.widgets.target_panel import TargetPanel
from competitions.international_uav.widgets.vehicle_list_panel import VehicleListPanel
from theme import flush_layout, space_layout
from theme.layout import NO_SPACING
from theme.tokens import SPACE_LG

logger = logging.getLogger(__name__)

FORM_PATH = Path(__file__).resolve().parents[1] / "designer" / "main_window.ui"

MILLISECONDS_PER_SECOND = 1000


class InternationalMainWindow(QMainWindow):

    # incoming MQTT data arrives on the network thread; these signals hop it
    # over to the Qt thread
    vehicle_changed = pyqtSignal(str)
    targets_changed = pyqtSignal()
    detection_received = pyqtSignal(object, object)
    health_changed = pyqtSignal()
    mission_changed = pyqtSignal()
    command_acknowledged = pyqtSignal(str, str)

    def __init__(self, selection) -> None:
        super().__init__()
        uic.loadUi(FORM_PATH, self)

        self.vehicles = build_vehicles(selection)
        self.controller = MissionController(
            self.vehicles[0], [vehicle for vehicle in self.vehicles[1:]]
        )
        self.mission_start_monotonic = time.monotonic()

        self.setWindowTitle(f"{WINDOW_TITLE} - {selection.competition.label} Mode")
        self.build_layout()
        self.connect_widgets()
        self.connect_controller()

        self.broker_status_label = QLabel(self)
        self.statusbar.addPermanentWidget(self.broker_status_label)
        self.broker_connected_shown = None
        self.refresh_broker_status()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(REFRESH_INTERVAL_MS)
        self.refresh_timer.timeout.connect(self.refresh_live_values)
        self.refresh_timer.start()

        logger.info(f"Interface ready for {len(self.vehicles) - 1} agent(s) and the Pasifik.")

    # Construction

    def build_layout(self) -> None:
        self.mission_bar = MissionBar(self)
        self.vehicle_list = VehicleListPanel(self.vehicles, self)
        self.link_health = LinkHealthPanel(self)
        self.map_view = MapView(self)
        self.log_panel = LogPanel(self)
        self.target_panel = TargetPanel(self)
        self.detection_column = DetectionColumn(self)

        left_column = QWidget(self)
        left_layout = QVBoxLayout(left_column)
        flush_layout(left_layout)
        left_layout.addWidget(self.vehicle_list, VEHICLE_LIST_STRETCH)
        left_layout.addWidget(self.link_health, LINK_HEALTH_STRETCH)
        left_column.setMinimumWidth(SIDE_COLUMN_WIDTH)

        centre_column = QSplitter(Qt.Orientation.Vertical, self)
        centre_column.addWidget(self.map_view)
        centre_column.addWidget(self.log_panel)
        centre_column.setStretchFactor(0, MAP_STRETCH)
        centre_column.setStretchFactor(1, LOG_STRETCH)

        right_column = QSplitter(Qt.Orientation.Vertical, self)
        right_column.addWidget(self.target_panel)
        right_column.addWidget(self.detection_column)
        right_column.setStretchFactor(0, TARGET_PANEL_STRETCH)
        right_column.setStretchFactor(1, DETECTION_PANEL_STRETCH)
        right_column.setMinimumWidth(DETECTION_COLUMN_WIDTH)

        columns = QSplitter(Qt.Orientation.Horizontal, self)
        columns.addWidget(left_column)
        columns.addWidget(centre_column)
        columns.addWidget(right_column)
        # the map is the part worth the space when the window is resized
        columns.setStretchFactor(0, LEFT_COLUMN_STRETCH)
        columns.setStretchFactor(1, CENTRE_COLUMN_STRETCH)
        columns.setStretchFactor(2, RIGHT_COLUMN_STRETCH)
        # The handle is the gap between panels, and it is the same gap the
        # whole application uses.
        columns.setHandleWidth(SPACE_LG)

        # A splitter draws no margin of its own, so the breathing room around
        # the three columns comes from the widget holding it.
        workspace = QWidget(self)
        workspace_layout = QVBoxLayout(workspace)
        space_layout(workspace_layout)
        workspace_layout.addWidget(columns)

        # The mission bar runs edge to edge under the title bar.
        flush_layout(self.rootlayout, NO_SPACING)
        self.rootlayout.addWidget(self.mission_bar)
        self.rootlayout.addWidget(workspace)

    def connect_widgets(self) -> None:
        self.mission_bar.dispatch_requested.connect(self.dispatch_swarm)
        self.mission_bar.hold_requested.connect(self.hold_mission)
        self.mission_bar.resume_requested.connect(self.resume_mission)
        self.mission_bar.abort_requested.connect(self.abort_mission)
        self.mission_bar.start_recording_requested.connect(self.start_recording)
        self.mission_bar.stop_recording_requested.connect(self.stop_recording)

        self.detection_column.approve_requested.connect(self.approve_detection)
        self.detection_column.reject_requested.connect(self.reject_detection)

        self.target_panel.veto_requested.connect(self.veto_target)
        self.target_panel.requeue_requested.connect(self.requeue_target)
        self.target_panel.target_selected.connect(self.map_view.select_target)
        self.map_view.target_clicked.connect(self.target_panel.select_target)

    def connect_controller(self) -> None:
        # the decode work runs on the MQTT network thread so the UI thread
        # only receives ready images and paints them
        self.controller.on_vehicle_changed = self.vehicle_changed.emit
        self.controller.on_targets_changed = self.targets_changed.emit
        self.controller.on_detection = self.decode_detection
        self.controller.on_health_changed = self.health_changed.emit
        self.controller.on_mission_changed = self.mission_changed.emit
        self.controller.on_command_ack = self.command_acknowledged.emit

        self.vehicle_changed.connect(self.handle_vehicle_changed)
        self.targets_changed.connect(self.handle_targets_changed)
        self.detection_received.connect(self.handle_detection)
        self.health_changed.connect(self.handle_health_changed)
        self.mission_changed.connect(self.handle_mission_changed)
        self.command_acknowledged.connect(self.handle_command_acknowledged)

    # Operator decisions

    def approve_detection(self, detection: Detection) -> None:
        """The moment a picture becomes a place the swarm flies to."""
        self.controller.approve_detection(detection)
        self.log_panel.append(
            DETECTION_APPROVED_FORMAT.format(
                label=detection.label(),
                latitude=detection.latitude(),
                longitude=detection.longitude(),
            )
        )

    def reject_detection(self, detection: Detection) -> None:
        self.controller.reject_detection(detection)
        self.log_panel.append(
            DETECTION_REJECTED_FORMAT.format(
                label=detection.label(), detection_id=detection.detection_id()
            )
        )

    def veto_target(self, target_id: str) -> None:
        self.controller.veto_target(target_id)
        self.log_panel.append(f"Target {target_id} vetoed by the operator.")

    def requeue_target(self, target_id: str) -> None:
        self.controller.requeue_target(target_id)
        self.log_panel.append(f"Target {target_id} put back in the pool.")

    def dispatch_swarm(self) -> None:
        """The click that puts the swarm in the air."""
        self.controller.dispatch_swarm()
        self.log_panel.append(
            "SEND DRONES sent: every approved target is being assigned. "
            "The ground station refuses while the Pasifik is still flying."
        )

    def hold_mission(self) -> None:
        self.controller.hold_mission()
        self.mission_bar.set_holding(True)
        self.log_panel.append("HOLD sent to every agent.")

    def resume_mission(self) -> None:
        self.controller.resume_mission()
        self.mission_bar.set_holding(False)
        self.log_panel.append("RESUME sent to every agent.")

    def abort_mission(self) -> None:
        self.controller.abort_mission()
        self.log_panel.append("ABORT sent: every vehicle returns and lands.")

    def start_recording(self) -> None:
        self.controller.start_recording()
        self.log_panel.append(
            "RECORD sent. The bar says REC once the Pasifik reports that its "
            "camera is being written to the card."
        )

    def stop_recording(self) -> None:
        self.controller.stop_recording()
        self.log_panel.append("STOP RECORDING sent to the Pasifik.")

    # Incoming data (already on the Qt thread here)

    def handle_vehicle_changed(self, vehicle_id: str) -> None:
        self.vehicle_list.refresh_vehicle(vehicle_id)
        self.refresh_map()

    def handle_targets_changed(self) -> None:
        self.target_panel.show_targets(list(self.controller.targets.values()))
        self.refresh_map()

    def handle_detection(self, image: QImage, payload: dict) -> None:
        self.detection_column.add_detection(Detection(QPixmap.fromImage(image), payload))
        self.log_panel.append("Detection received, waiting for a verdict.")

    def handle_health_changed(self) -> None:
        self.link_health.show_links(self.controller.links, self.controller.tracker)
        self.mission_bar.show_recording(self.controller.recording)

    def handle_mission_changed(self) -> None:
        self.mission_bar.show_mission_state(self.controller.mission_state)
        self.mission_bar.show_scan_progress(
            self.controller.scan_percent,
            self.controller.scan_legs_done,
            self.controller.scan_legs_total,
        )
        self.refresh_map()

    def handle_command_acknowledged(self, command: str, vehicle_id: str) -> None:
        self.log_panel.append(f"{command} acknowledged by {vehicle_id}.")
        self.refresh_command_acks()

    def decode_detection(self, image_bytes, payload) -> None:
        """Runs on the MQTT network thread: decode here, paint on the Qt thread."""
        image = QImage.fromData(image_bytes)
        if image.isNull():
            logger.warning("A detection image could not be decoded and was dropped.")
            return
        self.detection_received.emit(image, payload)

    # Periodic refresh

    def refresh_live_values(self) -> None:
        """Ages, the elapsed clock and the ack timer keep moving without new data."""
        elapsed_seconds = time.monotonic() - self.mission_start_monotonic
        self.mission_bar.show_elapsed(elapsed_seconds)
        self.vehicle_list.refresh_staleness()
        self.refresh_command_acks()
        self.refresh_broker_status()

    def refresh_command_acks(self) -> None:
        missing = self.controller.unacknowledged_vehicles()
        self.mission_bar.show_command_acks(
            self.controller.pending_command,
            len(self.controller.acknowledged_vehicles),
            len(self.controller.vehicles),
            missing,
            self.controller.command_ack_timed_out(),
        )

    def refresh_map(self) -> None:
        self.map_view.show_mission(
            self.vehicles,
            list(self.controller.targets.values()),
            self.controller.scan_polygon,
            self.controller.scan_legs,
        )

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
        # nobody reads the ages while the window is minimised
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self.refresh_timer.stop()
            elif not self.refresh_timer.isActive():
                self.refresh_timer.start()


def build_vehicles(selection) -> list:
    """The Pasifik first, then one agent per drone the operator selected.

    The mission flies one Pasifik — its topics carry no vehicle id — so a
    larger VTOL count on the selection screen changes nothing here.
    """
    if selection.vtol_count > 1:
        logger.warning(
            f"{selection.vtol_count} VTOLs were selected, but this mission has one "
            f"Pasifik and one set of Pasifik topics. The extra ones are ignored."
        )

    vehicles = [VehicleState(PASIFIK_VEHICLE_ID, PASIFIK_TITLE, is_pasifik=True)]
    for agent_number in range(1, selection.drone_count + 1):
        agent_id = str(agent_number)
        vehicles.append(
            VehicleState(
                agent_id, AGENT_TITLE_FORMAT.format(agent_id=agent_id), is_pasifik=False
            )
        )
    return vehicles
