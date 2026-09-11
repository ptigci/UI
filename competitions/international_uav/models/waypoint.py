"""One item of the mission the Pasifik is flying, as the map draws it.

The aircraft reports every mission item that has a coordinate, in flying
order, with the sequence number the autopilot knows it by. That number is what
joins a dot on the map to the "waypoint 4 / 12" on the card.
"""

from dataclasses import dataclass

from competitions.international_uav.config import (
    KEY_WAYPOINT_LATITUDE,
    KEY_WAYPOINT_LONGITUDE,
    KEY_WAYPOINT_SEQUENCE,
)


@dataclass(frozen=True)
class Waypoint:
    sequence: int
    latitude: float
    longitude: float


def waypoint_from_payload(entry) -> Waypoint | None:
    """One waypoint out of the scan progress message, or None if it is malformed."""
    if not isinstance(entry, dict):
        return None
    try:
        return Waypoint(
            int(entry[KEY_WAYPOINT_SEQUENCE]),
            float(entry[KEY_WAYPOINT_LATITUDE]),
            float(entry[KEY_WAYPOINT_LONGITUDE]),
        )
    except (KeyError, TypeError, ValueError):
        return None
