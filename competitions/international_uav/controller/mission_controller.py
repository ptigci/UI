"""The mission state the widgets read, and the one MQTT client under it.

What the operator decides goes out in controller/operator_decisions.py; what the
ground station says comes back in controller/incoming_messages.py. This file is
what holds them together: the state both sides touch, the callbacks the window
hangs off, and the list of topics this interface listens to.

The callbacks fire on the MQTT network thread — the window bridges them onto
the Qt thread.
"""

import logging

from mqtt.mqtt_client import MqttClient
from competitions.international_uav.config import (
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
from competitions.international_uav.controller.incoming_messages import (
    PASIFIK_VEHICLE_ID,
    IncomingMessagesMixin,
)
from competitions.international_uav.controller.operator_decisions import (
    OperatorDecisionsMixin,
)
from competitions.international_uav.models import (
    Target,
    VehicleState,
    tracker_from_payload,
)

logger = logging.getLogger(__name__)

SUBSCRIBED_TOPICS = (
    TOPIC_PASIFIK_TELEMETRY,
    TOPIC_PASIFIK_STATUS,
    TOPIC_SCAN_PROGRESS,
    TOPIC_DETECTION_FRAME,
    TOPIC_AGENT_TELEMETRY_PATTERN,
    TOPIC_AGENT_STATUS_PATTERN,
    TOPIC_TARGET_CONFIRMED,
    TOPIC_TARGET_ASSIGNMENT,
    TOPIC_MAP_TILE,
    TOPIC_SYSTEM_HEALTH,
    TOPIC_COMMAND_ACK,
    TOPIC_LINK_TEST_RESULT,
    TOPIC_PASIFIK_STATUSTEXT,
    TOPIC_COMMAND_RESULT,
    TOPIC_CALIBRATION_PROGRESS,
)


class MissionController(OperatorDecisionsMixin, IncomingMessagesMixin):
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
        # The mission the Pasifik is flying, as the map draws it, and the
        # sequence number of the item it is flying to.
        self.scan_waypoints: list = []
        self.scan_current_sequence: int | None = None

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
        self.on_map_tile = None           # callable(tile fields as a dict)
        self.on_link_test = None          # callable(payload)
        self.on_statustext = None         # callable(severity, text)
        self.on_command_result = None     # callable(command, accepted, detail)
        self.on_calibration_progress = None  # callable(progress fields as a dict)

        self.mqtt_client = MqttClient()
        self.mqtt_client.on_message_callback = self.route_incoming_message
        for topic in SUBSCRIBED_TOPICS:
            self.mqtt_client.subscribe(topic)


__all__ = ["PASIFIK_VEHICLE_ID", "MissionController"]
