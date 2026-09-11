"""The Pasifik's own controls on the main window, and what it says back.

Importing and starting a mission, arming, the modes and the calibrations go
out through the controller; the aircraft's answers, its autopilot's messages
and the calibration progress come back here on the Qt thread and land in the
log, on the FLIGHT card's last line and on the CALIBRATION tab.

A mixin on InternationalMainWindow, so these keep using self.controller,
self.flight_panel, self.calibration_panel and self.log_panel.
"""

from pathlib import Path

from competitions.international_uav.config import (
    AUTOPILOT_CAUTION_MAX_SEVERITY,
    AUTOPILOT_CRITICAL_MAX_SEVERITY,
    AUTOPILOT_LINE_FORMAT,
    AUTOPILOT_TAG,
    CALIBRATION_STATES,
    FLIGHT_TEXT,
)
from competitions.international_uav.mission_file import MissionFileError, read_mission_file
from theme.tokens import STATE_CAUTION, STATE_CRITICAL, STATE_INFO, STATE_NONE, STATE_OK

CALIBRATION_ACTIVE_STATES = (CALIBRATION_STATES["running"], CALIBRATION_STATES["waiting"])


class AircraftControlsMixin:
    """What the operator asks of the Pasifik, and what it answers."""

    # Operator decisions

    def import_mission(self, path: str) -> None:
        """Read a Mission Planner export and send it up, or say why not.

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
        message = FLIGHT_TEXT["mission_sent_format"].format(name=name, count=len(items))
        self.log_panel.append(message)
        self.flight_panel.show_result(message, STATE_INFO)

    def send_aircraft_command(self, command: str) -> None:
        self.controller.send_aircraft_command(command)
        self.log_panel.append(f"{command} sent to the Pasifik.")

    def set_aircraft_mode(self, mode: str) -> None:
        self.controller.set_aircraft_mode(mode)
        self.log_panel.append(f"Mode {mode} asked of the Pasifik.")

    def send_calibration_command(self, calibration: str, action: str) -> None:
        self.controller.send_calibration_command(calibration, action)
        self.log_panel.append(f"Calibration {calibration}: {action} sent to the Pasifik.")

    # Incoming data (already on the Qt thread here)

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
            self.log_panel.append(
                f"Calibration {progress['calibration']} {progress['state']}. {progress['detail']}"
            )


def autopilot_state(severity: int) -> str:
    """MAVLink's severity number as a design-system state; 0 is the worst."""
    if severity <= AUTOPILOT_CRITICAL_MAX_SEVERITY:
        return STATE_CRITICAL
    if severity <= AUTOPILOT_CAUTION_MAX_SEVERITY:
        return STATE_CAUTION
    return STATE_NONE
