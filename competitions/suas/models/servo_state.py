"""Where each release servo was last driven, as the aircraft last said.

The bays are on the autopilot's servo rail, so what comes down is the output
number and the pulse width the aircraft asked for -- not a position it made
itself.

This is the only thing that tells a servo that moved from a press that went
nowhere. The aircraft drives no servo when it starts up -- a bay that closed on
its own would close on the hand loading it -- so a station nobody has pressed
reports "unknown", and that is a real answer rather than a missing one.

The aircraft sends the stations as a list, so they keep the order it uses and
the rows on the monitor do not swap places between messages.
"""

import time

from competitions.suas.config import (
    KEY_SERVO_MOVED_AT,
    KEY_SERVO_OUTPUT,
    KEY_SERVO_PULSE,
    KEY_SERVO_SIMULATED,
    KEY_SERVO_STATE,
    KEY_SERVO_STATION,
    KEY_SERVO_STATIONS,
    SERVO_STATE_UNKNOWN,
)


class ServoStation:
    """One servo: where it went, on which output, and whether it really moved."""

    def __init__(self, station: str, state: str, position, servo_output,
                 simulated: bool, moved_at) -> None:
        self.station = station
        self.state = state
        self.position = position
        self.servo_output = servo_output
        self.simulated = simulated
        self.moved_at = moved_at


class ServoState:
    """Every servo the aircraft reported, in the order it reported them."""

    def __init__(self) -> None:
        self.stations: list[ServoStation] = []

    def update_from(self, payload: dict) -> None:
        stations = payload.get(KEY_SERVO_STATIONS)
        if not isinstance(stations, list):
            return
        self.stations = [
            read_station(entry) for entry in stations if isinstance(entry, dict)
        ]

    def find(self, station: str) -> ServoStation | None:
        for servo in self.stations:
            if servo.station == station:
                return servo
        return None

    def seconds_since_moved(self, station: str) -> float | None:
        """How long ago that servo moved, or None while it never has.

        The aircraft stamps the move with its own clock, so this is only as
        good as the two machines agreeing on the time. It is read as an age on
        the bench, not as a measurement.
        """
        servo = self.find(station)
        if servo is None or servo.moved_at is None:
            return None
        return time.time() - servo.moved_at


def read_station(entry: dict) -> ServoStation:
    return ServoStation(
        str(entry.get(KEY_SERVO_STATION, "")),
        str(entry.get(KEY_SERVO_STATE) or SERVO_STATE_UNKNOWN),
        number_or_none(entry.get(KEY_SERVO_PULSE)),
        number_or_none(entry.get(KEY_SERVO_OUTPUT)),
        bool(entry.get(KEY_SERVO_SIMULATED)),
        number_or_none(entry.get(KEY_SERVO_MOVED_AT)),
    )


def number_or_none(value) -> float | None:
    """A number from the wire, or None when the field is missing or spoiled."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
