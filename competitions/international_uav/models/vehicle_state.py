"""What the interface knows about one vehicle right now.

Plain state with no Qt in it: the controller fills it from MQTT messages and
the widgets read it. Any field is None until the vehicle has reported it, and
the widgets show that as missing rather than as a zero.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field

from competitions.international_uav.config import (
    KEY_AIRSPEED,
    KEY_ALTITUDE_AGL,
    KEY_ARMED,
    KEY_ASSIGNED_TARGET,
    KEY_BATTERY_PERCENT,
    KEY_BATTERY_VOLTAGE,
    KEY_GPS_FIX,
    KEY_GROUND_SPEED,
    KEY_HEADING,
    KEY_LATITUDE,
    KEY_LONGITUDE,
    KEY_MODE,
    KEY_RTK_STATUS,
    KEY_STATE,
    KEY_WAYPOINT,
    KEY_WAYPOINT_TOTAL,
    MAP_TRACK_LENGTH,
    VEHICLE_STALE_AFTER_MS,
)


@dataclass
class VehicleState:
    vehicle_id: str
    title: str
    is_pasifik: bool

    latitude: float | None = None
    longitude: float | None = None
    altitude_agl: float | None = None
    ground_speed: float | None = None
    airspeed: float | None = None
    heading: float | None = None
    battery_percent: float | None = None
    battery_voltage: float | None = None
    gps_fix: str | None = None
    rtk_status: str | None = None
    # The mission item the autopilot is flying to, and how many there are.
    # Only the Pasifik reports these, and only once its mission is read back.
    waypoint: int | None = None
    waypoint_total: int | None = None

    state: str | None = None
    mode: str | None = None
    armed: bool | None = None
    assigned_target: str | None = None

    last_message_monotonic: float | None = None
    track: deque = field(default_factory=lambda: deque(maxlen=MAP_TRACK_LENGTH))
    # Telemetry arrives on the MQTT thread and the map is drawn on Qt's, so the
    # track is written and read at the same time. Reading it without this raises
    # "deque mutated during iteration" in the middle of a paint.
    track_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update_telemetry(self, payload: dict) -> None:
        self.latitude = number_from(payload, KEY_LATITUDE, self.latitude)
        self.longitude = number_from(payload, KEY_LONGITUDE, self.longitude)
        self.altitude_agl = number_from(payload, KEY_ALTITUDE_AGL, self.altitude_agl)
        self.ground_speed = number_from(payload, KEY_GROUND_SPEED, self.ground_speed)
        self.airspeed = number_from(payload, KEY_AIRSPEED, self.airspeed)
        self.heading = number_from(payload, KEY_HEADING, self.heading)
        self.battery_percent = number_from(payload, KEY_BATTERY_PERCENT, self.battery_percent)
        self.battery_voltage = number_from(payload, KEY_BATTERY_VOLTAGE, self.battery_voltage)
        self.gps_fix = text_from(payload, KEY_GPS_FIX, self.gps_fix)
        self.rtk_status = text_from(payload, KEY_RTK_STATUS, self.rtk_status)
        self.waypoint = integer_from(payload, KEY_WAYPOINT, self.waypoint)
        self.waypoint_total = integer_from(payload, KEY_WAYPOINT_TOTAL, self.waypoint_total)
        self.mark_seen()

        if self.has_position():
            with self.track_lock:
                self.track.append((self.latitude, self.longitude))

    def update_status(self, payload: dict) -> None:
        self.state = text_from(payload, KEY_STATE, self.state)
        self.mode = text_from(payload, KEY_MODE, self.mode)
        self.assigned_target = text_from(payload, KEY_ASSIGNED_TARGET, self.assigned_target)
        if KEY_ARMED in payload:
            self.armed = bool(payload[KEY_ARMED])
        self.mark_seen()

    def mark_seen(self) -> None:
        self.last_message_monotonic = time.monotonic()

    def track_points(self) -> list[tuple[float, float]]:
        """A snapshot of where this vehicle has been, safe to draw from."""
        with self.track_lock:
            return list(self.track)

    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def age_milliseconds(self) -> float | None:
        if self.last_message_monotonic is None:
            return None
        return (time.monotonic() - self.last_message_monotonic) * 1000

    def is_stale(self) -> bool:
        age_milliseconds = self.age_milliseconds()
        if age_milliseconds is None:
            return True
        return age_milliseconds > VEHICLE_STALE_AFTER_MS


def number_from(payload: dict, key: str, previous: float | None) -> float | None:
    """Read one numeric field, keeping the old value if it is absent or junk."""
    if key not in payload:
        return previous
    try:
        return float(payload[key])
    except (TypeError, ValueError):
        return previous


def integer_from(payload: dict, key: str, previous: int | None) -> int | None:
    """Like number_from, except that a null in the message means the value is gone.

    The aircraft sends null for its waypoint until a mission is read back, and
    the card must show that as missing rather than keep an old number.
    """
    if key not in payload:
        return previous
    value = payload[key]
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return previous


def text_from(payload: dict, key: str, previous: str | None) -> str | None:
    if key not in payload:
        return previous
    value = payload[key]
    if value is None:
        return previous
    return str(value)
