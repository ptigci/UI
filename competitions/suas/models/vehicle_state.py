"""What the one aircraft is doing right now, in the units it arrived in.

Everything stays metric here and is converted where it is shown, so there is one
place to look when a number on screen is wrong. Anything that has not arrived
yet is None rather than zero — a zero altitude reads as information, and on this
display a wrong number is worse than a visible gap.
"""

import time

from competitions.suas.config import (
    KEY_AIRSPEED,
    KEY_ALTITUDE_AGL,
    KEY_ALTITUDE_AMSL,
    KEY_ARMED,
    KEY_BATTERY_PERCENT,
    KEY_BATTERY_SOURCE,
    KEY_BATTERY_VOLTAGE,
    KEY_GPS_FIX,
    KEY_GROUND_SPEED,
    KEY_HEADING,
    KEY_LATITUDE,
    KEY_LONGITUDE,
    KEY_MODE,
    KEY_SATELLITE_COUNT,
    KEY_TERRAIN_CLEARANCE,
    MAP_TRACK_LENGTH,
)

MILLISECONDS_PER_SECOND = 1000


class VehicleState:
    """The aircraft's live state, plus the track it has flown."""

    def __init__(self) -> None:
        self.latitude: float | None = None
        self.longitude: float | None = None
        self.altitude_agl_metres: float | None = None
        self.altitude_amsl_metres: float | None = None
        self.terrain_clearance_metres: float | None = None
        self.ground_speed_metres_per_second: float | None = None
        self.airspeed_metres_per_second: float | None = None
        self.heading_degrees: float | None = None
        self.mode: str | None = None
        self.armed: bool | None = None
        self.battery_voltage: float | None = None
        self.battery_percent: float | None = None
        self.battery_source: str | None = None
        self.gps_fix: str | None = None
        self.satellite_count: int | None = None

        self.home_latitude: float | None = None
        self.home_longitude: float | None = None
        self.track: list[tuple[float, float]] = []
        self.last_telemetry_monotonic: float | None = None

    def update_from(self, payload: dict) -> None:
        self.latitude = float_or_keep(payload.get(KEY_LATITUDE), self.latitude)
        self.longitude = float_or_keep(payload.get(KEY_LONGITUDE), self.longitude)
        self.altitude_agl_metres = float_or_keep(
            payload.get(KEY_ALTITUDE_AGL), self.altitude_agl_metres
        )
        self.altitude_amsl_metres = float_or_keep(
            payload.get(KEY_ALTITUDE_AMSL), self.altitude_amsl_metres
        )
        self.terrain_clearance_metres = float_or_keep(
            payload.get(KEY_TERRAIN_CLEARANCE), self.terrain_clearance_metres
        )
        self.ground_speed_metres_per_second = float_or_keep(
            payload.get(KEY_GROUND_SPEED), self.ground_speed_metres_per_second
        )
        self.airspeed_metres_per_second = float_or_keep(
            payload.get(KEY_AIRSPEED), self.airspeed_metres_per_second
        )
        self.heading_degrees = float_or_keep(payload.get(KEY_HEADING), self.heading_degrees)
        self.battery_voltage = float_or_keep(
            payload.get(KEY_BATTERY_VOLTAGE), self.battery_voltage
        )
        self.battery_percent = float_or_keep(
            payload.get(KEY_BATTERY_PERCENT), self.battery_percent
        )
        self.satellite_count = int_or_keep(
            payload.get(KEY_SATELLITE_COUNT), self.satellite_count
        )

        if KEY_BATTERY_SOURCE in payload:
            self.battery_source = str(payload[KEY_BATTERY_SOURCE])
        if KEY_MODE in payload:
            self.mode = str(payload[KEY_MODE])
        if KEY_GPS_FIX in payload:
            self.gps_fix = str(payload[KEY_GPS_FIX])
        if KEY_ARMED in payload:
            self.armed = bool(payload[KEY_ARMED])

        self.last_telemetry_monotonic = time.monotonic()
        self.record_position()

    def record_position(self) -> None:
        """Remember where it has been, so the map can draw a track."""
        if self.latitude is None or self.longitude is None:
            return

        position = (self.latitude, self.longitude)
        if self.track and self.track[-1] == position:
            return

        # The first fix is where it took off from, which is what HOME means on
        # the ribbon until the autopilot says otherwise.
        if self.home_latitude is None:
            self.home_latitude = self.latitude
            self.home_longitude = self.longitude

        self.track.append(position)
        if len(self.track) > MAP_TRACK_LENGTH:
            del self.track[0]

    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def position(self) -> tuple[float, float] | None:
        if not self.has_position():
            return None
        return (self.latitude, self.longitude)

    def home_position(self) -> tuple[float, float] | None:
        if self.home_latitude is None or self.home_longitude is None:
            return None
        return (self.home_latitude, self.home_longitude)

    def telemetry_age_milliseconds(self) -> float | None:
        if self.last_telemetry_monotonic is None:
            return None
        return (time.monotonic() - self.last_telemetry_monotonic) * MILLISECONDS_PER_SECOND


def float_or_keep(value, current):
    """A missing or unreadable field leaves the last good value alone."""
    if value is None:
        return current
    try:
        return float(value)
    except (TypeError, ValueError):
        return current


def int_or_keep(value, current):
    if value is None:
        return current
    try:
        return int(value)
    except (TypeError, ValueError):
        return current
