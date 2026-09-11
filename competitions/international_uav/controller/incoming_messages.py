"""Everything that arrives from the ground station, and what it changes.

One router and one handler per topic. All of it runs on the MQTT network
thread, so a handler updates the state the widgets read and then calls the
window's callback — the window is what hops it onto the Qt thread.

A mixin on MissionController, so these keep using self.vehicles and self.targets.
"""

import base64
import binascii
import logging

from config import DETECTION_KEY_IMAGE
from competitions.international_uav.config import (
    KEY_CALIBRATION_DETAIL,
    KEY_CALIBRATION_NAME,
    KEY_CALIBRATION_PERCENT,
    KEY_CALIBRATION_STATE,
    KEY_CALIBRATION_STEP,
    KEY_COMMAND,
    KEY_COMMAND_RESULT_ACCEPTED,
    KEY_COMMAND_RESULT_COMMAND,
    KEY_COMMAND_RESULT_DETAIL,
    KEY_COMMAND_VEHICLE,
    KEY_HEALTH_LINKS,
    KEY_HEALTH_RECORDING,
    KEY_HEALTH_TRACKER,
    KEY_SCAN_CURRENT_SEQUENCE,
    KEY_SCAN_LEGS_DONE,
    KEY_SCAN_LEGS_TOTAL,
    KEY_SCAN_PERCENT,
    KEY_SCAN_WAYPOINTS,
    KEY_STATE,
    KEY_STATUSTEXT_SEVERITY,
    KEY_STATUSTEXT_TEXT,
    KEY_TARGET_ID,
    KEY_TILE_ID,
    KEY_TILE_LATITUDE,
    KEY_TILE_LONGITUDE,
    KEY_TILE_METRES_PER_PIXEL,
    KEY_TILE_PATH,
    KEY_TILE_REVISION,
    KEY_TILE_SESSION,
    KEY_TILE_SIZE_PIXELS,
    TOPIC_AGENT_STATUS_PATTERN,
    TOPIC_AGENT_TELEMETRY_PATTERN,
    TOPIC_CALIBRATION_PROGRESS,
    TOPIC_COMMAND_ACK,
    TOPIC_COMMAND_RESULT,
    TOPIC_DETECTION_FRAME,
    TOPIC_LINK_TEST_RESULT,
    TOPIC_MAP_TILE,
    TOPIC_PASIFIK_STATUS,
    TOPIC_PASIFIK_STATUSTEXT,
    TOPIC_PASIFIK_TELEMETRY,
    TOPIC_SCAN_PROGRESS,
    TOPIC_SYSTEM_HEALTH,
    TOPIC_TARGET_ASSIGNMENT,
    TOPIC_TARGET_CONFIRMED,
)
from competitions.international_uav.models import (
    link_from_payload,
    target_from_payload,
    tracker_from_payload,
    waypoint_from_payload,
)

logger = logging.getLogger(__name__)

# The scanning VTOL has topics of its own, so it needs no id on the wire.
PASIFIK_VEHICLE_ID = "pasifik"

# Agent topics look like "agent/{id}/{type}"; the type comes from the
# subscribe patterns so config/mqtt.toml stays the single source of truth.
AGENT_TELEMETRY_TYPE = TOPIC_AGENT_TELEMETRY_PATTERN.split("/")[-1]
AGENT_STATUS_TYPE = TOPIC_AGENT_STATUS_PATTERN.split("/")[-1]
AGENT_TOPIC_PARTS = 3


