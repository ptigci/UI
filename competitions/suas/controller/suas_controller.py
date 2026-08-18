"""The mission bus: what the aircraft reports, and what the operator sends back.

This application never talks to the aircraft. It connects to the broker on the
ground services machine, and SUAS/computer/relay is the only thing joined to
both that broker and the aircraft's own. So everything here is one hop further
away than it looks: a command reaches the aircraft when the ground services
carry it, and a report arrives when they carried it back.

That makes all of it allowed to fail, twice over, which is fine. The mission
continues without us — perception, localisation and the release decision all run
onboard — so this holds the picture the widgets draw and sends the operator's
decisions, and nothing safety-critical. RTL, LAND and flight termination live in
safety_link.py for exactly that reason: they go straight to the autopilot over
MAVLink and depend on none of this.

Callbacks fire on the MQTT network thread. The window bridges them onto the Qt
thread; nothing here touches a widget.
"""

import base64
import binascii
import logging

from config import (
    DETECTION_KEY_CONFIDENCE,
    DETECTION_KEY_ID,
    DETECTION_KEY_LABEL,
    DETECTION_KEY_LATITUDE,
    DETECTION_KEY_LONGITUDE,
    DETECTION_KEY_TIMESTAMP,
)
from mqtt.mqtt_client import MqttClient
from competitions.suas.config import (
    ACK_REJECTED,
    ACTION_FINISH,
    ACTION_GOTO_TARGET,
    ACTION_RELEASE,
    ACTION_START_RECORDING,
    ACTION_STOP_RECORDING,
    DECISION_APPROVE,
    DECISION_DENY,
    DETECTION_OPERATOR_ID,
    KEY_ACCEPTANCE_RADIUS,
    KEY_ACK_COMMAND_ID,
    KEY_ACK_REASON,
    KEY_ACK_STATUS,
    KEY_CAMERA_ACTION,
    KEY_CAMERA_COMMAND_ID,
    KEY_CONFIRM_DECISION,
    KEY_CONFIRM_OPERATOR,
    KEY_CONFIRM_TRACK_ID,
    KEY_FLIGHT_ACTION,
    KEY_FLIGHT_COMMAND_ID,
    KEY_TARGET_CLASS,
    KEY_TARGET_CONFIDENCE,
    KEY_TARGET_FRAME_TIMESTAMP,
    KEY_TARGET_IMAGE,
    KEY_TARGET_LATITUDE,
    KEY_TARGET_LONGITUDE,
    KEY_TARGET_TRACK_ID,
    KEY_VIDEO_IMAGE,
    TOPIC_TARGET_CONFIRM,
    TOPIC_TARGET_DETECTED,
    KEY_WAYPOINT_DISTANCE,
    KEY_WAYPOINT_INDEX,
    KEY_WAYPOINT_TOTAL,
    TOPIC_CAMERA_COMMAND,
    TOPIC_CAMERA_STATE,
    TOPIC_COMMAND_ACK,
    TOPIC_FLIGHT_COMMAND,
    TOPIC_HEALTH_LINK,
    TOPIC_MISSION_STATE,
    TOPIC_RELEASE_COUNTDOWN,
    TOPIC_TELEMETRY,
    TOPIC_VIDEO_FRAME,
    TOPIC_WAYPOINT,
)
from competitions.suas.models import (
    CameraState, LapState, LinkPair, ReleaseState, VehicleState,
)

logger = logging.getLogger(__name__)

MISSION_LINK_NAME = "MQTT 5.8G"
SAFETY_LINK_NAME = "MAVLINK 900MHz"


