"""The aircraft's own controls on the main window, and what it says back.

Importing and starting a mission, arming, the modes and the calibrations go
out through the controller; the aircraft's acknowledgements and results, its
autopilot's messages and the calibration progress come back here on the Qt
thread and land in the log under the map, on the FLIGHT card's last line and
on the CALIBRATION tab.

A mixin on SuasMainWindow, so these keep using self.controller,
self.flight_panel, self.calibration_panel, self.log_panel and self.map_view.
"""

from pathlib import Path

from competitions.suas.config import (
    ACK_REJECTED,
    AUTOPILOT_CAUTION_MAX_SEVERITY,
    AUTOPILOT_CRITICAL_MAX_SEVERITY,
    AUTOPILOT_LINE_FORMAT,
    AUTOPILOT_TAG,
    CALIBRATION_STATES,
    CALIBRATION_TEXT,
    FLIGHT_TEXT,
)
from competitions.suas.mission_file import MissionFileError, map_coordinates, read_mission_file
from theme.tokens import STATE_CAUTION, STATE_CRITICAL, STATE_INFO, STATE_NONE, STATE_OK

CALIBRATION_ACTIVE_STATES = (CALIBRATION_STATES["running"], CALIBRATION_STATES["waiting"])


class AircraftControlsMixin:
    """What the operator asks of the aircraft, and what it answers."""

    # Operator decisions

    def import_mission(self, path: str) -> None:
        """Read a Mission Planner export, send it up and draw it, or say why not.

        A file with one bad line sends nothing: the upload result would only
        have said the same thing later, from further away.
        """
        name = Path(path).name
        try:
            items = read_mission_file(path)
        except MissionFileError as error:
            message = FLIGHT_TEXT["mission_file_error_format"].format(name=name, reason=error)
            self.log_panel.append(message, STATE_CRITICAL)
            self.flight_panel.show_result(message, STATE_CRITICAL)
            return
        self.controller.send_mission(items)
        self.map_view.show_waypoints(map_coordinates(items))
        message = FLIGHT_TEXT["mission_sent_format"].format(name=name, count=len(items))
        self.log_panel.append(message)
        self.flight_panel.show_result(message, STATE_INFO)

    def send_aircraft_command(self, action: str) -> None:
        self.controller.send_aircraft_command(action)
        self.log_panel.append(FLIGHT_TEXT["command_sent_format"].format(command=action))

    def set_aircraft_mode(self, mode: str) -> None:
        self.controller.set_aircraft_mode(mode)
        self.log_panel.append(FLIGHT_TEXT["mode_sent_format"].format(mode=mode))

    def send_calibration_command(self, calibration: str, action: str) -> None:
        self.controller.send_calibration_command(calibration, action)
        self.log_panel.append(
            CALIBRATION_TEXT["command_sent_format"].format(calibration=calibration, action=action)
        )

    # Incoming data (already on the Qt thread here)

    def handle_aircraft_command_answer(self, status: str, reason: str) -> None:
        """The acknowledgement: the aircraft took the press, or refused it outright."""
        if status == ACK_REJECTED:
            text = FLIGHT_TEXT["ack_rejected_format"].format(reason=reason)
            self.log_panel.append(text, STATE_CRITICAL)
            self.flight_panel.show_result(text, STATE_CRITICAL)
            return
        text = FLIGHT_TEXT["ack_accepted_text"]
        self.log_panel.append(text)
        self.flight_panel.show_result(text, STATE_INFO)

    def handle_calibration_command_answer(self, status: str, reason: str) -> None:
        if status == ACK_REJECTED:
            self.log_panel.append(
                CALIBRATION_TEXT["command_rejected_format"].format(reason=reason), STATE_CRITICAL
            )

    def handle_command_result(self, command: str, accepted: bool, detail: str) -> None:
        """The aircraft's answer: in the log, and on the FLIGHT card's last line."""
        if accepted:
            text = FLIGHT_TEXT["result_accepted_format"].format(command=command, detail=detail)
            self.log_panel.append(text)
            self.flight_panel.show_result(text, STATE_OK)
            return
        text = FLIGHT_TEXT["result_refused_format"].format(command=command, detail=detail)
        self.log_panel.append(text, STATE_CRITICAL)
        self.flight_panel.show_result(text, STATE_CRITICAL)

    def handle_statustext(self, severity: int, text: str) -> None:
        """One line from the autopilot, coloured by how bad it is.

        A warning or worse also takes the FLIGHT card's last line, so a refused
        arm is read where the ARM button is; a newer answer replaces it.
        """
        line = AUTOPILOT_LINE_FORMAT.format(tag=AUTOPILOT_TAG, text=text)
        state = autopilot_state(severity)
        self.log_panel.append(line, state)
        if state != STATE_NONE:
            self.flight_panel.show_result(line, state)

    def handle_calibration_progress(self, progress: dict) -> None:
        self.calibration_panel.show_progress(progress)
        # The steps go past on the tab; only the end of a calibration is log-worthy.
        if progress["state"] not in CALIBRATION_ACTIVE_STATES:
            self.log_panel.append(CALIBRATION_TEXT["finished_format"].format(**progress))


def autopilot_state(severity: int) -> str:
    """MAVLink's severity number as a design-system state; 0 is the worst."""
    if severity <= AUTOPILOT_CRITICAL_MAX_SEVERITY:
        return STATE_CRITICAL
    if severity <= AUTOPILOT_CAUTION_MAX_SEVERITY:
        return STATE_CAUTION
    return STATE_NONE