class IncomingMessagesMixin:
    """One handler per topic, and the router that picks between them."""

    def route_incoming_message(self, topic: str, payload: dict) -> None:
        if not isinstance(payload, dict):
            logger.warning(f"Ignoring a message on '{topic}' that is not a JSON object.")
            return

        if topic == TOPIC_PASIFIK_TELEMETRY:
            self.handle_telemetry(PASIFIK_VEHICLE_ID, payload)
            return
        if topic == TOPIC_PASIFIK_STATUS:
            self.handle_pasifik_status(payload)
            return
        if topic == TOPIC_SCAN_PROGRESS:
            self.handle_scan_progress(payload)
            return
        if topic == TOPIC_DETECTION_FRAME:
            self.handle_detection_frame(payload)
            return
        if topic == TOPIC_TARGET_CONFIRMED or topic == TOPIC_TARGET_ASSIGNMENT:
            self.handle_target(payload)
            return
        if topic == TOPIC_MAP_TILE:
            self.handle_map_tile(payload)
            return
        if topic == TOPIC_SYSTEM_HEALTH:
            self.handle_health(payload)
            return
        if topic == TOPIC_COMMAND_ACK:
            self.handle_command_ack(payload)
            return
        if topic == TOPIC_LINK_TEST_RESULT:
            if self.on_link_test:
                self.on_link_test(payload)
            return
        if topic == TOPIC_PASIFIK_STATUSTEXT:
            self.handle_statustext(payload)
            return
        if topic == TOPIC_COMMAND_RESULT:
            self.handle_command_result(payload)
            return
        if topic == TOPIC_CALIBRATION_PROGRESS:
            self.handle_calibration_progress(payload)
            return

        self.handle_agent_message(topic, payload)

    def handle_agent_message(self, topic: str, payload: dict) -> None:
        topic_parts = topic.split("/")
        if len(topic_parts) != AGENT_TOPIC_PARTS:
            logger.warning(f"Ignoring message on unexpected topic: {topic}")
            return

        agent_id = topic_parts[1]
        if agent_id not in self.vehicles:
            logger.warning(f"Message from agent {agent_id}, which is not in this mission.")
            return

        message_type = topic_parts[2]
        if message_type == AGENT_TELEMETRY_TYPE:
            self.handle_telemetry(agent_id, payload)
        elif message_type == AGENT_STATUS_TYPE:
            self.handle_status(agent_id, payload)
        else:
            logger.warning(f"No handler for message type '{message_type}' (topic '{topic}').")

    def handle_telemetry(self, vehicle_id: str, payload: dict) -> None:
        self.vehicles[vehicle_id].update_telemetry(payload)
        if self.on_vehicle_changed:
            self.on_vehicle_changed(vehicle_id)

    def handle_status(self, vehicle_id: str, payload: dict) -> None:
        vehicle = self.vehicles[vehicle_id]
        previous_state = vehicle.state
        vehicle.update_status(payload)
        if vehicle.state != previous_state:
            logger.info(f"{vehicle.title} | state | {vehicle.state}")
        if self.on_vehicle_changed:
            self.on_vehicle_changed(vehicle_id)

    def handle_pasifik_status(self, payload: dict) -> None:
        """The Pasifik's state is the mission's state on the bar."""
        self.handle_status(PASIFIK_VEHICLE_ID, payload)
        if KEY_STATE not in payload:
            return
        self.mission_state = self.vehicles[PASIFIK_VEHICLE_ID].state
        if self.on_mission_changed:
            self.on_mission_changed()

    def handle_scan_progress(self, payload: dict) -> None:
        self.scan_percent = float_or_none(payload.get(KEY_SCAN_PERCENT))
        self.scan_legs_done = int_or_none(payload.get(KEY_SCAN_LEGS_DONE))
        self.scan_legs_total = int_or_none(payload.get(KEY_SCAN_LEGS_TOTAL))
        if KEY_SCAN_WAYPOINTS in payload:
            self.scan_waypoints = waypoint_list(payload[KEY_SCAN_WAYPOINTS])
        self.scan_current_sequence = int_or_none(payload.get(KEY_SCAN_CURRENT_SEQUENCE))
        if self.on_mission_changed:
            self.on_mission_changed()

    def handle_statustext(self, payload: dict) -> None:
        """One line from the Pasifik's autopilot, on its way to the operator's log."""
        severity = int_or_none(payload.get(KEY_STATUSTEXT_SEVERITY))
        text = payload.get(KEY_STATUSTEXT_TEXT)
        if severity is None or text is None:
            logger.warning("Autopilot message without a severity or a text.")
            return
        if self.on_statustext:
            self.on_statustext(severity, str(text))

    def handle_command_result(self, payload: dict) -> None:
        """The aircraft's answer to a command or a mission upload."""
        command = payload.get(KEY_COMMAND_RESULT_COMMAND)
        if command is None:
            logger.warning("Command result without a command name.")
            return
        accepted = bool(payload.get(KEY_COMMAND_RESULT_ACCEPTED, False))
        detail = str(payload.get(KEY_COMMAND_RESULT_DETAIL) or "")
        if accepted:
            logger.info(f"{command} accepted by the Pasifik. {detail}")
        else:
            logger.warning(f"{command} refused by the Pasifik. {detail}")
        if self.on_command_result:
            self.on_command_result(str(command), accepted, detail)

    def handle_calibration_progress(self, payload: dict) -> None:
        calibration = payload.get(KEY_CALIBRATION_NAME)
        state = payload.get(KEY_CALIBRATION_STATE)
        if calibration is None or state is None:
            logger.warning("Calibration progress without a calibration or a state.")
            return
        if self.on_calibration_progress:
            self.on_calibration_progress({
                "calibration": str(calibration),
                "state": str(state),
                "step": str(payload.get(KEY_CALIBRATION_STEP) or ""),
                "percent": float_or_none(payload.get(KEY_CALIBRATION_PERCENT)),
                "detail": str(payload.get(KEY_CALIBRATION_DETAIL) or ""),
            })

    def handle_detection_frame(self, payload: dict) -> None:
        encoded_image = payload.get(DETECTION_KEY_IMAGE)
        if not encoded_image:
            logger.warning("Detection message without image data, nothing to review.")
            return
        try:
            image_bytes = base64.b64decode(encoded_image)
        except (binascii.Error, TypeError, ValueError):
            logger.warning("Detection image data is not valid base64.")
            return

        logger.info("Detection received, waiting for the operator's verdict.")
        if self.on_detection:
            self.on_detection(image_bytes, payload)

    def handle_target(self, payload: dict) -> None:
        target_id = payload.get(KEY_TARGET_ID)
        if target_id is None:
            logger.warning("Target message without a target id.")
            return

        existing = self.targets.get(str(target_id))
        if existing is None:
            target = target_from_payload(payload)
            if target is None:
                return
            self.targets[target.target_id] = target
        else:
            existing.update_from(payload)

        if self.on_targets_changed:
            self.on_targets_changed()

    def handle_map_tile(self, payload: dict) -> None:
        """One square of the live map is ready on the disk.

        The message carries a path, not a picture: the ground station wrote the
        tile on this same laptop, and sending it through the broker as well
        would put the whole scan across the loopback twice.
        """
        tile_id = payload.get(KEY_TILE_ID)
        path = payload.get(KEY_TILE_PATH)
        latitude = float_or_none(payload.get(KEY_TILE_LATITUDE))
        longitude = float_or_none(payload.get(KEY_TILE_LONGITUDE))
        metres_per_pixel = float_or_none(payload.get(KEY_TILE_METRES_PER_PIXEL))
        size_pixels = int_or_none(payload.get(KEY_TILE_SIZE_PIXELS))
        revision = int_or_none(payload.get(KEY_TILE_REVISION))
        session = int_or_none(payload.get(KEY_TILE_SESSION))
        if tile_id is None or path is None or latitude is None or longitude is None:
            logger.warning("A map tile arrived without a name, a path or a place.")
            return
        if metres_per_pixel is None or size_pixels is None or revision is None or session is None:
            logger.warning(f"Map tile {tile_id} arrived without its scale, revision or session.")
            return

        if self.on_map_tile:
            self.on_map_tile({
                "tile_id": str(tile_id),
                "latitude": latitude,
                "longitude": longitude,
                "metres_per_pixel": metres_per_pixel,
                "size_pixels": size_pixels,
                "path": str(path),
                "revision": revision,
                "session": session,
            })

    def handle_health(self, payload: dict) -> None:
        reported_links = payload.get(KEY_HEALTH_LINKS, [])
        if isinstance(reported_links, list):
            self.links = [
                link
                for link in (link_from_payload(entry) for entry in reported_links
                             if isinstance(entry, dict))
                if link is not None
            ]
        else:
            logger.warning("Health message carries no usable link list.")

        tracker_payload = payload.get(KEY_HEALTH_TRACKER)
        if isinstance(tracker_payload, dict):
            self.tracker = tracker_from_payload(tracker_payload)

        # nothing is recorded until the ground station says it is
        self.recording = bool(payload.get(KEY_HEALTH_RECORDING, False))

        if self.on_health_changed:
            self.on_health_changed()

    def handle_command_ack(self, payload: dict) -> None:
        command = payload.get(KEY_COMMAND)
        vehicle_id = payload.get(KEY_COMMAND_VEHICLE)
        if command is None or vehicle_id is None:
            logger.warning("Command acknowledgement without a command or a vehicle.")
            return
        if command != self.pending_command:
            logger.warning(f"Acknowledgement for '{command}' arrived, which is not pending.")
            return

        self.acknowledged_vehicles.add(str(vehicle_id))
        if self.on_command_ack:
            self.on_command_ack(command, str(vehicle_id))


def float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def waypoint_list(value) -> list:
    """Keep only the well-formed waypoints out of a message, in the order sent."""
    if not isinstance(value, list):
        return []
    waypoints = []
    for entry in value:
        waypoint = waypoint_from_payload(entry)
        if waypoint is not None:
            waypoints.append(waypoint)
    return waypoints
