"""Everything the TEST tab sends, and the id each press is answered by.

Split out of ``test_bus.py`` for size, and it is a mixin rather than a separate
object so the bus keeps every method under its own name.

None of these presses reach anything the mission does not also use. A camera
press starts the recorder the mission's own press starts; a detector press
retunes the detector the aircraft searches with; a mapping press starts the
capture the survey starts; a route press runs the planner a found target would
have run. That is the point of the tab — a thing proved here is proved for the
mission, because it is the same code — so nothing here may quietly grow into a
second way of asking for the same work.

Every press carries an id of the controller's making, and the aircraft sends it
back on the acknowledgement. That is how an answer to a press the operator has
moved past is told from an answer to the one they are watching.
"""

import logging

from competitions.suas.config import (
    CAMERA_TEST_ACTIONS,
    KEY_CAMERA_ACTION,
    KEY_CAMERA_COMMAND_ID,
    KEY_CAMERA_FILE_NAMES,
    KEY_CAMERA_RATE,
    KEY_DETECTOR_ACTION,
    KEY_DETECTOR_COMMAND_BACKEND,
    KEY_DETECTOR_COMMAND_CONFIDENCE,
    KEY_DETECTOR_COMMAND_ID,
    KEY_GIMBAL_ACTION,
    KEY_GIMBAL_COMMAND_ID,
    KEY_GIMBAL_COMMAND_PITCH,
    KEY_GIMBAL_COMMAND_YAW,
    KEY_GIMBAL_COMMAND_ZOOM,
    KEY_MAPPING_ACTION,
    KEY_MAPPING_COMMAND_ID,
    KEY_ROUTE_COMMAND_ACTION,
    KEY_ROUTE_COMMAND_ALTITUDE,
    KEY_ROUTE_COMMAND_ID,
    KEY_ROUTE_COMMAND_LATITUDE,
    KEY_ROUTE_COMMAND_LONGITUDE,
    KEY_ROUTE_COMMAND_RADIUS,
    KEY_ROUTE_COMMAND_ROUTE_ID,
    KEY_ROUTE_COMMAND_STATION,
    KEY_WATCH_ACTION,
    KEY_WATCH_COMMAND_ID,
    KEY_WATCH_COMMAND_INDEX,
    TOPIC_CAMERA_COMMAND,
    TOPIC_DETECTOR_COMMAND,
    TOPIC_GIMBAL_COMMAND,
    TOPIC_MAPPING_REQUEST,
    TOPIC_ROUTE_COMMAND,
    TOPIC_WAYPOINT_WATCH_COMMAND,
)

logger = logging.getLogger(__name__)


