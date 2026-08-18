"""Publishes operator decisions over MQTT and routes what comes back.

Every payload the Uluslararası İHA interface sends or reads is built here,
from the topics and keys in config/. The callbacks fire on the MQTT network
thread — the window bridges them onto the Qt thread.
"""

import base64
import binascii
import logging
import time

from config import DETECTION_KEY_IMAGE
from mqtt.mqtt_client import MqttClient
from competitions.international_uav.config import (
    COMMAND_ABORT,
    COMMAND_ACK_TIMEOUT_MS,
    COMMAND_DISPATCH,
    COMMAND_HOLD,
    COMMAND_RESUME,
    COMMAND_START_RECORDING,
    COMMAND_STOP_RECORDING,
    KEY_COMMAND,
    KEY_COMMAND_TARGET,
    KEY_COMMAND_VEHICLE,
    KEY_HEALTH_LINKS,
    KEY_HEALTH_RECORDING,
    KEY_HEALTH_TRACKER,
    KEY_SCAN_LEGS,
    KEY_SCAN_LEGS_DONE,
    KEY_SCAN_LEGS_TOTAL,
    KEY_SCAN_PERCENT,
    KEY_SCAN_POLYGON,
    KEY_STATE,
    KEY_TARGET_ID,
    KEY_VERDICT,
    TOPIC_AGENT_STATUS_PATTERN,
    TOPIC_AGENT_TELEMETRY_PATTERN,
    TOPIC_COMMAND_ACK,
    TOPIC_DETECTION_APPROVE,
    TOPIC_DETECTION_FRAME,
    TOPIC_DETECTION_REJECT,
    TOPIC_PASIFIK_STATUS,
    TOPIC_PASIFIK_TELEMETRY,
    TOPIC_SCAN_PROGRESS,
    TOPIC_SYSTEM_COMMAND,
    TOPIC_SYSTEM_HEALTH,
    TOPIC_TARGET_ASSIGNMENT,
    TOPIC_TARGET_CONFIRMED,
    TOPIC_TARGET_REQUEUE,
    TOPIC_TARGET_VETO,
    VERDICT_APPROVED,
    VERDICT_REJECTED,
)
from competitions.international_uav.models import (
    Target,
    VehicleState,
    link_from_payload,
    target_from_payload,
    tracker_from_payload,
)

logger = logging.getLogger(__name__)

# The scanning VTOL has topics of its own, so it needs no id on the wire.
PASIFIK_VEHICLE_ID = "pasifik"

# Agent topics look like "agent/{id}/{type}"; the type comes from the
# subscribe patterns so config/mqtt.toml stays the single source of truth.
AGENT_TELEMETRY_TYPE = TOPIC_AGENT_TELEMETRY_PATTERN.split("/")[-1]
AGENT_STATUS_TYPE = TOPIC_AGENT_STATUS_PATTERN.split("/")[-1]
AGENT_TOPIC_PARTS = 3


