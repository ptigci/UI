"""Everything the operator sends, and whether the aircraft did it.

Split out of ``main_window.py`` because it is one subject and the window had
grown past what one file should hold. It is a mixin rather than a separate
object so the window keeps every method under its own name — nothing that reads
``window.return_to_launch()`` had to change.

The subject is the gap between pressing a button and the aircraft obeying it.
Two paths cross that gap and they fail differently:

* RTL, LAND and TERMINATE go over the direct MAVLink link and are confirmed by
  what the autopilot says afterwards — a heartbeat in the mode we asked for, or
  a COMMAND_ACK for the termination. Never by the click.
* GO TO DROP ZONE and RELEASE go over the mission bus, which is allowed to
  fail, and come back as an acknowledgement from the companion computer. A
  refusal is a normal answer there: it means the mission was not at a point
  where the step made sense.

Both get a timer, because a command that was sent and never answered looks
exactly like one that worked until the operator notices the aircraft has not
moved.
"""

import logging

from competitions.suas.config import (
    ACK_REJECTED,
    DROP_COMMAND_ACCEPTED_TEXT,
    DROP_COMMAND_REJECTED_FORMAT,
    DROP_COMMAND_SENT_TEXT,
    DROP_COMMAND_TIMEOUT_TEXT,
    MISSION_FINISH_ACCEPTED_TEXT,
    MISSION_START_ACCEPTED_TEXT,
    REFRESH_INTERVAL_MS,
    SAFETY_COMMAND_ACK_TIMEOUT_MS,
    SAFETY_COMMAND_LAND,
    SAFETY_COMMAND_RETURN_TO_LAUNCH,
    SAFETY_COMMAND_TERMINATE,
    SAFETY_MODE_LAND,
    SAFETY_MODE_RETURN_TO_LAUNCH,
)
from competitions.suas.controller.safety_link import FLIGHT_TERMINATION_COMMAND_NUMBER
from theme.tokens import STATE_CAUTION, STATE_CRITICAL, STATE_OK

logger = logging.getLogger(__name__)

# The mode a heartbeat has to come back reporting before each safety command
# counts as obeyed rather than merely sent.
SAFETY_COMMAND_MODES = {
    SAFETY_COMMAND_RETURN_TO_LAUNCH: SAFETY_MODE_RETURN_TO_LAUNCH,
    SAFETY_COMMAND_LAND: SAFETY_MODE_LAND,
}


