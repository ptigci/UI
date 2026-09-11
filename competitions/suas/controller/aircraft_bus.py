"""The aircraft's own controls on the mission bus, and what it says back.

Arming, the modes, starting the mission, uploading one and running a
calibration go out here; the autopilot's own words, the answer to each
command once its outcome is known, and the progress of a calibration come
back. Every command is answered twice: first on the acknowledgement topic,
matched on its command id like every other press, then on the result topic
when the aircraft knows what came of it.

A mixin on SuasController, so these keep using self.mqtt_client,
self.next_command_id and the pending ids the acknowledgements are matched on.
Callbacks fire on the MQTT network thread; nothing here touches a widget.
"""

import logging
import time

from competitions.suas.config import (
    ACTION_SET_MODE,
    KEY_AIRCRAFT_ACTION,
    KEY_AIRCRAFT_BUS_TIMESTAMP,
    KEY_AIRCRAFT_COMMAND_ID,
    KEY_AIRCRAFT_FLIGHT_MODE,
    KEY_CALIBRATION_ACTION,
    KEY_CALIBRATION_COMMAND_ID,
    KEY_CALIBRATION_COMMAND_NAME,
    KEY_CALIBRATION_DETAIL,
    KEY_CALIBRATION_NAME,
    KEY_CALIBRATION_PERCENT,
    KEY_CALIBRATION_STATE,
    KEY_CALIBRATION_STEP,
    KEY_COMMAND_RESULT_ACCEPTED,
    KEY_COMMAND_RESULT_COMMAND,
    KEY_COMMAND_RESULT_DETAIL,
    KEY_MISSION_ITEMS,
    KEY_MISSION_UPLOAD_ID,
    KEY_STATUSTEXT_SEVERITY,
    KEY_STATUSTEXT_TEXT,
    TOPIC_AIRCRAFT_COMMAND,
    TOPIC_CALIBRATION_COMMAND,
    TOPIC_CALIBRATION_PROGRESS,
    TOPIC_COMMAND_RESULT,
    TOPIC_MISSION_UPLOAD,
    TOPIC_STATUSTEXT,
)
from competitions.suas.controller.wire_values import float_or_none, int_or_none

logger = logging.getLogger(__name__)

# What the aircraft sends on this half of the bus. Counted as proof the
# mission link is alive, like the rest of its topics.
AIRCRAFT_BUS_TOPICS = (TOPIC_STATUSTEXT, TOPIC_COMMAND_RESULT, TOPIC_CALIBRATION_PROGRESS)


class AircraftBusMixin:
    """What the FLIGHT and CALIBRATION tabs send, and what comes back for them."""

    # Incoming data

    def route_aircraft_bus_message(self, topic: str, payload: dict) -> None:
        if topic == TOPIC_STATUSTEXT:
            self.handle_statustext(payload)
        elif topic == TOPIC_COMMAND_RESULT:
            self.handle_command_result(payload)
        elif topic == TOPIC_CALIBRATION_PROGRESS:
            self.handle_calibration_progress(payload)

    def handle_statustext(self, payload: dict) -> None:
        """One line from the autopilot, on its way to the log under the map."""
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
            logger.info(f"{command} accepted by the aircraft. {detail}")
        else:
            logger.warning(f"{command} refused by the aircraft. {detail}")
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

    # Outgoing commands

    def send_aircraft_command(self, action: str, flight_mode: str = "") -> str:
        """Arm, disarm, start the mission or ask for a mode.

        Returns:
            str: The command id the acknowledgement will carry.
        """
        command_id = self.next_command_id()
        self.pending_aircraft_command_id = command_id
        payload = {
            KEY_AIRCRAFT_COMMAND_ID: command_id,
            KEY_AIRCRAFT_ACTION: action,
            KEY_AIRCRAFT_BUS_TIMESTAMP: time.time(),
        }
        if flight_mode:
            payload[KEY_AIRCRAFT_FLIGHT_MODE] = flight_mode
        self.mqtt_client.publish_json(TOPIC_AIRCRAFT_COMMAND, payload)
        logger.info(f"Aircraft command '{action}' sent as {command_id}.")
        return command_id

    def set_aircraft_mode(self, flight_mode: str) -> str:
        return self.send_aircraft_command(ACTION_SET_MODE, flight_mode)

    def send_mission(self, items: list) -> str:
        """A mission read from a Mission Planner export, item by item."""
        command_id = self.next_command_id()
        self.pending_aircraft_command_id = command_id
        self.mqtt_client.publish_json(TOPIC_MISSION_UPLOAD, {
            KEY_MISSION_UPLOAD_ID: command_id,
            KEY_MISSION_ITEMS: items,
            KEY_AIRCRAFT_BUS_TIMESTAMP: time.time(),
        })
        logger.info(f"Mission of {len(items)} items sent as {command_id}.")
        return command_id

    def send_calibration_command(self, calibration: str, action: str) -> str:
        command_id = self.next_command_id()
        self.pending_calibration_command_id = command_id
        self.mqtt_client.publish_json(TOPIC_CALIBRATION_COMMAND, {
            KEY_CALIBRATION_COMMAND_ID: command_id,
            KEY_CALIBRATION_COMMAND_NAME: calibration,
            KEY_CALIBRATION_ACTION: action,
            KEY_AIRCRAFT_BUS_TIMESTAMP: time.time(),
        })
        logger.info(f"Calibration {calibration}: {action} sent as {command_id}.")
        return command_id