class MissionController:
    """Holds the mission state the widgets read and sends the operator's decisions."""

    def __init__(self, pasifik: VehicleState, agents: list[VehicleState]) -> None:
        self.vehicles: dict[str, VehicleState] = {pasifik.vehicle_id: pasifik}
        for agent in agents:
            self.vehicles[agent.vehicle_id] = agent

        self.targets: dict[str, Target] = {}
        self.links: list = []
        self.tracker = tracker_from_payload({})
        self.recording = False
        self.mission_state: str | None = None
        self.scan_percent: float | None = None
        self.scan_legs_done: int | None = None
        self.scan_legs_total: int | None = None
        self.scan_polygon: list = []
        self.scan_legs: list = []

        # The mission command waiting for the vehicles to acknowledge it.
        self.pending_command: str | None = None
        self.pending_command_monotonic: float | None = None
        self.acknowledged_vehicles: set[str] = set()

        self.on_vehicle_changed = None    # callable(vehicle_id)
        self.on_targets_changed = None    # callable()
        self.on_detection = None          # callable(image_bytes, payload)
        self.on_health_changed = None     # callable()
        self.on_mission_changed = None    # callable()
        self.on_command_ack = None        # callable(command, vehicle_id)

        self.mqtt_client = MqttClient()
        self.mqtt_client.on_message_callback = self.route_incoming_message
        for topic in (
            TOPIC_PASIFIK_TELEMETRY,
            TOPIC_PASIFIK_STATUS,
            TOPIC_SCAN_PROGRESS,
            TOPIC_DETECTION_FRAME,
            TOPIC_AGENT_TELEMETRY_PATTERN,
            TOPIC_AGENT_STATUS_PATTERN,
            TOPIC_TARGET_CONFIRMED,
            TOPIC_TARGET_ASSIGNMENT,
            TOPIC_SYSTEM_HEALTH,
            TOPIC_COMMAND_ACK,
        ):
            self.mqtt_client.subscribe(topic)

    # Operator decisions

    def approve_detection(self, detection) -> dict:
        """Send the detection's identification and ground coordinate onward.

        This is the moment the swarm learns about a place to fly to: the
        ground station turns an approved detection into a target and assigns
        an agent to it.
        """
        payload = detection.verdict_payload()
        payload[KEY_VERDICT] = VERDICT_APPROVED
        self.mqtt_client.publish_json(TOPIC_DETECTION_APPROVE, payload)
        return payload

    def reject_detection(self, detection) -> dict:
        payload = detection.verdict_payload()
        payload[KEY_VERDICT] = VERDICT_REJECTED
        self.mqtt_client.publish_json(TOPIC_DETECTION_REJECT, payload)
        return payload

    def veto_target(self, target_id: str) -> None:
        self.mqtt_client.publish_json(TOPIC_TARGET_VETO, {KEY_COMMAND_TARGET: target_id})

    def requeue_target(self, target_id: str) -> None:
        self.mqtt_client.publish_json(TOPIC_TARGET_REQUEUE, {KEY_COMMAND_TARGET: target_id})

    def dispatch_swarm(self) -> None:
        """Tell the ground station to assign every approved target and go.

        Published without waiting for acknowledgements, unlike HOLD and ABORT.
        Nothing is being asked of the vehicles here — the ground station works
        out who flies where and sends the assignments itself, and the answer the
        operator watches for is the agents appearing on the map with targets.
        """
        self.mqtt_client.publish_json(
            TOPIC_SYSTEM_COMMAND, {KEY_COMMAND: COMMAND_DISPATCH}
        )
        logger.warning(f"{COMMAND_DISPATCH} published to the ground station.")

    def hold_mission(self) -> None:
        self.send_mission_command(COMMAND_HOLD)

    def resume_mission(self) -> None:
        self.send_mission_command(COMMAND_RESUME)

    def abort_mission(self) -> None:
        self.send_mission_command(COMMAND_ABORT)

    def start_recording(self) -> None:
        self.send_recording_command(COMMAND_START_RECORDING)

    def stop_recording(self) -> None:
        self.send_recording_command(COMMAND_STOP_RECORDING)

    def send_recording_command(self, command: str) -> None:
        """Ask for the Pasifik's camera to be recorded, or for it to stop.

        Published like DISPATCH, without waiting for acknowledgements: the
        ground station passes this down to the aircraft, and the answer the
        operator watches for is the recording flag in the next health report.
        """
        self.mqtt_client.publish_json(TOPIC_SYSTEM_COMMAND, {KEY_COMMAND: command})
        logger.info(f"{command} published to the ground station.")

    def send_mission_command(self, command: str) -> None:
        """Publish a mission-wide command and start waiting for its acks."""
        self.pending_command = command
        self.pending_command_monotonic = time.monotonic()
        self.acknowledged_vehicles = set()
        self.mqtt_client.publish_json(TOPIC_SYSTEM_COMMAND, {KEY_COMMAND: command})
        logger.warning(f"{command} published to every vehicle.")

    def unacknowledged_vehicles(self) -> list[str]:
        return [
            vehicle_id
            for vehicle_id in self.vehicles
            if vehicle_id not in self.acknowledged_vehicles
        ]

    def command_ack_timed_out(self) -> bool:
        if self.pending_command is None or self.pending_command_monotonic is None:
            return False
        if not self.unacknowledged_vehicles():
            return False
        age_milliseconds = (time.monotonic() - self.pending_command_monotonic) * 1000
        return age_milliseconds > COMMAND_ACK_TIMEOUT_MS

    # Incoming data

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
        if topic == TOPIC_SYSTEM_HEALTH:
            self.handle_health(payload)
            return
        if topic == TOPIC_COMMAND_ACK:
            self.handle_command_ack(payload)
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
        if KEY_SCAN_POLYGON in payload:
            self.scan_polygon = coordinate_list(payload[KEY_SCAN_POLYGON])
        if KEY_SCAN_LEGS in payload:
            self.scan_legs = coordinate_list(payload[KEY_SCAN_LEGS])
        if self.on_mission_changed:
            self.on_mission_changed()

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


def coordinate_list(value) -> list:
    """Keep only well-formed [latitude, longitude] pairs out of a message."""
    if not isinstance(value, list):
        return []
    coordinates = []
    for entry in value:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            continue
        latitude = float_or_none(entry[0])
        longitude = float_or_none(entry[1])
        if latitude is not None and longitude is not None:
            coordinates.append((latitude, longitude))
    return coordinates
