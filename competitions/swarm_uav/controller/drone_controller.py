"""Publishes UI commands over MQTT and routes incoming vehicle data.

Payloads are built here and only here, using the topics from config/mqtt.toml,
so the wire format between the UI and the ground station stays in one place.
"""

import base64
import binascii
import logging
import time
from collections import deque

from competitions.swarm_uav.config import (
    CLOCK_SOURCE_PPS,
    MISSION_TARGET_AUTO_TEXT,
    PLAN_KEY_PLAN,
    PLAN_KEY_STEPS,
    PLAN_STATUS_DONE,
    PLAN_STATUS_FAILED,
    PLAN_STATUS_KEY_INDEX,
    PLAN_STATUS_KEY_PLAN,
    PLAN_STATUS_KEY_STATUS,
    PLAN_STATUS_MISSING,
    PLAN_STATUS_STARTED,
    PLAN_TEXT,
    TOPIC_ARM,
    TOPIC_CALIBRATE_COLOR,
    TOPIC_CALIBRATE_LATENCY,
    TOPIC_CALIBRATE_TAU,
    TOPIC_CAMERA_PATTERN,
    TOPIC_CLOCK_PATTERN,
    TOPIC_COLOR_ZONE,
    TOPIC_DISARM,
    TOPIC_DRONE_NUMBER,
    TOPIC_EMERGENCY,
    LINK_HEALTH_WINDOW_S,
    LINK_TEST_DURATION_S,
    LINK_TELEMETRY_RATE_HZ,
    TOPIC_ESP_LOG,
    TOPIC_LINK_TEST,
    TOPIC_LINK_TEST_RESULT,
    TOPIC_MESH_CHANNEL,
    TOPIC_FORCE_ARM,
    TOPIC_FORCE_DISARM,
    TOPIC_FORMATION,
    TOPIC_FREE,
    TOPIC_HEALTH_PATTERN,
    TOPIC_LAND,
    TOPIC_MISSION1,
    TOPIC_MISSION2,
    TOPIC_MISSION2_STATUS,
    TOPIC_MISSION_PLAN,
    TOPIC_MISSION_PLAN_RUN,
    TOPIC_MOVE,
    TOPIC_OBJECT_DETECTION_APPROVE,
    TOPIC_OBJECT_DETECTION_CANCEL,
    TOPIC_OBJECT_DETECTION_FRAMES,
    TOPIC_PLAN_STATUS_PATTERN,
    TOPIC_QR_CONTENT,
    TOPIC_QR_LOCATION,
    TOPIC_SIMULATION,
    TOPIC_STATE_PATTERN,
    TOPIC_TAKEOFF,
    TOPIC_TELEMETRY_PATTERN,
    TOPIC_WHITE_BALANCE,
)
from mqtt.mqtt_client import MqttClient
from widgets.detection_review import Detection
from competitions.swarm_uav.controller.hsv_band import band_text
from competitions.swarm_uav.controller.mission_plan import wire_steps

logger = logging.getLogger(__name__)

# Incoming topics look like "drone/{id}/{type}" — the type suffix comes from
# the subscribe patterns so config/mqtt.toml stays the single source of truth.
TELEMETRY_MESSAGE_TYPE = TOPIC_TELEMETRY_PATTERN.split("/")[-1]
CAMERA_MESSAGE_TYPE = TOPIC_CAMERA_PATTERN.split("/")[-1]
STATE_MESSAGE_TYPE = TOPIC_STATE_PATTERN.split("/")[-1]
HEALTH_MESSAGE_TYPE = TOPIC_HEALTH_PATTERN.split("/")[-1]
CLOCK_MESSAGE_TYPE = TOPIC_CLOCK_PATTERN.split("/")[-1]
PLAN_STATUS_MESSAGE_TYPE = TOPIC_PLAN_STATUS_PATTERN.split("/")[-1]

POSITION_AXES = ("x", "y", "z", "v")