class SuasController:
    """Holds the mission state the widgets read; publishes what the operator decides."""

    def __init__(self) -> None:
        self.vehicle = VehicleState()
        self.lap_state = LapState()
        self.release = ReleaseState()
        self.camera = CameraState()
        self.links = LinkPair(MISSION_LINK_NAME, SAFETY_LINK_NAME)

        self.waypoint_index: int | None = None
        self.waypoint_total: int | None = None
        self.waypoint_distance_metres: float | None = None
        self.acceptance_radius_metres: float | None = None

        # The press we are waiting for the aircraft to answer, so an
        # acknowledgement for something the operator has moved on from does not
        # overwrite what they are looking at now.
        self.pending_flight_command_id: str | None = None
        self.pending_camera_command_id: str | None = None
        self.sent_command_count = 0

        self.on_telemetry = None       # callable()
        self.on_mission_changed = None  # callable()
        self.on_waypoint_changed = None  # callable()
        self.on_detection = None       # callable(image_bytes, review_payload)
        self.on_release_changed = None  # callable()
        self.on_flight_command_answered = None  # callable(status, reason)
        self.on_video_frame = None     # callable(image_bytes)
        self.on_camera_changed = None  # callable()
        self.on_camera_command_answered = None  # callable(status, reason)

        self.mqtt_client = MqttClient()
        self.mqtt_client.on_message_callback = self.route_incoming_message
        for topic in (
            TOPIC_TELEMETRY,
            TOPIC_WAYPOINT,
            TOPIC_MISSION_STATE,
            TOPIC_HEALTH_LINK,
            TOPIC_COMMAND_ACK,
            TOPIC_TARGET_DETECTED,
            TOPIC_RELEASE_COUNTDOWN,
            TOPIC_CAMERA_STATE,
            TOPIC_VIDEO_FRAME,
        ):
            self.mqtt_client.subscribe(topic)

    # Incoming data

    def route_incoming_message(self, topic: str, payload: dict) -> None:
        if not isinstance(payload, dict):
            logger.warning(f"Ignoring a message on '{topic}' that is not a JSON object.")
            return

        # Anything arriving at all is proof the mission link is alive.
        self.links.mission.mark_seen()

        if topic == TOPIC_TELEMETRY:
            self.handle_telemetry(payload)
        elif topic == TOPIC_WAYPOINT:
            self.handle_waypoint(payload)
        elif topic == TOPIC_MISSION_STATE:
            self.handle_mission_state(payload)
        elif topic == TOPIC_HEALTH_LINK:
            self.handle_link_health(payload)
        elif topic == TOPIC_TARGET_DETECTED:
            self.handle_target_detected(payload)
        elif topic == TOPIC_RELEASE_COUNTDOWN:
            self.handle_release_countdown(payload)
        elif topic == TOPIC_VIDEO_FRAME:
            self.handle_video_frame(payload)
        elif topic == TOPIC_CAMERA_STATE:
            self.handle_camera_state(payload)
        elif topic == TOPIC_COMMAND_ACK:
            self.handle_command_acknowledgement(payload)
        else:
            logger.warning(f"No handler for topic '{topic}'.")

    def handle_telemetry(self, payload: dict) -> None:
        self.vehicle.update_from(payload)
        if self.on_telemetry:
            self.on_telemetry()

    def handle_waypoint(self, payload: dict) -> None:
        self.waypoint_index = int_or_none(payload.get(KEY_WAYPOINT_INDEX))
        self.waypoint_total = int_or_none(payload.get(KEY_WAYPOINT_TOTAL))
        self.waypoint_distance_metres = float_or_none(payload.get(KEY_WAYPOINT_DISTANCE))
        radius = float_or_none(payload.get(KEY_ACCEPTANCE_RADIUS))
        if radius is not None:
            self.acceptance_radius_metres = radius
        if self.on_waypoint_changed:
            self.on_waypoint_changed()

    def handle_mission_state(self, payload: dict) -> None:
        previously_valid = self.lap_state.lap_valid
        self.lap_state.update_from(payload)
        if previously_valid and not self.lap_state.lap_valid:
            # 3.7.6 sends the aircraft back to the start of the lap. It must be
            # in the log as well as on the screen, so a disputed count has both.
            logger.warning(
                f"Lap {self.lap_state.lap_in_progress()} invalidated: "
                f"{self.lap_state.lap_invalid_reason}"
            )
        if self.on_mission_changed:
            self.on_mission_changed()

    def handle_release_countdown(self, payload: dict) -> None:
        """Take the aircraft's latest word on how close the payload is to going."""
        self.release.update_from(payload)
        if self.on_release_changed:
            self.on_release_changed()

    def handle_video_frame(self, payload: dict) -> None:
        """Take one preview frame off the bus and pass the bytes up.

        Decoding base64 is cheap and happens here, on the network thread.
        Turning it into a picture is a Qt operation and does not: the window
        does that on its own thread, the same way it does a detection crop.
        """
        image_bytes = decode_image(payload.get(KEY_VIDEO_IMAGE))
        if not image_bytes:
            return

        self.camera.mark_frame()
        if self.on_video_frame:
            self.on_video_frame(image_bytes)

    def handle_camera_state(self, payload: dict) -> None:
        """Take the aircraft's word on whether the camera is recording."""
        self.camera.update_from(payload)
        if self.on_camera_changed:
            self.on_camera_changed()

    def handle_command_acknowledgement(self, payload: dict) -> None:
        """Report what the aircraft made of the operator's last press.

        Sending a command and having it acted on are different facts, and the
        gap between them is where a delivery goes wrong quietly. A refusal is a
        normal answer -- it means the mission was not at a point where the step
        made sense -- but it has to reach the operator, because nothing else on
        the screen will tell them the button did nothing.
        """
        status = payload.get(KEY_ACK_STATUS, "")
        reason = payload.get(KEY_ACK_REASON, "")

        if status == ACK_REJECTED:
            logger.warning(f"The aircraft refused a command: {reason or payload}")
        else:
            logger.info(f"Command acknowledgement: {payload}")

        command_id = payload.get(KEY_ACK_COMMAND_ID)

        if command_id == self.pending_flight_command_id:
            self.pending_flight_command_id = None
            if self.on_flight_command_answered:
                self.on_flight_command_answered(status, reason)
            return

        if command_id == self.pending_camera_command_id:
            self.pending_camera_command_id = None
            if self.on_camera_command_answered:
                self.on_camera_command_answered(status, reason)

    def handle_target_detected(self, payload: dict) -> None:
        """Turn an aircraft detection into something the review browser reads.

        The aircraft's field names and the shared browser's are different
        vocabularies on purpose -- one is our wire contract, the other belongs
        to a widget three competitions use -- so the translation happens here,
        at the boundary, and neither side learns about the other.

        A detection with no usable crop still raises a card. §3.6.3 does not
        score detection, and a card with no picture is far better than a target
        the operator never hears about.
        """
        track_id = payload.get(KEY_TARGET_TRACK_ID)
        if track_id is None:
            logger.warning("Detection message without a track id, ignored.")
            return

        review_payload = {
            DETECTION_KEY_ID: track_id,
            DETECTION_KEY_LABEL: payload.get(KEY_TARGET_CLASS),
            DETECTION_KEY_CONFIDENCE: payload.get(KEY_TARGET_CONFIDENCE),
            DETECTION_KEY_LATITUDE: payload.get(KEY_TARGET_LATITUDE),
            DETECTION_KEY_LONGITUDE: payload.get(KEY_TARGET_LONGITUDE),
            DETECTION_KEY_TIMESTAMP: payload.get(KEY_TARGET_FRAME_TIMESTAMP),
        }

        logger.info(f"Target {track_id} is waiting for a verdict.")
        if self.on_detection:
            self.on_detection(self.decoded_crop(payload), review_payload)

    def decoded_crop(self, payload: dict) -> bytes:
        """The detection's picture as bytes, empty when there is not one."""
        encoded = payload.get(KEY_TARGET_IMAGE)
        if not encoded:
            logger.warning("Detection carried no crop; the card has no picture.")
            return b""

        image_bytes = decode_image(encoded)
        if not image_bytes:
            logger.warning("Detection crop is not valid base64; card has no picture.")
        return image_bytes

    # Outgoing decisions

    def approve_detection(self, detection) -> dict:
        """Tell the aircraft this target may be delivered on."""
        return self.send_verdict(detection, DECISION_APPROVE)

    def reject_detection(self, detection) -> dict:
        """Tell the aircraft to reject this target and blacklist its place."""
        return self.send_verdict(detection, DECISION_DENY)

    def send_verdict(self, detection, decision: str) -> dict:
        """Publish one verdict.

        The picture does not go back: it has already been looked at, and a
        base64 blob on a congested 2.4 GHz link buys nothing.
        """
        payload = {
            KEY_CONFIRM_TRACK_ID: detection.detection_id(),
            KEY_CONFIRM_DECISION: decision,
            KEY_CONFIRM_OPERATOR: DETECTION_OPERATOR_ID,
        }
        self.mqtt_client.publish_json(TOPIC_TARGET_CONFIRM, payload)
        logger.info(f"Target {detection.detection_id()}: {decision}.")
        return payload

    # The operator's delivery steps

    def send_goto_target(self) -> str:
        """Ask the aircraft to fly its planned route to the next target."""
        return self.send_flight_command(ACTION_GOTO_TARGET)

    def send_release(self) -> str:
        """Ask the aircraft to release on the target it is hovering over."""
        return self.send_flight_command(ACTION_RELEASE)

    def send_finish(self) -> str:
        """Tell the aircraft to stop chasing targets; the operator is landing it."""
        return self.send_flight_command(ACTION_FINISH)

    def send_start_recording(self) -> str:
        """Ask the camera to start recording to its own card."""
        return self.send_camera_command(ACTION_START_RECORDING)

    def send_stop_recording(self) -> str:
        """Ask the camera to stop recording."""
        return self.send_camera_command(ACTION_STOP_RECORDING)

    def send_camera_command(self, action: str) -> str:
        """Publish one camera command and wait to be told what came of it.

        Returns:
            str: The command id.
        """
        command_id = self.next_command_id()
        self.pending_camera_command_id = command_id
        self.mqtt_client.publish_json(TOPIC_CAMERA_COMMAND, {
            KEY_CAMERA_COMMAND_ID: command_id,
            KEY_CAMERA_ACTION: action,
        })
        logger.info(f"Camera command '{action}' sent as {command_id}.")
        return command_id

    def next_command_id(self) -> str:
        """An id of ours, unique for this session.

        It comes back on the acknowledgement, which is how a late answer to a
        press the operator has already moved past is told from the answer to
        the one they are watching.
        """
        self.sent_command_count += 1
        return f"{DETECTION_OPERATOR_ID}-{self.sent_command_count}"

    def send_flight_command(self, action: str) -> str:
        """Publish one step and remember we are waiting for an answer to it.

        Returns:
            str: The command id, so the caller can start its own timer.
        """
        command_id = self.next_command_id()
        self.pending_flight_command_id = command_id
        self.mqtt_client.publish_json(TOPIC_FLIGHT_COMMAND, {
            KEY_FLIGHT_COMMAND_ID: command_id,
            KEY_FLIGHT_ACTION: action,
        })
        logger.info(f"Flight command '{action}' sent as {command_id}.")
        return command_id

    def handle_link_health(self, payload: dict) -> None:
        self.links.update_mission_from(payload)
        if self.on_mission_changed:
            self.on_mission_changed()


def decode_image(encoded) -> bytes:
    """Base64 to bytes, empty when it was not base64.

    Both pictures on this bus arrive the same way — the detection crop and the
    preview frame — and both would rather be missing than raise on the network
    thread.
    """
    if not encoded:
        return b""
    try:
        return base64.b64decode(encoded)
    except (binascii.Error, TypeError, ValueError):
        return b""


def int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
