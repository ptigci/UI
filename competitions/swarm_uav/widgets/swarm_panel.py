"""Swarm tab, loaded from designer/swarm_panel.ui.

The command and formation controls are fixed in the .ui file; the camera grid
on the right is built dynamically from the selected drone count, and the
readings beside the terminal come from TelemetryMonitor.
"""

import math
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from config import (
    CAMERA_ADD_TEXT,
    CAMERA_REMOVE_TEXT,
    DRONE_COUNT_MAX,
    DRONE_COUNT_MIN,
)
from competitions.swarm_uav.config import (
    FORMATION_ANGLE_MAX,
    FORMATION_ANGLE_MIN,
    FORMATION_CODE_INVERSE_V,
    FORMATION_CODE_LINE,
    FORMATION_CODE_V,
    FORMATION_DISTANCE_MAX,
    MIN_FORMATION_ANGLE,
    MIN_FORMATION_DISTANCE,
    MIN_TAKEOFF_ALTITUDE,
    MISSION2_ALL_IN_TEXT,
    MISSION2_START_TEXT,
    MISSION2_STILL_IN_TEXT,
    MISSION2_STOP_TEXT,
    MISSION2_WAITING_TEXT,
    MISSION_ACTIVE_STATES,
    MISSION_TARGET_AUTO_TEXT,
    MOVE_AXIS_MAX,
    MOVE_AXIS_MIN,
    QR_PANEL_TITLE,
    ROTATION_MAX,
    ROTATION_MIN,
    SPINBOX_DECIMALS,
    SWARM_CAMERA_HEADER_HEIGHT,
    SWARM_CAMERA_MIN_HEIGHT,
    SWARM_CAMERA_ROWS,
    SWARM_GRID_COLUMNS,
    TAKEOFF_ALTITUDE_MAX,
)
from theme import flush_layout, set_role, set_scale, set_variant
from theme.tokens import (
    ROLE_HEADING,
    SCALE_ICON,
    SPACE_SM,
    VARIANT_GHOST,
)
from widgets.camera_view import CameraView
from competitions.swarm_uav.widgets.qr_panel import QRContentPanel
from competitions.swarm_uav.widgets.telemetry_monitor import TelemetryMonitor

FORM_PATH = Path(__file__).resolve().parent.parent / "designer" / "swarm_panel.ui"

# cameras that do not fit one page go behind the < > buttons
CAMERAS_PER_PAGE = SWARM_GRID_COLUMNS * SWARM_CAMERA_ROWS

# grid slot of the QR content panel; drone ids start at 1 so 0 is free
QR_PANEL_ID = 0


