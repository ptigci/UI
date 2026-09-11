"""Reads a Mission Planner export into the items the Pasifik uploads.

The file is the QGC WPL 110 format Mission Planner saves: one header line,
then one whitespace-separated line per mission item —

    seq  current  frame  command  p1  p2  p3  p4  lat  lon  alt  autocontinue

Blank lines are skipped. Anything else is an error that names its line, and
nothing is sent: a mission with one bad item in it is not a mission.
"""

from pathlib import Path

from competitions.international_uav.config import (
    KEY_MISSION_ALTITUDE,
    KEY_MISSION_AUTOCONTINUE,
    KEY_MISSION_COMMAND,
    KEY_MISSION_FRAME,
    KEY_MISSION_LATITUDE,
    KEY_MISSION_LONGITUDE,
    KEY_MISSION_PARAM1,
    KEY_MISSION_PARAM2,
    KEY_MISSION_PARAM3,
    KEY_MISSION_PARAM4,
    KEY_MISSION_SEQUENCE,
    MISSION_FILE_TEXT,
)

# The format's own definition, not a tuning: the header every Mission Planner
# export starts with, and the twelve fields of an item line in their order.
# The `current` flag in the second field is Mission Planner's own bookkeeping
# and is not uploaded.
HEADER_PREFIX = "QGC WPL"
FIELD_COUNT = 12
SEQUENCE_FIELD = 0
FRAME_FIELD = 2
COMMAND_FIELD = 3
PARAM1_FIELD = 4
PARAM2_FIELD = 5
PARAM3_FIELD = 6
PARAM4_FIELD = 7
LATITUDE_FIELD = 8
LONGITUDE_FIELD = 9
ALTITUDE_FIELD = 10
AUTOCONTINUE_FIELD = 11
FIRST_ITEM_LINE = 2


class MissionFileError(Exception):
    """A mission file that cannot be sent, and why, in one sentence."""


def read_mission_file(path) -> list[dict]:
    """Every item in the file, keyed the way the upload message carries them."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise MissionFileError(MISSION_FILE_TEXT["unreadable_format"].format(reason=error))

    if not lines or not lines[0].startswith(HEADER_PREFIX):
        raise MissionFileError(
            MISSION_FILE_TEXT["bad_header_format"].format(header=HEADER_PREFIX)
        )

    items = []
    for line_number, line in enumerate(lines[1:], start=FIRST_ITEM_LINE):
        if not line.strip():
            continue
        items.append(mission_item(line, line_number))
    if not items:
        raise MissionFileError(MISSION_FILE_TEXT["empty_text"])
    return items


def mission_item(line: str, line_number: int) -> dict:
    fields = line.split()
    if len(fields) != FIELD_COUNT:
        raise MissionFileError(
            MISSION_FILE_TEXT["bad_column_count_format"].format(
                line_number=line_number, count=len(fields), expected=FIELD_COUNT
            )
        )
    return {
        KEY_MISSION_SEQUENCE: number_field(fields, SEQUENCE_FIELD, line_number, int),
        KEY_MISSION_FRAME: number_field(fields, FRAME_FIELD, line_number, int),
        KEY_MISSION_COMMAND: number_field(fields, COMMAND_FIELD, line_number, int),
        KEY_MISSION_PARAM1: number_field(fields, PARAM1_FIELD, line_number, float),
        KEY_MISSION_PARAM2: number_field(fields, PARAM2_FIELD, line_number, float),
        KEY_MISSION_PARAM3: number_field(fields, PARAM3_FIELD, line_number, float),
        KEY_MISSION_PARAM4: number_field(fields, PARAM4_FIELD, line_number, float),
        KEY_MISSION_LATITUDE: number_field(fields, LATITUDE_FIELD, line_number, float),
        KEY_MISSION_LONGITUDE: number_field(fields, LONGITUDE_FIELD, line_number, float),
        KEY_MISSION_ALTITUDE: number_field(fields, ALTITUDE_FIELD, line_number, float),
        KEY_MISSION_AUTOCONTINUE: number_field(fields, AUTOCONTINUE_FIELD, line_number, int),
    }


def number_field(fields: list, index: int, line_number: int, cast):
    try:
        return cast(fields[index])
    except ValueError:
        raise MissionFileError(
            MISSION_FILE_TEXT["bad_number_format"].format(
                line_number=line_number, value=fields[index]
            )
        )
