"""The state the SUAS widgets read: the aircraft, the laps, the delivery, the links."""

from competitions.suas.models.camera_state import CameraState
from competitions.suas.models.detector_state import DetectorState, Sighting
from competitions.suas.models.gimbal_state import GimbalState
from competitions.suas.models.lap_state import LapState, endurance_points_for
from competitions.suas.models.link_state import LinkPair, LinkState
from competitions.suas.models.mapping_capture_state import MappingCaptureState
from competitions.suas.models.media_state import MediaFile, MediaLibraryState
from competitions.suas.models.payload_state import PayloadState
from competitions.suas.models.release_state import ReleaseState
from competitions.suas.models.route_plan import RoutePlan
from competitions.suas.models.servo_state import ServoState, ServoStation
from competitions.suas.models.stitch_state import StitchState
from competitions.suas.models.target_map_state import TargetMapState
from competitions.suas.models.truth_points import TruthPoint, TruthPointStore
from competitions.suas.models.vehicle_state import VehicleState
from competitions.suas.models.waypoint_watch_state import WaypointWatchState

__all__ = [
    "CameraState",
    "DetectorState",
    "GimbalState",
    "LapState",
    "LinkPair",
    "LinkState",
    "MappingCaptureState",
    "MediaFile",
    "MediaLibraryState",
    "PayloadState",
    "ReleaseState",
    "RoutePlan",
    "ServoState",
    "ServoStation",
    "Sighting",
    "StitchState",
    "TargetMapState",
    "TruthPoint",
    "TruthPointStore",
    "VehicleState",
    "WaypointWatchState",
    "endurance_points_for",
]
