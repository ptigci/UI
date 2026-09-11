"""The SUAS panels. One widget per file, and the map is a package of its own."""

from competitions.suas.widgets.calibration_panel import CalibrationPanel
from competitions.suas.widgets.camera_panel import CameraPanel
from competitions.suas.widgets.detection_column import DetectionColumn
from competitions.suas.widgets.drop_test_panel import DropTestPanel
from competitions.suas.widgets.flight_panel import FlightPanel
from competitions.suas.widgets.lap_tracker import LapTracker
from competitions.suas.widgets.log_panel import LogPanel
from competitions.suas.widgets.map import MapView
from competitions.suas.widgets.mapping_panel import MappingPanel
from competitions.suas.widgets.mission_clock import MissionClock
from competitions.suas.widgets.mission_panel import MissionPanel
from competitions.suas.widgets.payload_panel import PayloadPanel
from competitions.suas.widgets.safety_panel import SafetyPanel
from competitions.suas.widgets.telemetry_ribbon import TelemetryRibbon

__all__ = [
    "CalibrationPanel",
    "CameraPanel",
    "DetectionColumn",
    "DropTestPanel",
    "FlightPanel",
    "LapTracker",
    "LogPanel",
    "MapView",
    "MappingPanel",
    "MissionClock",
    "MissionPanel",
    "PayloadPanel",
    "SafetyPanel",
    "TelemetryRibbon",
]
