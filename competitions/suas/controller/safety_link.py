"""RTL, landing and flight termination, straight to the autopilot.

Appendix B requires RTL and termination to be activatable from the ground
control station, and rule 5.3.5 requires the safety path to run on onsite
systems with no dependency on anything outside our control. Our mission traffic
goes MQTT -> Raspberry Pi -> MAVLink, which puts two single points of failure
between the operator and the aircraft: the companion process, and the 5.8 GHz
link. Neither may sit in this path, so this talks to the Pixhawk over the
RFD900x on 900 MHz and nothing else shares it.

The landing is here for the same reason rather than because a rule asks for it.
It is the last press of a delivery test, and a press that puts the aircraft on
the ground has no business travelling through the companion computer when there
is a link that does not need it.

The test that matters is the one the safety inspector effectively runs: pull the
power on the Raspberry Pi and terminate the flight from this panel.

pymavlink is imported defensively, the way the app root imports tomllib. A
missing serial library is an install problem, and a ground station that refuses
to open is worse than one that opens and says the safety link is down.
"""

import logging
import threading
import time

try:
    from pymavlink import mavutil
except ImportError:
    mavutil = None

from competitions.suas.config import (
    SAFETY_COMMAND_LAND,
    SAFETY_COMMAND_RETURN_TO_LAUNCH,
    SAFETY_COMMAND_TERMINATE,
    SAFETY_MAVLINK_BAUD_RATE,
    SAFETY_MAVLINK_ENDPOINT,
    SAFETY_MODE_LAND,
    SAFETY_MODE_RETURN_TO_LAUNCH,
)

logger = logging.getLogger(__name__)

# MAV_CMD_DO_FLIGHTTERMINATION, and the 1 that means terminate. The number is
# spelled out rather than read off mavutil so the acknowledgement can still be
# matched when pymavlink is not installed to be asked.
FLIGHT_TERMINATION_COMMAND_NUMBER = 185
FLIGHT_TERMINATION_ACTIVATE = 1

HEARTBEAT_READ_TIMEOUT_SECONDS = 1.0
RECONNECT_DELAY_SECONDS = 2.0


class SafetyLink:
    """One MAVLink connection, used only for the commands that must always work."""

    def __init__(self) -> None:
        self.connection = None
        self.on_heartbeat = None              # callable(flight_mode)
        self.on_command_acknowledged = None   # callable(command_number)
        self.running = False
        self.reader_thread: threading.Thread | None = None

    def start(self) -> None:
        if mavutil is None:
            logger.error(
                "pymavlink is not installed, so the ground station cannot command "
                "RTL or flight termination. Appendix B requires that it can."
            )
            return
        self.running = True
        self.reader_thread = threading.Thread(target=self.read_forever, daemon=True)
        self.reader_thread.start()

    def stop(self) -> None:
        self.running = False

    def connect(self) -> bool:
        try:
            self.connection = mavutil.mavlink_connection(
                SAFETY_MAVLINK_ENDPOINT, baud=SAFETY_MAVLINK_BAUD_RATE
            )
        except Exception as connection_error:
            # pymavlink raises whatever the underlying transport raises, and a
            # dead serial port must not take the interface down with it.
            logger.error(f"Safety link could not be opened: {connection_error}")
            self.connection = None
            return False
        logger.info(
            f"Safety link listening on {SAFETY_MAVLINK_ENDPOINT} "
            f"at {SAFETY_MAVLINK_BAUD_RATE} baud."
        )
        return True

    def read_forever(self) -> None:
        """Keep the link alive and report every heartbeat, on its own thread."""
        while self.running:
            if self.connection is None and not self.connect():
                time.sleep(RECONNECT_DELAY_SECONDS)
                continue

            message = self.receive_message()
            if message is None:
                continue
            self.report(message)

    def report(self, message) -> None:
        """Pass on what the autopilot actually said, not what we hoped it said.

        A heartbeat carries the mode, which is how an RTL is confirmed — asking
        for RTL and being told the aircraft is in RTL are different facts. A
        COMMAND_ACK carries the command it belongs to, which is how a flight
        termination is confirmed.
        """
        message_type = message.get_type()
        if message_type == "HEARTBEAT" and self.on_heartbeat:
            self.on_heartbeat(str(self.connection.flightmode))
        elif message_type == "COMMAND_ACK" and self.on_command_acknowledged:
            self.on_command_acknowledged(int(message.command))

    def receive_message(self):
        try:
            return self.connection.recv_match(blocking=True, timeout=HEARTBEAT_READ_TIMEOUT_SECONDS)
        except Exception as read_error:
            logger.warning(f"Safety link dropped: {read_error}")
            self.connection = None
            return None

    # The three commands

    def send_return_to_launch(self) -> bool:
        return self.send_mode(SAFETY_MODE_RETURN_TO_LAUNCH,
                              SAFETY_COMMAND_RETURN_TO_LAUNCH)

    def send_land(self) -> bool:
        return self.send_mode(SAFETY_MODE_LAND, SAFETY_COMMAND_LAND)

    def send_mode(self, mode: str, command_name: str) -> bool:
        """Ask the autopilot for a flight mode over the safety link.

        The mode is a name rather than a number so pymavlink resolves it for
        the frame type the autopilot reports, and it is the same name a
        heartbeat has to come back carrying before the command counts as
        acknowledged. Asking and being obeyed are different facts.
        """
        if self.connection is None:
            logger.error(f"{command_name} was requested with no safety link.")
            return False
        try:
            self.connection.set_mode(mode)
        except Exception as send_error:
            logger.error(f"{command_name} could not be sent: {send_error}")
            return False
        logger.warning(f"{command_name} sent over the safety link.")
        return True

    def send_flight_termination(self) -> bool:
        if self.connection is None:
            logger.error("Flight termination was requested with no safety link.")
            return False
        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                FLIGHT_TERMINATION_COMMAND_NUMBER,
                0,
                FLIGHT_TERMINATION_ACTIVATE,
                0,
                0,
                0,
                0,
                0,
                0,
            )
        except Exception as send_error:
            logger.error(f"Flight termination could not be sent: {send_error}")
            return False
        logger.warning(f"{SAFETY_COMMAND_TERMINATE} sent over the safety link.")
        return True
