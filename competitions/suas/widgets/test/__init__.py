"""The TEST tab's pages. One page per subject, one widget per file.

These are not a bench copy of the mission screen. Every press on them reaches
the code the scored mission runs, so a thing proved here is proved for the
flight -- see ``windows/test_tab.py`` for what each one is wired to.
"""

from competitions.suas.widgets.test.camera_test_panel import CameraTestPanel
from competitions.suas.widgets.test.card_column import CardColumn
from competitions.suas.widgets.test.detection_test_panel import DetectionTestPanel
from competitions.suas.widgets.test.gimbal_bar import GimbalBar
from competitions.suas.widgets.test.mapping_test_panel import MappingTestPanel
from competitions.suas.widgets.test.place_drop_row import PlaceDropRow
from competitions.suas.widgets.test.servo_test_panel import ServoTestPanel
from competitions.suas.widgets.test.sighting_column import SightingColumn
from competitions.suas.widgets.test.stream_column import StreamColumn
from competitions.suas.widgets.test.transfer_bar import TransferBar
from competitions.suas.widgets.test.truth_point_table import TruthPointTable
from competitions.suas.widgets.test.waypoint_monitor_panel import WaypointMonitorPanel

__all__ = [
    "CameraTestPanel",
    "CardColumn",
    "DetectionTestPanel",
    "GimbalBar",
    "MappingTestPanel",
    "PlaceDropRow",
    "ServoTestPanel",
    "SightingColumn",
    "StreamColumn",
    "TransferBar",
    "TruthPointTable",
    "WaypointMonitorPanel",
]