class TestCommandsMixin:
    """The presses the TEST tab makes, on the bus the mission already speaks."""

    def send_camera_test_command(self, action: str, rate_hz: float | None = None,
                                 file_names: list | None = None) -> str:
        """One press of the camera page.

        The rate rides along with the photo timers and the file names with a
        fetch; both are left out of a press that has no use for them, because
        the contract makes them optional and a field sent empty reads on the
        aircraft as a real answer rather than a missing one.
        """
        command_id = self.next_command_id()
        self.pending_camera_command_id = command_id
        payload = {
            KEY_CAMERA_COMMAND_ID: command_id,
            KEY_CAMERA_ACTION: action,
        }
        if rate_hz is not None:
            payload[KEY_CAMERA_RATE] = rate_hz
        if file_names is not None:
            payload[KEY_CAMERA_FILE_NAMES] = file_names

        self.mqtt_client.publish_json(TOPIC_CAMERA_COMMAND, payload)
        logger.info(f"Camera test command '{action}' sent as {command_id}.")
        return command_id

    def send_gimbal_command(self, action: str, yaw_degrees: float | None = None,
                            pitch_degrees: float | None = None,
                            zoom: float | None = None) -> str:
        """Point the camera, or stop it where it is."""
        command_id = self.next_command_id()
        self.pending_gimbal_command_id = command_id
        payload = {
            KEY_GIMBAL_COMMAND_ID: command_id,
            KEY_GIMBAL_ACTION: action,
        }
        if yaw_degrees is not None:
            payload[KEY_GIMBAL_COMMAND_YAW] = yaw_degrees
        if pitch_degrees is not None:
            payload[KEY_GIMBAL_COMMAND_PITCH] = pitch_degrees
        if zoom is not None:
            payload[KEY_GIMBAL_COMMAND_ZOOM] = zoom

        self.mqtt_client.publish_json(TOPIC_GIMBAL_COMMAND, payload)
        logger.info(f"Gimbal command '{action}' sent as {command_id}.")
        return command_id

    def send_waypoint_watch(self, action: str,
                            waypoint_index: int | None = None) -> str:
        """Arm the scan on a mission item, or take both settings off.

        This does not add a second way of starting the survey: it changes the
        item number the aircraft's own lap watch is already comparing against,
        so the scan still starts where it always did — somewhere else.
        """
        command_id = self.next_command_id()
        self.pending_watch_command_id = command_id
        payload = {
            KEY_WATCH_COMMAND_ID: command_id,
            KEY_WATCH_ACTION: action,
        }
        if waypoint_index is not None:
            payload[KEY_WATCH_COMMAND_INDEX] = waypoint_index

        self.mqtt_client.publish_json(TOPIC_WAYPOINT_WATCH_COMMAND, payload)
        logger.info(f"Waypoint watch '{action}' sent as {command_id}.")
        return command_id

    def send_mapping_command(self, action: str) -> str:
        """Start or stop the mapping capture the survey would have started."""
        command_id = self.next_command_id()
        self.pending_mapping_command_id = command_id
        self.mqtt_client.publish_json(TOPIC_MAPPING_REQUEST, {
            KEY_MAPPING_COMMAND_ID: command_id,
            KEY_MAPPING_ACTION: action,
        })
        logger.info(f"Mapping capture '{action}' sent as {command_id}.")
        return command_id

    def send_detector_command(self, action: str, backend: str = "",
                              minimum_confidence: float | None = None) -> str:
        """Run, stop or retune the detector the aircraft flies with.

        There is no bench detector. This changes the settings the mission's own
        pipeline reads, so a threshold proved here is the threshold the
        aircraft searches with.
        """
        command_id = self.next_command_id()
        self.pending_detector_command_id = command_id
        payload = {
            KEY_DETECTOR_COMMAND_ID: command_id,
            KEY_DETECTOR_ACTION: action,
        }
        if backend:
            payload[KEY_DETECTOR_COMMAND_BACKEND] = backend
        if minimum_confidence is not None:
            payload[KEY_DETECTOR_COMMAND_CONFIDENCE] = minimum_confidence

        self.mqtt_client.publish_json(TOPIC_DETECTOR_COMMAND, payload)
        logger.info(f"Detector command '{action}' sent as {command_id}.")
        return command_id

    def send_route_command(self, action: str, route_id: str = "",
                           latitude: float | None = None,
                           longitude: float | None = None,
                           altitude_metres: float | None = None,
                           radius_metres: float | None = None,
                           station: str = "") -> str:
        """Plan a route to a place the operator named, or answer the one on offer.

        The route id goes out with an answer so a press cannot fly a route the
        operator has already moved past — the aircraft refuses an id that is not
        the one it is offering.
        """
        command_id = self.next_command_id()
        self.pending_route_command_id = command_id
        payload = {
            KEY_ROUTE_COMMAND_ID: command_id,
            KEY_ROUTE_COMMAND_ACTION: action,
        }
        if route_id:
            payload[KEY_ROUTE_COMMAND_ROUTE_ID] = route_id
        if latitude is not None:
            payload[KEY_ROUTE_COMMAND_LATITUDE] = latitude
        if longitude is not None:
            payload[KEY_ROUTE_COMMAND_LONGITUDE] = longitude
        if altitude_metres is not None:
            payload[KEY_ROUTE_COMMAND_ALTITUDE] = altitude_metres
        if radius_metres is not None:
            payload[KEY_ROUTE_COMMAND_RADIUS] = radius_metres
        if station:
            payload[KEY_ROUTE_COMMAND_STATION] = station

        self.mqtt_client.publish_json(TOPIC_ROUTE_COMMAND, payload)
        logger.info(f"Route command '{action}' sent as {command_id}.")
        return command_id

    def camera_action(self, name: str) -> str:
        """One of the camera page's actions, by the name the config gives it."""
        return CAMERA_TEST_ACTIONS[name]
