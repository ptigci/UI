"""Reads the lap the judges hand over at check-in.

Section 3.2.2 gives each team the waypoint sequence for both flight lines at
Check-In, before Mission Time starts. We save each as a QGC WPL file — the format
Mission Planner writes — and this turns one into the coordinates the map draws.

Only the navigation waypoints are kept. A lap file also carries takeoff, landing
and speed-change commands, and drawing those as places on the map would put
markers where the aircraft never goes.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

WPL_HEADER_PREFIX = "QGC WPL"
WPL_FIELD_COUNT = 12
COMMAND_FIELD_INDEX = 3
LATITUDE_FIELD_INDEX = 8
LONGITUDE_FIELD_INDEX = 9

# MAV_CMD values that mean "fly to this place".
NAVIGATION_COMMANDS = frozenset(
    {
        16,  # NAV_WAYPOINT
        17,  # NAV_LOITER_UNLIM
        18,  # NAV_LOITER_TURNS
        19,  # NAV_LOITER_TIME
        82,  # NAV_SPLINE_WAYPOINT
    }
)


def read_waypoint_file(waypoint_file: Path) -> list:
    """The lap as a list of coordinates, or an empty list with a reason logged."""
    if not waypoint_file.exists():
        logger.warning(
            f"Waypoint file not found: {waypoint_file}. The lap is handed over at "
            f"Check-In - save it there, before Mission Time."
        )
        return []

    try:
        lines = waypoint_file.read_text(encoding="utf-8").splitlines()
    except OSError as read_error:
        logger.error(f"Waypoint file could not be read: {read_error}")
        return []

    waypoints = []
    for line in lines:
        coordinate = waypoint_from_line(line)
        if coordinate is not None:
            waypoints.append(coordinate)

    logger.info(f"Loaded {len(waypoints)} waypoints from {waypoint_file.name}")
    return waypoints


def waypoint_from_line(line: str):
    """One tab-separated WPL row, if it is a navigation waypoint with a position."""
    stripped = line.strip()
    if not stripped or stripped.startswith(WPL_HEADER_PREFIX):
        return None

    fields = stripped.split("\t")
    if len(fields) < WPL_FIELD_COUNT:
        return None

    try:
        command = int(float(fields[COMMAND_FIELD_INDEX]))
        latitude = float(fields[LATITUDE_FIELD_INDEX])
        longitude = float(fields[LONGITUDE_FIELD_INDEX])
    except ValueError:
        logger.warning(f"Skipping an unreadable waypoint row: {stripped}")
        return None

    if command not in NAVIGATION_COMMANDS:
        return None
    # A home row and an unset waypoint both come through as zeros.
    if latitude == 0.0 and longitude == 0.0:
        return None
    return (latitude, longitude)
