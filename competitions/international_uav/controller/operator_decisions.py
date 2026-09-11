"""Everything the operator decides, on its way to the ground station.

Approving a detection and marking a victim on the live map are the two ways a
place to fly to gets into the system, and they are the only two things here a
human had to be present for. The rest is the override: dropping a target,
putting one back, holding the swarm, calling it back, sending it home, and
the camera.

The Pasifik's own controls are here too: arming it, its mode, the mission it
flies and its calibrations. The ground station passes those down the Rocket
line, and the aircraft answers every one on pasifik/command/result.

A mixin on MissionController, so these keep using self.mqtt_client.
"""

import logging
import time

from competitions.international_uav.config import (
    AIRCRAFT_COMMAND_SET_MODE,
    COMMAND_ABORT,
    COMMAND_ACK_TIMEOUT_MS,
    COMMAND_DISPATCH,
    COMMAND_HOLD,
    COMMAND_RESUME,
    COMMAND_RETREAT,
    COMMAND_START_RECORDING,
    COMMAND_STOP_RECORDING,
    KEY_AIRCRAFT_COMMAND,
    KEY_AIRCRAFT_MODE,
    KEY_CALIBRATION_ACTION,
    KEY_CALIBRATION_COMMAND_NAME,
    KEY_COMMAND,
    KEY_COMMAND_TARGET,
    KEY_LINK_TEST_AGENT_IDS,
    KEY_LINK_TEST_DURATION,
    KEY_MISSION_ITEMS,
    KEY_TARGET_LATITUDE,
    KEY_TARGET_LONGITUDE,
    KEY_VERDICT,
    LINK_TEST_DURATION_S,
    TOPIC_CALIBRATION_COMMAND,
    TOPIC_DETECTION_APPROVE,
    TOPIC_DETECTION_REJECT,
    TOPIC_LINK_TEST,
    TOPIC_PASIFIK_COMMAND,
    TOPIC_PASIFIK_MISSION,
    TOPIC_SYSTEM_COMMAND,
    TOPIC_TARGET_MANUAL,
    TOPIC_TARGET_REQUEUE,
    TOPIC_TARGET_VETO,
    VERDICT_APPROVED,
    VERDICT_REJECTED,
)

logger = logging.getLogger(__name__)

MILLISECONDS_PER_SECOND = 1000


class OperatorDecisionsMixin:
    """The messages that leave because somebody pressed or clicked something."""

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

    def mark_target(self, latitude: float, longitude: float) -> None:
        """Send a victim the operator found on the map himself.

        The detector never saw this one — the operator did, in the mosaic the
        Pasifik built. The ground station puts it in the pool beside the
        approved detections, so from there on it is an ordinary target.
        """
        self.mqtt_client.publish_json(
            TOPIC_TARGET_MANUAL,
            {KEY_TARGET_LATITUDE: latitude, KEY_TARGET_LONGITUDE: longitude},
        )
        logger.warning(f"Target marked on the map at {latitude:.6f}, {longitude:.6f}.")

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

    def retreat_swarm(self) -> None:
        """Call every agent back to the launch grid, flying or not.

        Published without waiting for acknowledgements, like DISPATCH: this one
        is the swarm's, and the Pasifik neither answers it nor does anything
        about it. What the operator watches for is the agents turning for home
        on the map. The ground station stops handing out targets when it sees
        this, so nobody is sent out again on landing.
        """
        self.mqtt_client.publish_json(
            TOPIC_SYSTEM_COMMAND, {KEY_COMMAND: COMMAND_RETREAT}
        )
        logger.warning(f"{COMMAND_RETREAT} published to the ground station.")

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
        age_milliseconds = (
            time.monotonic() - self.pending_command_monotonic
        ) * MILLISECONDS_PER_SECOND
        return age_milliseconds > COMMAND_ACK_TIMEOUT_MS

    def link_test(self, agent_ids: list[int]) -> None:
        """The DEV tab's LINK TEST: the ground station probes every link."""
        self.mqtt_client.publish_json(
            TOPIC_LINK_TEST,
            {KEY_LINK_TEST_DURATION: LINK_TEST_DURATION_S, KEY_LINK_TEST_AGENT_IDS: agent_ids},
        )

    # The Pasifik itself

    def send_aircraft_command(self, command: str) -> None:
        """ARM, FORCE_ARM, FORCE_DISARM or START_MISSION, straight to the aircraft."""
        self.mqtt_client.publish_json(TOPIC_PASIFIK_COMMAND, {KEY_AIRCRAFT_COMMAND: command})
        logger.warning(f"{command} published to the Pasifik.")

    def set_aircraft_mode(self, mode: str) -> None:
        self.mqtt_client.publish_json(
            TOPIC_PASIFIK_COMMAND,
            {KEY_AIRCRAFT_COMMAND: AIRCRAFT_COMMAND_SET_MODE, KEY_AIRCRAFT_MODE: mode},
        )
        logger.warning(f"{AIRCRAFT_COMMAND_SET_MODE} {mode} published to the Pasifik.")

    def send_mission(self, items: list[dict]) -> None:
        """A mission read out of a Mission Planner file, for the aircraft to upload."""
        self.mqtt_client.publish_json(TOPIC_PASIFIK_MISSION, {KEY_MISSION_ITEMS: items})
        logger.info(f"Mission of {len(items)} items published to the Pasifik.")

    def send_calibration_command(self, calibration: str, action: str) -> None:
        self.mqtt_client.publish_json(
            TOPIC_CALIBRATION_COMMAND,
            {KEY_CALIBRATION_COMMAND_NAME: calibration, KEY_CALIBRATION_ACTION: action},
        )
        logger.info(f"Calibration {calibration} {action} published to the Pasifik.")
