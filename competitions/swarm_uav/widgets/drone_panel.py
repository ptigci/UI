"""Per-vehicle tab, loaded from designer/drone_panel.ui.

Edit the layout and styling in Qt Designer; this class only applies the
config ranges, wires the buttons to signals and updates the data labels.
The first VTOL tab additionally embeds the object-detection browser in its
bottom-right corner (with_detection=True).
"""

from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QMessageBox, QWidget

from config import CAMERA_ADD_TEXT, CAMERA_REMOVE_TEXT, POSITION_DECIMALS
from competitions.swarm_uav.widgets.clock_status import ClockStatusLabel
from widgets.detection_review import DetectionReviewPanel
from competitions.swarm_uav.config import (
    LATENCY_PROPS_QUESTION,
    LATENCY_PROPS_TITLE,
    MIN_TAKEOFF_ALTITUDE,
    MOVE_AXIS_MAX,
    MOVE_AXIS_MIN,
    SPINBOX_DECIMALS,
    STATE_UNKNOWN_TEXT,
    TAKEOFF_ALTITUDE_MAX,
)
from theme import set_role
from theme.tokens import ROLE_READOUT

FORM_PATH = Path(__file__).resolve().parent.parent / "designer" / "drone_panel.ui"


class DronePanel(QWidget):
    """One tab of the main window, used for both drones and VTOLs."""

    arm_requested = pyqtSignal()
    force_arm_requested = pyqtSignal()
    disarm_requested = pyqtSignal()
    force_disarm_requested = pyqtSignal()
    takeoff_requested = pyqtSignal(float)
    move_requested = pyqtSignal(float, float, float)
    land_requested = pyqtSignal()
    free_requested = pyqtSignal()
    tau_calibration_requested = pyqtSignal()
    # Carries the operator's answer about the propellers, so the drone decides
    # on a human's word rather than on anything the software guessed.
    latency_calibration_requested = pyqtSignal(bool)
    emergency_requested = pyqtSignal()
    camera_toggle_requested = pyqtSignal(bool)

    def __init__(self, vehicle_name: str, with_detection: bool = False, parent=None) -> None:
        super().__init__(parent)
        uic.loadUi(FORM_PATH, self)
        self.vehicle_name = vehicle_name

        self.namelbl.setText(vehicle_name.upper())
        self.camlbl.setText(f"{vehicle_name.upper()} CAM")
        self.connlbl.set_prefix("last message: ")
        self.connlbl.set_age(None)

        # Mission state from drone/{id}/state, next to the vehicle name.
        self.statelbl = QLabel(self)
        set_role(self.statelbl, ROLE_READOUT)
        self.set_state(STATE_UNKNOWN_TEXT)
        self.headerlayout.insertWidget(1, self.statelbl)

        # PPS clock sync from drone/{id}/clock, next to the mission state.
        self.clocklbl = ClockStatusLabel(self)
        self.headerlayout.insertWidget(2, self.clocklbl)

        # main_window talks to the camera through this attribute
        self.camera_view = self.cam
        self.camera_enabled = True

        self.detection_panel = None
        if with_detection:
            self.detection_panel = DetectionReviewPanel(self)
            self.generallayout.addWidget(self.detection_panel)

        self.configure_inputs()
        self.connect_buttons()

        zero_text = f"{0.0:.{POSITION_DECIMALS}f}"
        for value_label in (self.xlbl, self.ylbl, self.zlbl, self.vlbl):
            value_label.setText(zero_text)

    def configure_inputs(self) -> None:
        self.altSpinBox.setRange(MIN_TAKEOFF_ALTITUDE, TAKEOFF_ALTITUDE_MAX)
        self.altSpinBox.setDecimals(SPINBOX_DECIMALS)
        for move_input in (self.xSpinBox, self.ySpinBox, self.zSpinBox):
            move_input.setRange(MOVE_AXIS_MIN, MOVE_AXIS_MAX)
            move_input.setDecimals(SPINBOX_DECIMALS)

    def connect_buttons(self) -> None:
        self.armbtn.clicked.connect(self.arm_requested)
        self.farmbtn.clicked.connect(self.force_arm_requested)
        self.disarmbtn.clicked.connect(self.disarm_requested)
        self.fdisarmbtn.clicked.connect(self.force_disarm_requested)
        self.landbtn.clicked.connect(self.land_requested)
        self.freebtn.clicked.connect(self.free_requested)
        self.taubtn.clicked.connect(self.tau_calibration_requested)
        self.latencybtn.clicked.connect(self.request_latency_calibration)
        self.emergencybtn.clicked.connect(self.emergency_requested)
        self.takeoffbtn.clicked.connect(self.request_takeoff)
        self.movebtn.clicked.connect(self.request_move)
        self.camtogglebtn.clicked.connect(
            lambda: self.camera_toggle_requested.emit(not self.camera_enabled)
        )

    def request_takeoff(self) -> None:
        altitude = self.altSpinBox.value()
        if altitude <= MIN_TAKEOFF_ALTITUDE:
            QMessageBox.warning(
                self,
                "Invalid altitude",
                f"Takeoff altitude must be greater than {MIN_TAKEOFF_ALTITUDE:g} m.",
            )
            return
        self.takeoff_requested.emit(altitude)

    def request_latency_calibration(self) -> None:
        answer = QMessageBox.question(
            self,
            LATENCY_PROPS_TITLE,
            LATENCY_PROPS_QUESTION,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        self.latency_calibration_requested.emit(
            answer == QMessageBox.StandardButton.Yes
        )

    def request_move(self) -> None:
        self.move_requested.emit(
            self.xSpinBox.value(), self.ySpinBox.value(), self.zSpinBox.value()
        )

    def update_position(self, x: float, y: float, z: float, velocity: float) -> None:
        self.xlbl.setText(f"{x:.{POSITION_DECIMALS}f}")
        self.ylbl.setText(f"{y:.{POSITION_DECIMALS}f}")
        self.zlbl.setText(f"{z:.{POSITION_DECIMALS}f}")
        self.vlbl.setText(f"{velocity:.{POSITION_DECIMALS}f}")

    def set_connection_age(self, age_milliseconds: int | None) -> None:
        self.connlbl.set_age(age_milliseconds)

    def set_state(self, state_text: str) -> None:
        self.statelbl.setText(f"state: {state_text}")

    def set_clock_status(self, disciplined: bool, error_ms: float | None) -> None:
        self.clocklbl.show_status(disciplined, error_ms)

    def set_camera_enabled(self, enabled: bool) -> None:
        self.camera_enabled = enabled
        if enabled:
            toggle_text = CAMERA_REMOVE_TEXT
            camera_row_stretch = 1
        else:
            toggle_text = CAMERA_ADD_TEXT
            camera_row_stretch = 0
        self.camtogglebtn.setText(toggle_text)
        self.camera_view.setVisible(enabled)
        # the camera row stops claiming space while the output is closed
        self.armlayout.setRowStretch(1, camera_row_stretch)
        if enabled:
            self.camera_view.set_unavailable()