class CommandControlMixin:
    """The window's outgoing commands and the answers to them."""

    # The safety link: RTL, LAND, TERMINATE

    def return_to_launch(self) -> None:
        if self.safety_link.send_return_to_launch():
            self.begin_safety_command(SAFETY_COMMAND_RETURN_TO_LAUNCH)
        self.stand_the_delivery_down()

    def land_aircraft(self) -> None:
        if self.safety_link.send_land():
            self.begin_safety_command(SAFETY_COMMAND_LAND)
        self.stand_the_delivery_down()

    def terminate_flight(self) -> None:
        if self.safety_link.send_flight_termination():
            self.begin_safety_command(SAFETY_COMMAND_TERMINATE)

    def begin_safety_command(self, command: str) -> None:
        """Sent is not the same as done, so the panel says which of the two it is."""
        self.pending_safety_command = command
        self.pending_safety_command_elapsed_ms = 0
        self.safety_panel.show_command_sent(command)

    def handle_safety_heartbeat(self, flight_mode: str) -> None:
        """Every heartbeat proves the safety link, and confirms a mode change took."""
        self.controller.links.safety.mark_seen()
        expected_mode = SAFETY_COMMAND_MODES.get(self.pending_safety_command)
        if expected_mode is None:
            return
        if flight_mode == expected_mode:
            self.acknowledge_safety_command()

    def handle_safety_acknowledgement(self, command_number: int) -> None:
        """A COMMAND_ACK confirms the flight termination, and only that."""
        if self.pending_safety_command != SAFETY_COMMAND_TERMINATE:
            return
        if command_number == FLIGHT_TERMINATION_COMMAND_NUMBER:
            self.acknowledge_safety_command()

    def acknowledge_safety_command(self) -> None:
        self.safety_panel.show_command_acknowledged(self.pending_safety_command)
        logger.info(f"{self.pending_safety_command} acknowledged by the autopilot.")
        self.pending_safety_command = None

    def refresh_safety_command(self) -> None:
        if self.pending_safety_command is None:
            return
        self.pending_safety_command_elapsed_ms += REFRESH_INTERVAL_MS
        if self.pending_safety_command_elapsed_ms < SAFETY_COMMAND_ACK_TIMEOUT_MS:
            return
        # An unacknowledged safety command is the worst thing on this screen to
        # leave looking like it worked.
        logger.error(f"{self.pending_safety_command} was not acknowledged by the autopilot.")
        self.safety_panel.show_command_timed_out(self.pending_safety_command)
        self.pending_safety_command = None

    # The mission bus: the delivery steps

    # The survey, started and ended by hand

    def start_survey(self) -> None:
        """The aircraft never reported the survey waypoint; start it anyway."""
        self.controller.send_start_survey()
        self.await_mission_command(MISSION_START_ACCEPTED_TEXT)

    def finish_survey(self) -> None:
        """The aircraft never reported the last waypoint; end the scan anyway."""
        self.controller.send_finish_survey()
        self.await_mission_command(MISSION_FINISH_ACCEPTED_TEXT)

    def await_mission_command(self, accepted_text: str) -> None:
        """Start the clock on a press, and remember what to say when it lands."""
        self.pending_mission_command_elapsed_ms = 0
        self.pending_mission_accepted_text = accepted_text
        self.mission_panel.show_command_sent()

    def handle_mission_command_answer(self, status: str, reason: str) -> None:
        self.pending_mission_command_elapsed_ms = None
        if status == ACK_REJECTED:
            self.mission_panel.show_command_rejected(reason)
            return
        self.mission_panel.show_command_accepted(self.pending_mission_accepted_text)

    def refresh_mission_command(self) -> None:
        """A press the aircraft never answered is said so, not left pending."""
        if self.pending_mission_command_elapsed_ms is None:
            return
        self.pending_mission_command_elapsed_ms += REFRESH_INTERVAL_MS
        if self.pending_mission_command_elapsed_ms < SAFETY_COMMAND_ACK_TIMEOUT_MS:
            return
        self.pending_mission_command_elapsed_ms = None
        self.mission_panel.show_command_timed_out()

    def go_to_drop_zone(self) -> None:
        self.begin_flight_command(self.controller.send_goto_target())

    def release_payload(self, station: str) -> None:
        """Open one bay. The button says which, because each bay has a servo."""
        self.begin_flight_command(self.controller.send_release(station))

    def hold_payload(self, station: str) -> None:
        """Clamp one bay shut on the payload that has just been loaded into it.

        The aircraft drives no servo when it starts, so this is the only thing
        that closes a bay before a flight.
        """
        self.begin_flight_command(self.controller.send_hold(station))

    def begin_flight_command(self, command_id: str) -> None:
        """Start the clock on a press, so an unanswered one does not sit silent.

        These travel the mission bus, which is allowed to fail. A command that
        goes out and is never acknowledged looks exactly like one that worked
        until the operator notices the aircraft has not moved -- by which time
        they have spent a minute of a 45-minute clock on it.
        """
        self.pending_flight_command_elapsed_ms = 0
        if self.drop_test_panel is not None:
            self.drop_test_panel.show_status(DROP_COMMAND_SENT_TEXT, STATE_CAUTION)
        self.note_delivery_sent(command_id)
        logger.info(f"Delivery step {command_id} sent to the aircraft.")

    def stand_the_delivery_down(self) -> None:
        """Tell the aircraft the delivery run is over, on the way to the ground.

        The mode change is what lands the aircraft and it does not need this.
        This is so the companion computer drops the target it was hovering over:
        without it, a RELEASE pressed by mistake during the descent still has
        something to fire at, and a spent station never comes back.

        It rides the mission bus, so it is allowed to fail. If it does, the
        aircraft works the run out for itself when the motors disarm.
        """
        if self.drop_test_panel is None:
            return
        self.controller.send_finish()

    def handle_flight_command_answer(self, status: str, reason: str) -> None:
        """Say what the aircraft made of the press, refusal included."""
        self.pending_flight_command_elapsed_ms = None
        self.note_delivery_answer(status, reason)
        if self.drop_test_panel is None:
            return

        if status == ACK_REJECTED:
            self.drop_test_panel.show_status(
                DROP_COMMAND_REJECTED_FORMAT.format(reason=reason), STATE_CRITICAL
            )
            return
        self.drop_test_panel.show_status(DROP_COMMAND_ACCEPTED_TEXT, STATE_OK)

    def refresh_flight_command(self) -> None:
        """An unanswered press is said out loud rather than left looking sent."""
        if self.pending_flight_command_elapsed_ms is None:
            return

        self.pending_flight_command_elapsed_ms += REFRESH_INTERVAL_MS
        if self.pending_flight_command_elapsed_ms < SAFETY_COMMAND_ACK_TIMEOUT_MS:
            return

        logger.error("The aircraft did not answer the last delivery step.")
        self.pending_flight_command_elapsed_ms = None
        self.note_delivery_timeout()
        if self.drop_test_panel is None:
            return
        self.drop_test_panel.show_status(DROP_COMMAND_TIMEOUT_TEXT, STATE_CRITICAL)

    # The mission bus: the mapping test

    def start_folder_stitch(self, folder_path: str) -> None:
        """Ask the ground services to stitch the folder the operator picked.

        No timer on this one either: the answer is the stitch state itself,
        which the panel draws as it arrives -- including "running", which is
        the acknowledgement.
        """
        self.controller.send_stitch_request(folder_path)
        self.mapping_panel.show_request_sent()

    # The mission bus: the camera's own recording

    def start_recording(self) -> None:
        self.controller.send_start_recording()
        self.camera_panel.show_command_sent()

    def stop_recording(self) -> None:
        self.controller.send_stop_recording()
        self.camera_panel.show_command_sent()

    def handle_camera_command_answer(self, status: str, reason: str) -> None:
        """Say what the camera made of the press.

        There is no timer on this one. The recording state is published
        retained, so a command that was acted on shows up as the label changing
        whether or not the acknowledgement reached us -- and a command that was
        not shows up as a label that did not change.
        """
        if self.camera_panel is None:
            return
        if status == ACK_REJECTED:
            self.camera_panel.show_command_rejected(reason)
            return
        self.camera_panel.show_command_accepted()
