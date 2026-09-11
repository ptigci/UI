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
    ACTION_FINISH_SURVEY,
    ACTION_START_SURVEY,
    ACTION_GOTO_TARGET,
    ACTION_HOLD,
    ACTION_RELEASE,
    ACTION_START_RECORDING,
    ACTION_STOP_RECORDING,
    DECISION_APPROVE,
    DECISION_DENY,
    DETECTION_CARD_LABEL_FORMAT,
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
    KEY_FLIGHT_STATION,
    KEY_MISSION_ACTION,
    KEY_MISSION_COMMAND_ID,
    KEY_PROBE_ID,
    KEY_PROBE_SENT_AT,
    KEY_TARGET_AVERAGE_CONFIDENCE,
    KEY_TARGET_CLASS,
    KEY_TARGET_CONFIDENCE,
    KEY_TARGET_OBSERVATION_COUNT,
    KEY_TARGET_SCORE,
    KEY_TARGET_STATION,
    KEY_TARGET_FRAME_TIMESTAMP,
    KEY_TARGET_IMAGE,
    KEY_STITCH_COMMAND_ID,
    KEY_STITCH_FOLDER,
    KEY_STITCH_IMAGE,
    KEY_TARGET_LATITUDE,
    KEY_TARGET_LONGITUDE,
    KEY_TARGET_TRACK_ID,
    KEY_VIDEO_IMAGE,
    TOPIC_MAPPING_EXPORT,
    TOPIC_MISSION_COMMAND,
    TOPIC_PAYLOAD_STATE,
    TOPIC_ROUTE_PLAN,
    TOPIC_STITCH_REQUEST,
    TOPIC_STITCH_STATE,
    TOPIC_TARGET_BLACKLIST,
    TOPIC_TARGET_TRACK,
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
    TOPIC_LINK_PROBE,
    TOPIC_LINK_PROBE_REPLY,
    TOPIC_MISSION_STATE,
    TOPIC_RELEASE_COUNTDOWN,
    TOPIC_TELEMETRY,
    TOPIC_VIDEO_FRAME,
    TOPIC_WAYPOINT,
)
from competitions.suas.controller.aircraft_bus import AIRCRAFT_BUS_TOPICS, AircraftBusMixin
from competitions.suas.controller.test_bus import TEST_TOPICS, TestBus
from competitions.suas.controller.wire_values import (
    decode_image, float_or_none, int_or_none,
)
from competitions.suas.models import (
    CameraState, LapState, LinkPair, PayloadState, ReleaseState, RoutePlan,
    StitchState, TargetMapState, VehicleState,
)

logger = logging.getLogger(__name__)

MISSION_LINK_NAME = "ROCKET 2.4GHz"
SAFETY_LINK_NAME = "MAVLINK 900MHz"


# What the aircraft itself sends. Only these count as proof the mission link
# is alive: the video preview and the stitch state come from the ground
# services on this laptop and keep arriving with the aircraft switched off.
AIRCRAFT_TOPICS = (
    TOPIC_TELEMETRY,
    TOPIC_WAYPOINT,
    TOPIC_MISSION_STATE,
    TOPIC_HEALTH_LINK,
    TOPIC_COMMAND_ACK,
    TOPIC_TARGET_DETECTED,
    TOPIC_RELEASE_COUNTDOWN,
    TOPIC_CAMERA_STATE,
    TOPIC_ROUTE_PLAN,
    TOPIC_TARGET_TRACK,
    TOPIC_TARGET_BLACKLIST,
    TOPIC_PAYLOAD_STATE,
) + AIRCRAFT_BUS_TOPICS