class SwarmPanel(QWidget):
    """Commands here target every drone at once; missions and formations too."""

    arm_requested = pyqtSignal()
    force_arm_requested = pyqtSignal()
    disarm_requested = pyqtSignal()
    force_disarm_requested = pyqtSignal()
    takeoff_requested = pyqtSignal(float)
    move_requested = pyqtSignal(float, float, float)
    land_requested = pyqtSignal()
    free_requested = pyqtSignal()
    emergency_requested = pyqtSignal()
    formation_requested = pyqtSignal(str, float, float, float, float, float)
    mission1_requested = pyqtSignal(int)
    mission2_requested = pyqtSignal(bool)  # True starts the RC session, False ends it
    plan_upload_requested = pyqtSignal()
    plan_execute_requested = pyqtSignal()
    refresh_requested = pyqtSignal(int, bool)  # drone count, simulation enabled
    camera_toggle_requested = pyqtSignal(int, bool)

    def __init__(self, drones: list[tuple[int, str]], initial_drone_count: int, parent=None) -> None:
        """drones is a list of (vehicle_id, display_name) tuples."""
        super().__init__(parent)
        uic.loadUi(FORM_PATH, self)

        # the QR content panel shares the grid, so views are QWidgets here
        self.camera_views: dict[int, QWidget] = {}
        self.camera_headers: dict[int, QWidget] = {}
        self.camera_toggles: dict[int, QPushButton] = {}
        self.camera_enabled: dict[int, bool] = {}

        # Latest state per drone, so the command buttons can follow the swarm.
        self.drone_states: dict[int, str] = {}

        self.configure_inputs(drones, initial_drone_count)
        self.connect_buttons()
        # Everything the ground station can send mid-flight. EMERGENCY and the
        # camera controls are deliberately not here.
        self.gated_buttons = [
            self.swarmarmbtn, self.swarmfarmbtn, self.swarmdisarmbtn,
            self.swarmfdisarmbtn, self.swarmlandbtn, self.swarmtakeoffbtn,
            self.swarmmovebtn, self.swarmfreebtn,
            self.linebtn, self.vbtn, self.inversevbtn,
        ]
        self.build_camera_grid(drones)
        self.telemetry_monitor = TelemetryMonitor(drones, self)
        self.telemetrylayout.addWidget(self.telemetry_monitor, 0, 0)

        # let the buttons grow into free space and compress on small windows
        # instead of clipping into each other
        for command_button in self.findChildren(QPushButton):
            button_policy = command_button.sizePolicy()
            button_policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
            command_button.setSizePolicy(button_policy)

    # Input configuration

    def configure_inputs(self, drones: list[tuple[int, str]], initial_drone_count: int) -> None:
        self.swarmalt.setRange(MIN_TAKEOFF_ALTITUDE, TAKEOFF_ALTITUDE_MAX)
        for move_input in (self.swarmx, self.swarmy, self.swarmz):
            move_input.setRange(MOVE_AXIS_MIN, MOVE_AXIS_MAX)
        for rotation_input in (self.yawbtn, self.pitchbtn, self.rollbtn):
            rotation_input.setRange(ROTATION_MIN, ROTATION_MAX)
        self.fdbtn.setRange(MIN_FORMATION_DISTANCE, FORMATION_DISTANCE_MAX)
        self.fanglebtn.setRange(FORMATION_ANGLE_MIN, FORMATION_ANGLE_MAX)

        for double_input in (self.swarmalt, self.swarmx, self.swarmy, self.swarmz,
                             self.yawbtn, self.pitchbtn, self.rollbtn,
                             self.fdbtn, self.fanglebtn):
            double_input.setDecimals(SPINBOX_DECIMALS)

        # 0 means AUTO: the leaving drone comes from the QR payload, which
        # is the competition setting; an explicit id is only for testing.
        drone_ids = [drone_id for drone_id, drone_name in drones]
        self.missionidSpinBox.setRange(0, max(drone_ids))
        self.missionidSpinBox.setSpecialValueText(MISSION_TARGET_AUTO_TEXT)
        self.missionidSpinBox.setValue(0)

        self.dronecountSpinBox.setRange(DRONE_COUNT_MIN, DRONE_COUNT_MAX)
        self.dronecountSpinBox.setValue(initial_drone_count)

    def connect_buttons(self) -> None:
        self.swarmarmbtn.clicked.connect(self.arm_requested)
        self.swarmfarmbtn.clicked.connect(self.force_arm_requested)
        self.swarmdisarmbtn.clicked.connect(self.disarm_requested)
        self.swarmfdisarmbtn.clicked.connect(self.force_disarm_requested)
        self.swarmlandbtn.clicked.connect(self.land_requested)
        self.swarmfreebtn.clicked.connect(self.free_requested)
        self.swarmemergencybtn.clicked.connect(self.emergency_requested)
        self.swarmtakeoffbtn.clicked.connect(self.request_takeoff)
        self.swarmmovebtn.clicked.connect(self.request_move)

        self.linebtn.clicked.connect(lambda: self.request_formation(FORMATION_CODE_LINE))
        self.vbtn.clicked.connect(lambda: self.request_formation(FORMATION_CODE_V))
        self.inversevbtn.clicked.connect(lambda: self.request_formation(FORMATION_CODE_INVERSE_V))

        self.mission1btn.clicked.connect(
            lambda: self.mission1_requested.emit(self.missionidSpinBox.value())
        )
        self.mission2btn.toggled.connect(self.request_mission2)
        self.uploadmissionbtn.clicked.connect(self.plan_upload_requested)
        self.executemissionbtn.clicked.connect(self.plan_execute_requested)
        self.refreshbtn.clicked.connect(
            lambda: self.refresh_requested.emit(
                self.dronecountSpinBox.value(), self.simulationCheckBox.isChecked()
            )
        )

    def set_plan_uploaded(self, uploaded: bool) -> None:
        """EXECUTE MISSION only works once a plan has been uploaded."""
        self.executemissionbtn.setEnabled(uploaded)

    # Command validation

    def request_takeoff(self) -> None:
        altitude = self.swarmalt.value()
        if altitude <= MIN_TAKEOFF_ALTITUDE:
            QMessageBox.warning(
                self,
                "Invalid altitude",
                f"Takeoff altitude must be greater than {MIN_TAKEOFF_ALTITUDE:g} m.",
            )
            return
        self.takeoff_requested.emit(altitude)

    def request_mission2(self, active: bool) -> None:
        """MISSION 2 stays pressed while the RC session runs; again ends it."""
        if active:
            self.mission2btn.setText(MISSION2_STOP_TEXT)
        else:
            self.mission2btn.setText(MISSION2_START_TEXT)
        self.mission2_requested.emit(active)

    def show_mission2_status(self, active: bool, waiting: list[int]) -> None:
        """Say on the button which drones still lack the command.

        The ground station keeps sending it to them and reports here every
        time the list changes, so the button reads "all in" once every drone
        has answered.
        """
        drones = ", ".join(str(drone_id) for drone_id in waiting)
        if active and waiting:
            text = f"{MISSION2_STOP_TEXT} ({MISSION2_WAITING_TEXT.format(drones=drones)})"
        elif active:
            text = f"{MISSION2_STOP_TEXT} ({MISSION2_ALL_IN_TEXT})"
        elif waiting:
            text = f"{MISSION2_START_TEXT} ({MISSION2_STILL_IN_TEXT.format(drones=drones)})"
        else:
            text = MISSION2_START_TEXT
        self.mission2btn.setText(text)

    def request_move(self) -> None:
        self.move_requested.emit(self.swarmx.value(), self.swarmy.value(), self.swarmz.value())

    def request_formation(self, formation_code: str) -> None:
        distance = self.fdbtn.value()
        if distance <= MIN_FORMATION_DISTANCE:
            QMessageBox.warning(
                self,
                "Invalid formation",
                f"Distance must be greater than {MIN_FORMATION_DISTANCE:g} m.",
            )
            return

        angle = self.fanglebtn.value()
        needs_angle = formation_code in (FORMATION_CODE_V, FORMATION_CODE_INVERSE_V)
        if needs_angle and angle < MIN_FORMATION_ANGLE:
            QMessageBox.warning(
                self,
                "Invalid formation",
                f"Angle must be at least {MIN_FORMATION_ANGLE:g}° for V formations.",
            )
            return

        self.formation_requested.emit(
            formation_code,
            distance,
            angle,
            self.yawbtn.value(),
            self.pitchbtn.value(),
            self.rollbtn.value(),
        )

    # Dynamic monitor grids

    def build_camera_grid(self, drones: list[tuple[int, str]]) -> None:
        """Create one camera view per drone plus the QR content slot; only
        one page is on the grid at a time."""
        self.camera_entries: list[tuple[int, QWidget, QWidget]] = []
        for drone_id, drone_name in drones:
            camera_header = self.build_camera_header(drone_id, f"CAM {drone_id}")
            camera_header.hide()

            camera_view = CameraView(self)
            camera_view.setMinimumHeight(SWARM_CAMERA_MIN_HEIGHT)
            camera_view.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            camera_view.hide()

            self.camera_entries.append((drone_id, camera_header, camera_view))
            self.camera_views[drone_id] = camera_view

        # the decoded QR payload takes the slot after the last camera, so
        # it lives with the video outputs (and pages/toggles like them)
        qr_header = self.build_camera_header(QR_PANEL_ID, QR_PANEL_TITLE)
        qr_header.hide()
        self.qr_panel = QRContentPanel(self)
        self.qr_panel.setMinimumHeight(SWARM_CAMERA_MIN_HEIGHT)
        self.qr_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.qr_panel.hide()
        self.camera_entries.append((QR_PANEL_ID, qr_header, self.qr_panel))
        self.camera_views[QR_PANEL_ID] = self.qr_panel

        # cameras share the horizontal space; the vertical split is set per
        # page in _show_camera_page, based on how many cameras are open
        for grid_column in range(SWARM_GRID_COLUMNS):
            self.camlayout.setColumnStretch(grid_column, 1)

        # closed cameras keep their name and + button in a row under the grid
        self.closed_cameras_layout = QHBoxLayout()
        self.closed_cameras_layout.addStretch()
        self.dronmonitorlayout.insertLayout(2, self.closed_cameras_layout)

        self.camprevbtn.clicked.connect(lambda: self.show_camera_page(self.camera_page - 1))
        self.camnextbtn.clicked.connect(lambda: self.show_camera_page(self.camera_page + 1))

        self.camera_page = 0
        self.show_camera_page(0)

    def build_camera_header(self, drone_id: int, title: str) -> QWidget:
        """Output name plus its remove/add button, kept as one grid cell."""
        camera_header = QWidget(self)
        camera_header.setMaximumHeight(SWARM_CAMERA_HEADER_HEIGHT)

        header_layout = QHBoxLayout(camera_header)
        flush_layout(header_layout, SPACE_SM)
        title_label = QLabel(title, camera_header)
        set_role(title_label, ROLE_HEADING)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        camera_toggle = QPushButton(CAMERA_REMOVE_TEXT, camera_header)
        # one glyph wide, so it asks the design system for the icon size
        set_variant(camera_toggle, VARIANT_GHOST)
        set_scale(camera_toggle, SCALE_ICON)
        camera_toggle.setToolTip("Remove this output from the UI, or add it back.")
        camera_toggle.clicked.connect(
            lambda checked, did=drone_id: self.camera_toggle_requested.emit(
                did, not self.camera_enabled[did]
            )
        )
        header_layout.addWidget(camera_toggle)

        self.camera_headers[drone_id] = camera_header
        self.camera_toggles[drone_id] = camera_toggle
        self.camera_enabled[drone_id] = True
        return camera_header

    def open_camera_entries(self) -> list:
        return [entry for entry in self.camera_entries if self.camera_enabled[entry[0]]]

    def camera_page_count(self) -> int:
        return max(1, math.ceil(len(self.open_camera_entries()) / CAMERAS_PER_PAGE))

    def show_camera_page(self, page_index: int) -> None:
        open_entries = self.open_camera_entries()
        page_count = self.camera_page_count()
        page_index = max(0, min(page_index, page_count - 1))
        self.camera_page = page_index

        # take every open camera off the grid, then place only the requested
        # page, so views can never pile up on top of each other
        for drone_id, camera_header, camera_view in open_entries:
            self.camlayout.removeWidget(camera_header)
            self.camlayout.removeWidget(camera_view)
            camera_header.hide()
            camera_view.hide()

        page_start = page_index * CAMERAS_PER_PAGE
        page_entries = open_entries[page_start:page_start + CAMERAS_PER_PAGE]
        for slot_index, (drone_id, camera_header, camera_view) in enumerate(page_entries):
            grid_row = (slot_index // SWARM_GRID_COLUMNS) * 2
            grid_column = slot_index % SWARM_GRID_COLUMNS
            # the last camera stretches across the leftover columns of its row
            is_last_camera = slot_index == len(page_entries) - 1
            if is_last_camera:
                column_span = SWARM_GRID_COLUMNS - grid_column
            else:
                column_span = 1
            self.camlayout.addWidget(camera_header, grid_row, grid_column, 1, column_span)
            self.camlayout.addWidget(camera_view, grid_row + 1, grid_column, 1, column_span)
            camera_header.show()
            camera_view.show()

        # only the view rows in use share the vertical space, so the open
        # cameras grow to fill the whole section when others are closed
        used_view_rows = math.ceil(len(page_entries) / SWARM_GRID_COLUMNS)
        for page_row in range(SWARM_CAMERA_ROWS):
            if page_row < used_view_rows:
                row_stretch = 1
            else:
                row_stretch = 0
            self.camlayout.setRowStretch(page_row * 2 + 1, row_stretch)

        pagination_needed = page_count > 1
        self.camprevbtn.setVisible(pagination_needed)
        self.camnextbtn.setVisible(pagination_needed)
        self.campagelabel.setVisible(pagination_needed)
        if page_entries:
            first_slot_name = self.slot_name(page_entries[0][0])
            last_slot_name = self.slot_name(page_entries[-1][0])
            self.campagelabel.setText(
                f"CAM {first_slot_name}-{last_slot_name} / {len(open_entries)}"
            )
        self.camprevbtn.setEnabled(page_index > 0)
        self.camnextbtn.setEnabled(page_index < page_count - 1)

    @staticmethod
    def slot_name(drone_id: int) -> str:
        if drone_id == QR_PANEL_ID:
            return "QR"
        return str(drone_id)

    # Data updates from the main window

    def update_position(self, drone_id: int, x: float, y: float, z: float, velocity: float) -> None:
        self.telemetry_monitor.update_position(drone_id, x, y, z, velocity)

    def set_connection_health(self, drone_id: int, health) -> None:
        self.telemetry_monitor.set_connection_health(drone_id, health)

    def set_state(self, drone_id: int, state_text: str) -> None:
        self.telemetry_monitor.set_state(drone_id, state_text)
        self.drone_states[drone_id] = state_text
        self.refresh_command_buttons()

    def refresh_command_buttons(self) -> None:
        """Grey the command buttons out while any drone is flying a mission.

        The drones refuse these commands themselves — the şartname allows the
        ground station no input during a mission — so this only saves the
        operator from pressing a button that will not do anything. EMERGENCY
        stays live: a kill is a safety action, not mission input.
        """
        mission_flying = self.mission_flying()
        for command_button in self.gated_buttons:
            command_button.setEnabled(not mission_flying)

    def mission_flying(self) -> bool:
        """Whether any drone reports a state that means a mission is running."""
        return any(
            state in MISSION_ACTIVE_STATES for state in self.drone_states.values()
        )

    def set_clock_status(self, drone_id: int, source: str, error_ms: float | None) -> None:
        self.telemetry_monitor.set_clock_status(drone_id, source, error_ms)

    def clear_display(self) -> None:
        """Wipe the terminal, the decoded QR and the drone readings."""
        self.swarmterminal.clear()
        self.qr_panel.clear_qr()
        self.telemetry_monitor.clear_readings()

    def show_camera_frame(self, drone_id: int, frame: QPixmap) -> None:
        camera_view = self.camera_views.get(drone_id)
        if camera_view is not None:
            camera_view.show_pixmap(frame)

    def set_camera_unavailable(self, drone_id: int) -> None:
        camera_view = self.camera_views.get(drone_id)
        if camera_view is not None:
            camera_view.set_unavailable()

    def set_camera_enabled(self, drone_id: int, enabled: bool) -> None:
        if self.camera_enabled.get(drone_id) in (None, enabled):
            return
        self.camera_enabled[drone_id] = enabled
        camera_header = self.camera_headers[drone_id]
        camera_view = self.camera_views[drone_id]
        if enabled:
            toggle_text = CAMERA_REMOVE_TEXT
        else:
            toggle_text = CAMERA_ADD_TEXT
        self.camera_toggles[drone_id].setText(toggle_text)

        if enabled:
            # the repack below returns the header to the camera grid
            self.closed_cameras_layout.removeWidget(camera_header)
            # the QR panel keeps its content; real cameras reset until
            # frames resume
            if drone_id != QR_PANEL_ID:
                camera_view.set_unavailable()
        else:
            self.camlayout.removeWidget(camera_header)
            self.camlayout.removeWidget(camera_view)
            camera_view.hide()
            # keep the camera name and its + button reachable under the grid
            self.closed_cameras_layout.insertWidget(
                self.closed_cameras_layout.count() - 1, camera_header
            )
            camera_header.show()

        self.show_camera_page(self.camera_page)