class DroneController:
    """Sends commands for every vehicle and caches the latest incoming state.

    The on_telemetry / on_camera_frame callbacks fire on the MQTT network
    thread — the UI must bridge them onto the Qt thread (see MainWindow).
    """

    def __init__(self, drone_ids: list[int], vtol_ids: list[int]) -> None:
        self.drone_ids = list(drone_ids)
        self.vtol_ids = list(vtol_ids)

        all_vehicle_ids = self.drone_ids + self.vtol_ids
        self.positions: dict[int, dict] = {
            vehicle_id: dict.fromkeys(POSITION_AXES, 0.0) for vehicle_id in all_vehicle_ids
        }
        self.states: dict[int, str] = {}
        self.last_message_monotonic: dict[int, float] = {}
        self.first_message_monotonic: dict[int, float] = {}
        # When each drone's position messages arrived, inside the health window.
        self.telemetry_arrivals: dict[int, deque] = {}
        self.camera_stream_active: dict[int, bool] = {}
        # What is steering each drone clock, as last reported. A drone not
        # in here has said nothing about its clock yet.
        self.clock_sources: dict[int, str] = {}

        # The uploaded mission plan, kept so the drones' progress reports can
        # be shown as the step descriptions the operator typed.
        self.mission_plan_id = 0
        self.mission_plan_steps: list = []

        self.on_telemetry = None        # callable(vehicle_id, payload)
        self.on_camera_frame = None     # callable(vehicle_id, image_bytes or None)
        self.on_state = None            # callable(vehicle_id, state_text)
        self.on_health = None           # callable(vehicle_id, payload)
        self.on_clock = None            # callable(vehicle_id, payload)
        self.on_plan_status = None      # callable(vehicle_id, payload)
        self.on_qr_content = None       # callable(payload)
        self.on_color_zone = None       # callable(payload)
        self.on_detection_frame = None  # callable(image_bytes, payload)
        self.on_esp_message = None      # callable(payload)
        self.on_link_test = None        # callable(payload)
        self.on_mission2_status = None  # callable(payload)

        self.mqtt_client = MqttClient()
        self.mqtt_client.on_message_callback = self.route_incoming_message
        self.mqtt_client.subscribe(TOPIC_TELEMETRY_PATTERN)
        self.mqtt_client.subscribe(TOPIC_CAMERA_PATTERN)
        self.mqtt_client.subscribe(TOPIC_STATE_PATTERN)
        self.mqtt_client.subscribe(TOPIC_HEALTH_PATTERN)
        self.mqtt_client.subscribe(TOPIC_CLOCK_PATTERN)
        self.mqtt_client.subscribe(TOPIC_PLAN_STATUS_PATTERN)
        self.mqtt_client.subscribe(TOPIC_QR_CONTENT)
        self.mqtt_client.subscribe(TOPIC_COLOR_ZONE)
        self.mqtt_client.subscribe(TOPIC_OBJECT_DETECTION_FRAMES)
        self.mqtt_client.subscribe(TOPIC_ESP_LOG)
        self.mqtt_client.subscribe(TOPIC_LINK_TEST_RESULT)

        # The count alone sets the ground station up; only the refresh button
        # sends it on to the drones, so starting the UI never resets a swarm.
        self.publish_vehicle_count(refresh=False)

    def vehicle_name(self, vehicle_id: int) -> str:
        if vehicle_id in self.vtol_ids:
            return f"VTOL {self.vtol_ids.index(vehicle_id) + 1}"
        return f"Drone {vehicle_id}"

    def milliseconds_since_last_message(self, vehicle_id: int) -> int | None:
        last_seen = self.last_message_monotonic.get(vehicle_id)
        if last_seen is None:
            return None
        return int((time.monotonic() - last_seen) * 1000)

    def note_telemetry_arrival(self, vehicle_id: int) -> None:
        """Only the position stream counts as the link being alive: a camera
        stream over WiFi kept the label green while the mesh was dead."""
        now = time.monotonic()
        self.last_message_monotonic[vehicle_id] = now
        self.first_message_monotonic.setdefault(vehicle_id, now)
        arrivals = self.telemetry_arrivals.setdefault(vehicle_id, deque())
        arrivals.append(now)
        while arrivals and now - arrivals[0] > LINK_HEALTH_WINDOW_S:
            arrivals.popleft()

    def link_health(self, vehicle_id: int) -> tuple[int, float, float] | None:
        """(age ms, received Hz, loss %) over the window, None before the first message."""
        age_milliseconds = self.milliseconds_since_last_message(vehicle_id)
        if age_milliseconds is None:
            return None
        now = time.monotonic()
        arrivals = self.telemetry_arrivals.get(vehicle_id, deque())
        while arrivals and now - arrivals[0] > LINK_HEALTH_WINDOW_S:
            arrivals.popleft()
        # A stream younger than the window is judged over its own length,
        # else the first message reads as 96 % loss that counts down for 5 s.
        stream_age_s = now - self.first_message_monotonic[vehicle_id]
        window_s = max(min(LINK_HEALTH_WINDOW_S, stream_age_s), 1.0 / LINK_TELEMETRY_RATE_HZ)
        rate_hz = len(arrivals) / window_s
        expected = LINK_TELEMETRY_RATE_HZ * window_s
        loss_percent = max(0.0, 100.0 * (1.0 - len(arrivals) / expected))
        return age_milliseconds, rate_hz, loss_percent

    def clear_cached_readings(self) -> None:
        """Forget the positions behind a refreshed screen, so nothing older
        than the refresh is drawn again. The message times stay: a refresh
        says nothing about the link, and clearing them showed every drone as
        "no data" on a link that never dropped."""
        for position in self.positions.values():
            position.update(dict.fromkeys(POSITION_AXES, 0.0))

    def set_vehicle_ids(self, drone_ids: list[int], vtol_ids: list[int]) -> str:
        """Apply a new vehicle layout (refresh) and announce the new count."""
        self.drone_ids = list(drone_ids)
        self.vtol_ids = list(vtol_ids)
        for vehicle_id in self.drone_ids + self.vtol_ids:
            self.positions.setdefault(vehicle_id, dict.fromkeys(POSITION_AXES, 0.0))
        return self.publish_vehicle_count(refresh=True)

    # Commands

    def publish_vehicle_count(self, refresh: bool) -> str:
        """Announce the vehicle count; with refresh the drones reset for a new mission."""
        # the mesh swarm counts drones; VTOL-only modes announce their VTOLs
        vehicle_count = len(self.drone_ids) or len(self.vtol_ids)
        self.mqtt_client.publish_json(
            TOPIC_DRONE_NUMBER, {"drone_number": vehicle_count, "refresh": refresh}
        )
        if refresh:
            return f"Refresh sent to {vehicle_count} drones; each answers when it is reset."
        return f"Drone count set to {vehicle_count}"

    def set_simulation(self, simulation_enabled: bool) -> str:
        self.mqtt_client.publish_json(
            TOPIC_SIMULATION, {"simulation": simulation_enabled}
        )
        return f"Simulation mode published: {str(simulation_enabled).lower()}"

    def arm(self, vehicle_ids) -> str:
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(TOPIC_ARM, {"drone_ids": target_ids})
        return f"Arm command sent to {target_names}."

    def disarm(self, vehicle_ids) -> str:
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(TOPIC_DISARM, {"drone_ids": target_ids})
        return f"Disarm command sent to {target_names}."

    def force_arm(self, vehicle_ids) -> str:
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(TOPIC_FORCE_ARM, {"drone_ids": target_ids})
        return f"Force arm command sent to {target_names}."

    def force_disarm(self, vehicle_ids) -> str:
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(TOPIC_FORCE_DISARM, {"drone_ids": target_ids})
        return f"Force disarm command sent to {target_names}."

    def takeoff(self, vehicle_ids, altitude: float) -> str:
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(
            TOPIC_TAKEOFF, {"drone_ids": target_ids, "altitude": altitude}
        )
        return f"Takeoff command sent to {target_names}. Altitude = {altitude} m"

    def land(self, vehicle_ids) -> str:
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(TOPIC_LAND, {"drone_ids": target_ids})
        return f"Land command sent to {target_names}."

    def move(self, vehicle_ids, x_offset: float, y_offset: float, z_offset: float) -> str:
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(
            TOPIC_MOVE,
            {"drone_ids": target_ids, "x": x_offset, "y": y_offset, "z": z_offset},
        )
        return f"Move command sent to {target_names}. x={x_offset}, y={y_offset}, z={z_offset}"

    def link_test(self, vehicle_ids: list, swarm_only: bool, channel) -> str:
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(
            TOPIC_LINK_TEST,
            {
                "duration_s": LINK_TEST_DURATION_S, "drone_ids": target_ids,
                "swarm_only": swarm_only, "channel": channel,
            },
        )
        where = ""
        if channel is not None:
            where = f" on channel {channel}"
        if not target_ids:
            return f"Link test started with no drone ticked: only the air{where} is checked."
        if swarm_only:
            return (
                f"Link test started, swarm only: {target_names} and the ground station "
                f"probe the mesh{where} for {LINK_TEST_DURATION_S:.0f} s with the bridges left alone."
            )
        return (
            f"Link test started: {target_names} and the ground station probe the mesh{where} "
            f"for {LINK_TEST_DURATION_S:.0f} s while their bridges listen to the air."
        )

    def set_mesh_channel(self, channel: int) -> str:
        self.mqtt_client.publish_json(TOPIC_MESH_CHANNEL, {"channel": channel})
        return f"Mesh channel change to {channel} sent; every node moves and saves it."

    def free(self, vehicle_ids) -> str:
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(TOPIC_FREE, {"drone_ids": target_ids})
        return f"Free command sent to {target_names}."

    def calibrate_tau(self, vehicle_ids) -> str:
        # the drone answers on its feedback topic; the result shows up in
        # the mesh log with the measured dead time and time constant
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(TOPIC_CALIBRATE_TAU, {"drone_ids": target_ids})
        return (
            f"Tau calibration sent to {target_names} — the drone darts a few "
            f"metres north and returns; result appears in the mesh log."
        )

    def measure_white_balance(self, vehicle_ids) -> str:
        # the camera fixes its balance on the ground it is looking at and keeps
        # it across restarts; the colour bands are measured through whatever
        # balance is in force, so this goes first
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(TOPIC_WHITE_BALANCE, {"drone_ids": target_ids})
        return (
            f"White balance measurement sent to {target_names} — it takes a "
            f"couple of seconds; calibrate the colours once it answers."
        )

    def calibrate_color(self, vehicle_ids, color_name: str, bands: list) -> str:
        # measured on that drone's own camera view, so it is sent to that drone
        # alone; it applies at once and the drone keeps it across restarts
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(
            TOPIC_CALIBRATE_COLOR,
            {"drone_ids": target_ids, "color": color_name, "bands": bands},
        )
        return f"{color_name} HSV band sent to {target_names}: {band_text(bands)}"

    def calibrate_latency(self, vehicle_ids, props_removed: bool) -> str:
        # the drone answers on its feedback topic with the measured link
        # latency and motor response, and writes both into its own config
        target_ids, target_names = self.resolve_targets(vehicle_ids)
        self.mqtt_client.publish_json(
            TOPIC_CALIBRATE_LATENCY,
            {"drone_ids": target_ids, "props_removed": props_removed},
        )
        if props_removed:
            return (
                f"Latency calibration sent to {target_names} — the motors will "
                f"spin briefly; result appears in the mesh log."
            )
        return (
            f"Link latency only sent to {target_names} — propellers not "
            f"confirmed off, so the motors stay still."
        )

    def save_qr_position(self, vehicle_id: int, qr_number: int) -> str:
        # the ground station takes the position out of the drone's own
        # telemetry and writes it into the drone config, so the mission flies
        # to the placard as it was measured on the field
        self.mqtt_client.publish_json(
            TOPIC_QR_LOCATION, {"drone_id": vehicle_id, "qr": qr_number}
        )
        return (
            f"QR {qr_number} location taken from {self.vehicle_name(vehicle_id)} — "
            f"the ground station writes it into the drone config."
        )

    def formation(
        self,
        formation_code: str,
        distance: float,
        angle: float,
        yaw: float,
        pitch: float,
        roll: float,
    ) -> str:
        self.mqtt_client.publish_json(
            TOPIC_FORMATION,
            {
                "formation": formation_code,
                "distance": distance,
                "angle": angle,
                "yaw": yaw,
                "pitch": pitch,
                "roll": roll,
            },
        )
        return (
            f"{formation_code} formation sent. distance={distance}, angle={angle}, "
            f"yaw={yaw}, pitch={pitch}, roll={roll}"
        )

    def mission1(self, target_drone_id: int | None) -> str:
        # the whole swarm receives the command; the target field is only a
        # fallback — the QR payload names the leaving drone, so None (AUTO)
        # is the competition setting
        self.mqtt_client.publish_json(
            TOPIC_MISSION1, {"drone_ids": self.drone_ids, "target_id": target_drone_id}
        )
        if target_drone_id is None:
            target_name = MISSION_TARGET_AUTO_TEXT
        else:
            target_name = self.vehicle_name(target_drone_id)
        return f"Mission 1 sent to the swarm. Target = {target_name}"

    def mission2(self, active: bool) -> str:
        # the same topic starts and ends the RC session, so the button on the
        # panel can be a toggle; ending it leaves the swarm flying where it is
        self.mqtt_client.publish_json(
            TOPIC_MISSION2, {"drone_ids": self.drone_ids, "active": active}
        )
        if active:
            return "Mission 2 sent to the swarm."
        return "Mission 2 stopped; the swarm keeps its last setpoint."

    def upload_mission_plan(self, plan_steps: list) -> str:
        """Send the operator's plan to the swarm and remember what was sent.

        Each upload gets its own id, so a drone that only received part of a
        plan can say so and the swarm never runs a half-uploaded one. The ground
        station keeps the steps to turn the drones' progress reports back into
        readable lines.
        """
        self.mission_plan_id += 1
        self.mission_plan_steps = list(plan_steps)
        self.mqtt_client.publish_json(
            TOPIC_MISSION_PLAN,
            {
                PLAN_KEY_PLAN: self.mission_plan_id,
                PLAN_KEY_STEPS: wire_steps(plan_steps),
            },
        )
        return PLAN_TEXT["uploaded"].format(
            plan=self.mission_plan_id, count=len(plan_steps)
        )

    def execute_mission_plan(self) -> str:
        """Start the uploaded plan. The swarm flies it on its own from here."""
        if not self.mission_plan_steps:
            return PLAN_TEXT["no_plan"]
        self.mqtt_client.publish_json(
            TOPIC_MISSION_PLAN_RUN, {PLAN_KEY_PLAN: self.mission_plan_id}
        )
        return PLAN_TEXT["executing"].format(
            plan=self.mission_plan_id, count=len(self.mission_plan_steps)
        )

    def emergency_stop(self) -> str:
        # the emergency topic carries no drone ids — it always stops everything
        self.mqtt_client.publish_json(TOPIC_EMERGENCY, {})
        logger.warning("EMERGENCY STOP published.")
        return "EMERGENCY STOP published."

    def approve_detection(self, detection: Detection) -> str:
        # the metadata is echoed back so the backend can match the verdict to
        # its detection; the image itself stays on the ground station
        self.mqtt_client.publish_json(
            TOPIC_OBJECT_DETECTION_APPROVE, detection.verdict_payload()
        )
        return "Object detection approved."

    def cancel_detection(self, detection: Detection) -> str:
        self.mqtt_client.publish_json(
            TOPIC_OBJECT_DETECTION_CANCEL, detection.verdict_payload()
        )
        return "Object detection cancelled."

    def resolve_targets(self, vehicle_ids) -> tuple[list[int], str]:
        if isinstance(vehicle_ids, list):
            target_ids = vehicle_ids
        else:
            target_ids = [vehicle_ids]
        target_names = ", ".join(self.vehicle_name(vehicle_id) for vehicle_id in target_ids)
        return target_ids, target_names

    # Incoming data

    def route_incoming_message(self, topic: str, payload: dict) -> None:
        if topic == TOPIC_OBJECT_DETECTION_FRAMES:
            self.handle_detection_frame(payload)
            return
        if topic == TOPIC_ESP_LOG:
            if self.on_esp_message:
                self.on_esp_message(payload)
            return
        if topic == TOPIC_LINK_TEST_RESULT:
            if self.on_link_test:
                self.on_link_test(payload)
            return
        if topic == TOPIC_MISSION2_STATUS:
            if self.on_mission2_status:
                self.on_mission2_status(payload)
            return
        if topic == TOPIC_QR_CONTENT:
            self.handle_qr_content(payload)
            return
        if topic == TOPIC_COLOR_ZONE:
            self.handle_color_zone(payload)
            return

        topic_parts = topic.split("/")
        if len(topic_parts) != 3:
            logger.warning(f"Ignoring message on unexpected topic: {topic}")
            return
        try:
            vehicle_id = int(topic_parts[1])
        except ValueError:
            logger.warning(f"Cannot parse a vehicle id from topic: {topic}")
            return

        message_type = topic_parts[2]
        if message_type == TELEMETRY_MESSAGE_TYPE:
            self.note_telemetry_arrival(vehicle_id)
            self.handle_telemetry(vehicle_id, payload)
        elif message_type == CAMERA_MESSAGE_TYPE:
            self.handle_camera(vehicle_id, payload)
        elif message_type == STATE_MESSAGE_TYPE:
            self.handle_state(vehicle_id, payload)
        elif message_type == HEALTH_MESSAGE_TYPE:
            self.handle_health(vehicle_id, payload)
        elif message_type == CLOCK_MESSAGE_TYPE:
            self.handle_clock(vehicle_id, payload)
        elif message_type == PLAN_STATUS_MESSAGE_TYPE:
            if self.on_plan_status:
                self.on_plan_status(vehicle_id, payload)
        else:
            logger.warning(f"No handler for message type '{message_type}' (topic '{topic}').")

    def handle_telemetry(self, vehicle_id: int, payload: dict) -> None:
        position = self.positions.setdefault(vehicle_id, dict.fromkeys(POSITION_AXES, 0.0))
        for axis in POSITION_AXES:
            # A drone sends null metres until the swarm origin is known; the
            # last value stands until it can place itself.
            if payload.get(axis) is not None:
                try:
                    position[axis] = float(payload[axis])
                except (TypeError, ValueError):
                    logger.warning(
                        f"{self.vehicle_name(vehicle_id)} sent a non-numeric '{axis}' value: "
                        f"{payload[axis]!r}"
                    )

        if self.on_telemetry:
            self.on_telemetry(vehicle_id, payload)

    def handle_camera(self, vehicle_id: int, payload: dict) -> None:
        vehicle_name = self.vehicle_name(vehicle_id)

        if not payload.get("available", True):
            if self.camera_stream_active.get(vehicle_id) is not False:
                logger.info(f"{vehicle_name} | camera | module not available")
            self.camera_stream_active[vehicle_id] = False
            if self.on_camera_frame:
                self.on_camera_frame(vehicle_id, None)
            return

        encoded_image = payload.get("image")
        if not encoded_image:
            logger.warning(f"{vehicle_name} | camera | message without image data")
            return
        try:
            image_bytes = base64.b64decode(encoded_image)
        except (binascii.Error, TypeError, ValueError):
            logger.warning(f"{vehicle_name} | camera | image data is not valid base64")
            return

        # log stream state changes once instead of one line per frame
        if not self.camera_stream_active.get(vehicle_id):
            logger.info(f"{vehicle_name} | camera | stream active")
            self.camera_stream_active[vehicle_id] = True

        if self.on_camera_frame:
            self.on_camera_frame(vehicle_id, image_bytes)

    def handle_state(self, vehicle_id: int, payload: dict) -> None:
        state_text = payload.get("state")
        if not isinstance(state_text, str):
            logger.warning(f"{self.vehicle_name(vehicle_id)} sent a state without text.")
            return
        # the drone repeats its state every couple of seconds; log the changes
        if self.states.get(vehicle_id) != state_text:
            logger.info(f"{self.vehicle_name(vehicle_id)} | state | {state_text}")
        self.states[vehicle_id] = state_text
        if self.on_state:
            self.on_state(vehicle_id, state_text)

    def handle_health(self, vehicle_id: int, payload: dict) -> None:
        logger.info(f"{self.vehicle_name(vehicle_id)} | gps health | {payload}")
        if self.on_health:
            self.on_health(vehicle_id, payload)

    def plan_status_line(self, payload: dict) -> str | None:
        """One drone's plan progress as a terminal line.

        The steps stay on the ground station, so a report only carries the step
        number and what happened to it; the description is looked up here.
        Reports of an older upload are dropped — they say nothing about the plan
        the swarm is flying now.
        """
        if payload.get(PLAN_STATUS_KEY_PLAN) != self.mission_plan_id:
            return None
        step_index = payload.get(PLAN_STATUS_KEY_INDEX)
        status_code = payload.get(PLAN_STATUS_KEY_STATUS)
        if not isinstance(step_index, int) or not isinstance(status_code, str):
            logger.warning(f"Unusable mission plan status ignored: {payload}")
            return None

        step_number = step_index + 1
        step_count = len(self.mission_plan_steps)
        if status_code == PLAN_STATUS_MISSING:
            return PLAN_TEXT["status_missing"].format(step=step_number)
        if status_code == PLAN_STATUS_DONE:
            return PLAN_TEXT["status_done"].format(step=step_number, count=step_count)
        if status_code == PLAN_STATUS_FAILED:
            return PLAN_TEXT["status_failed"].format(step=step_number, count=step_count)
        if status_code != PLAN_STATUS_STARTED:
            return PLAN_TEXT["status_unknown"].format(
                step=step_number, status=status_code
            )

        if not 0 <= step_index < step_count:
            logger.warning(f"Mission plan status for an unknown step: {payload}")
            return None
        return PLAN_TEXT["status_started"].format(
            step=step_number,
            count=step_count,
            description=self.mission_plan_steps[step_index].description(),
        )

    def handle_clock(self, vehicle_id: int, payload: dict) -> None:
        source = payload.get("source")
        if not isinstance(source, str):
            logger.warning(
                f"{self.vehicle_name(vehicle_id)} sent a clock report without a "
                f"source."
            )
            return
        # the report repeats every few seconds; log only the transitions
        if self.clock_sources.get(vehicle_id) != source:
            self.clock_sources[vehicle_id] = source
            logger.info(f"{self.vehicle_name(vehicle_id)} | clock | steered by {source}")
        if self.on_clock:
            self.on_clock(vehicle_id, payload)

    def drones_without_pps(self) -> list[int]:
        """The drones that have not reported a pulse of their own.

        A drone following a sibling is one of them: its clock is good
        enough to fly barriers on, and the operator still has to know its
        GPS is down before the swarm leaves the ground. A drone that has
        said nothing about its clock counts too — silence is not a lock.
        """
        return [
            drone_id for drone_id in self.drone_ids
            if self.clock_sources.get(drone_id) != CLOCK_SOURCE_PPS
        ]

    def handle_qr_content(self, payload) -> None:
        if not isinstance(payload, dict):
            logger.warning("QR content message is not a JSON object.")
            return
        logger.info(f"QR {payload.get('qr_id')} content received.")
        if self.on_qr_content:
            self.on_qr_content(payload)

    def handle_color_zone(self, payload) -> None:
        if not isinstance(payload, dict):
            logger.warning("Color zone message is not a JSON object.")
            return
        logger.info(f"Colored zone '{payload.get('color')}' detected.")
        if self.on_color_zone:
            self.on_color_zone(payload)

    def handle_detection_frame(self, payload) -> None:
        if not isinstance(payload, dict):
            logger.warning("Object detection message is not a JSON object.")
            return

        encoded_image = payload.get("image")
        if not encoded_image:
            logger.warning("Object detection message without image data.")
            return
        try:
            image_bytes = base64.b64decode(encoded_image)
        except (binascii.Error, TypeError, ValueError):
            logger.warning("Object detection image data is not valid base64.")
            return

        logger.info("Object detection frame received.")
        if self.on_detection_frame:
            self.on_detection_frame(image_bytes, payload)