class SuasController(AircraftBusMixin):
    """Holds the mission state the widgets read; publishes what the operator decides."""

    def __init__(self) -> None:
        self.vehicle = VehicleState()
        self.lap_state = LapState()
        self.release = ReleaseState()
        self.camera = CameraState()
        self.stitch = StitchState()
        self.route = RoutePlan()
        self.targets = TargetMapState()
        self.payload = PayloadState()
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
        self.pending_mission_command_id: str | None = None
        self.pending_aircraft_command_id: str | None = None
        self.pending_calibration_command_id: str | None = None
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
        self.on_mission_command_answered = None  # callable(status, reason)
        self.on_stitch_changed = None  # callable(image_bytes)
        self.on_route_changed = None   # callable()
        self.on_targets_changed = None  # callable()
        self.on_payload_changed = None  # callable()
        # The FLIGHT and CALIBRATION tabs: the autopilot's words, the answer
        # to each press, and where a calibration is.
        self.on_statustext = None      # callable(severity, text)
        self.on_command_result = None  # callable(command, accepted, detail)
        self.on_calibration_progress = None  # callable(progress)
        self.on_aircraft_command_answered = None  # callable(status, reason)
        self.on_calibration_command_answered = None  # callable(status, reason)
        # Set by the DEV tab's link test while it runs, and only then.
        self.on_link_probe_reply = None  # callable(payload)

        self.mqtt_client = MqttClient()
        self.mqtt_client.on_message_callback = self.route_incoming_message
        # The bench pages of the TEST tab. They share this connection and this
        # command numbering; nothing else of theirs is in here.
        self.test = TestBus(self.mqtt_client, self.next_command_id)
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
            TOPIC_STITCH_STATE,
            TOPIC_ROUTE_PLAN,
            TOPIC_TARGET_TRACK,
            TOPIC_TARGET_BLACKLIST,
            TOPIC_PAYLOAD_STATE,
            TOPIC_LINK_PROBE_REPLY,
        ) + AIRCRAFT_BUS_TOPICS + TEST_TOPICS:
            self.mqtt_client.subscribe(topic)

    # Incoming data

    def route_incoming_message(self, topic: str, payload: dict) -> None:
        if not isinstance(payload, dict):
            logger.warning(f"Ignoring a message on '{topic}' that is not a JSON object.")
            return

        if topic in AIRCRAFT_TOPICS:
            self.links.mission.mark_seen()

        if self.test.handles(topic):
            self.test.route(topic, payload)
        elif topic in AIRCRAFT_BUS_TOPICS:
            self.route_aircraft_bus_message(topic, payload)
        elif topic == TOPIC_TELEMETRY:
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
        elif topic == TOPIC_STITCH_STATE:
            self.handle_stitch_state(payload)
        elif topic == TOPIC_COMMAND_ACK:
            self.handle_command_acknowledgement(payload)
        elif topic == TOPIC_ROUTE_PLAN:
            self.handle_route_plan(payload)
        elif topic == TOPIC_TARGET_TRACK:
            self.handle_target_track(payload)
        elif topic == TOPIC_TARGET_BLACKLIST:
            self.handle_blacklist(payload)
        elif topic == TOPIC_PAYLOAD_STATE:
            self.handle_payload_state(payload)
        elif topic == TOPIC_LINK_PROBE_REPLY:
            if self.on_link_probe_reply:
                self.on_link_probe_reply(payload)
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

    def handle_stitch_state(self, payload: dict) -> None:
        """Take the ground services' word on the folder stitch.

        The preview travels as bytes for the same reason a video frame does:
        turning it into a picture is a Qt operation, and this is the network
        thread. An update with no picture in it still goes up -- "running" and
        "failed" have no picture and are worth drawing.
        """
        self.stitch.update_from(payload)
        if self.on_stitch_changed:
            self.on_stitch_changed(decode_image(payload.get(KEY_STITCH_IMAGE)))

    def handle_route_plan(self, payload: dict) -> None:
        """The aircraft is about to fly a route; the map draws it first."""
        self.route.update_from(payload)
        if self.on_route_changed:
            self.on_route_changed()

    def handle_target_track(self, payload: dict) -> None:
        self.targets.update_track_from(payload)
        if self.on_targets_changed:
            self.on_targets_changed()

    def handle_blacklist(self, payload: dict) -> None:
        self.targets.update_zones_from(payload)
        if self.on_targets_changed:
            self.on_targets_changed()

    def handle_payload_state(self, payload: dict) -> None:
        self.payload.update_from(payload)
        if self.on_payload_changed:
            self.on_payload_changed()

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

        if self.test.handle_acknowledgement(command_id, status, reason):
            return

        if command_id == self.pending_flight_command_id:
            self.pending_flight_command_id = None
            if self.on_flight_command_answered:
                self.on_flight_command_answered(status, reason)
            return

        if command_id == self.pending_camera_command_id:
            self.pending_camera_command_id = None
            if self.on_camera_command_answered:
                self.on_camera_command_answered(status, reason)
            return

        if command_id == self.pending_mission_command_id:
            self.pending_mission_command_id = None
            if self.on_mission_command_answered:
                self.on_mission_command_answered(status, reason)
            return

        if command_id == self.pending_aircraft_command_id:
            self.pending_aircraft_command_id = None
            if self.on_aircraft_command_answered:
                self.on_aircraft_command_answered(status, reason)
            return

        if command_id == self.pending_calibration_command_id:
            self.pending_calibration_command_id = None
            if self.on_calibration_command_answered:
                self.on_calibration_command_answered(status, reason)

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
            DETECTION_KEY_LABEL: card_label(payload),
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

    def send_release(self, station: str = "") -> str:
        """Ask the aircraft to open one bay.

        ``station`` names it, because each bay has its own servo. Empty leaves
        the choice to the aircraft, which is what the delivery flow wants: the
        target it is hovering over already decides which payload goes.
        """
        return self.send_flight_command(ACTION_RELEASE, station)

    def send_hold(self, station: str = "") -> str:
        """Ask the aircraft to clamp one bay shut on the payload in it.

        The aircraft drives no servo when it starts, so nothing grips a payload
        until this goes out. Empty holds every bay it is carrying.
        """
        return self.send_flight_command(ACTION_HOLD, station)

    def send_finish(self) -> str:
        """Tell the aircraft to stop chasing targets; the operator is landing it."""
        return self.send_flight_command(ACTION_FINISH)

    def send_start_recording(self) -> str:
        """Ask the aircraft to start recording, on the Pi and on the camera."""
        return self.send_camera_command(ACTION_START_RECORDING)

    def send_stop_recording(self) -> str:
        """Ask the camera to stop recording."""
        return self.send_camera_command(ACTION_STOP_RECORDING)

    def send_start_survey(self) -> str:
        """Ask the aircraft to start the survey now, waypoint or no waypoint."""
        return self.send_mission_command(ACTION_START_SURVEY, "Start survey")

    def send_finish_survey(self) -> str:
        """Ask the aircraft to end the scan now, waypoint or no waypoint."""
        return self.send_mission_command(ACTION_FINISH_SURVEY, "Scan done")

    def send_mission_command(self, action: str, description: str) -> str:
        """Publish one mission command and remember what we are waiting on."""
        command_id = self.next_command_id()
        self.pending_mission_command_id = command_id
        self.mqtt_client.publish_json(TOPIC_MISSION_COMMAND, {
            KEY_MISSION_COMMAND_ID: command_id,
            KEY_MISSION_ACTION: action,
        })
        logger.info(f"{description} sent as {command_id}.")
        return command_id

    def send_export_request(self) -> str:
        """Ask the ground services to copy the newest map to the stick now."""
        command_id = self.next_command_id()
        self.mqtt_client.publish_json(TOPIC_MAPPING_EXPORT, {
            KEY_STITCH_COMMAND_ID: command_id,
        })
        logger.info(f"Map export requested as {command_id}.")
        return command_id

    def send_link_probe(self, probe_id: int, sent_at: float) -> None:
        """One probe of the DEV tab's link test; the aircraft echoes it back."""
        self.mqtt_client.publish_json(TOPIC_LINK_PROBE, {
            KEY_PROBE_ID: probe_id,
            KEY_PROBE_SENT_AT: sent_at,
        })

    def send_stitch_request(self, folder_path: str) -> str:
        """Ask the ground services to stitch a folder of recorded frames.

        No pending id is kept: the answer is not an acknowledgement but the
        stitch state itself, which arrives on its own topic and says everything.

        Returns:
            str: The command id.
        """
        command_id = self.next_command_id()
        self.mqtt_client.publish_json(TOPIC_STITCH_REQUEST, {
            KEY_STITCH_COMMAND_ID: command_id,
            KEY_STITCH_FOLDER: folder_path,
        })
        logger.info(f"Stitch of '{folder_path}' requested as {command_id}.")
        return command_id

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

    def send_flight_command(self, action: str, station: str = "") -> str:
        """Publish one step and remember we are waiting for an answer to it.

        Returns:
            str: The command id, so the caller can start its own timer.
        """
        command_id = self.next_command_id()
        self.pending_flight_command_id = command_id
        payload = {
            KEY_FLIGHT_COMMAND_ID: command_id,
            KEY_FLIGHT_ACTION: action,
        }
        if station:
            payload[KEY_FLIGHT_STATION] = station
        self.mqtt_client.publish_json(TOPIC_FLIGHT_COMMAND, payload)
        logger.info(f"Flight command '{action}' sent as {command_id}.")
        return command_id

    def handle_link_health(self, payload: dict) -> None:
        self.links.update_mission_from(payload)
        if self.on_mission_changed:
            self.on_mission_changed()


def card_label(payload: dict) -> str:
    """The first line of a card: the class and the numbers the aircraft chooses by.

    The shared browser shows one label, so the sightings, the average and the
    score ride in it -- the operator should judge with the same figures the
    aircraft will act on if nobody answers.
    """
    return DETECTION_CARD_LABEL_FORMAT.format(
        target_class=payload.get(KEY_TARGET_CLASS),
        count=int_or_none(payload.get(KEY_TARGET_OBSERVATION_COUNT)) or 0,
        average=float_or_none(payload.get(KEY_TARGET_AVERAGE_CONFIDENCE)) or 0.0,
        score=float_or_none(payload.get(KEY_TARGET_SCORE)) or 0.0,
        station=payload.get(KEY_TARGET_STATION) or "?",
    )
