"""Loads the shared config/ folder and exposes every setting as a constant.

The config/ folder is the single source of truth — change values there, not
here. config/general.toml holds the day-to-day switches; the other files hold
stable UI constants. All files deep-merge into one tree, so a key lives in
exactly one file.

Only settings every competition needs live here. A competition keeps its own
config/ folder and its own loader next to it (competitions/<name>/config.py),
which reuses load_config_folder below.
Requires Python 3.11+ (tomllib); on older versions install tomli.
"""

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

CONFIG_DIR = Path(__file__).with_name("config")


def merge_config_file(target: dict, source: dict, file_name: str):
    """Merge one config file into the combined tree, rejecting duplicates."""
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_config_file(target[key], value, file_name)
        elif key in target:
            raise ValueError(
                f"Config key '{key}' in {file_name} is already defined by another file."
            )
        else:
            target[key] = value


def load_config_folder(config_directory: Path) -> dict:
    """Deep-merge every .toml file in one config folder into a single tree."""
    loaded_config: dict = {}
    for config_file_path in sorted(config_directory.glob("*.toml")):
        with open(config_file_path, "rb") as config_file:
            merge_config_file(loaded_config, tomllib.load(config_file), config_file_path.name)
    return loaded_config


config: dict = load_config_folder(CONFIG_DIR)

# Design tokens
#
# Handed over whole rather than unpacked here: theme/tokens.py turns them into
# named constants and mixes the shades that derive from them.

THEME_TOKENS: dict = config["theme"]

# Logging

LOG_LEVEL: str = config["logging"]["level"]
LOG_FORMAT: str = config["logging"]["format"]
LOG_DATE_FORMAT: str = config["logging"]["date_format"]
LOG_COLORS: dict = config["logging"]["colors"]

# MQTT broker

MQTT_BROKER_ADDRESS: str = config["mqtt"]["broker_address"]
MQTT_PORT: int = config["mqtt"]["port"]
MQTT_KEEPALIVE_SECONDS: int = config["mqtt"]["keepalive_seconds"]

# Competitions


@dataclass(frozen=True)
class Competition:
    key: str
    label: str
    uses_drones: bool
    uses_vtols: bool


COMPETITIONS: list[Competition] = [
    Competition(
        key=competition_key,
        label=entry["label"],
        uses_drones=entry["uses_drones"],
        uses_vtols=entry["uses_vtols"],
    )
    for competition_key, entry in config["competitions"].items()
]

# Selection screen

selection = config["selection"]

SELECTION_TITLE: str = selection["title"]
SELECTION_SUBTITLE: str = selection["subtitle"]
SELECTION_VEHICLES_TITLE: str = selection["vehicles_title"]
SELECTION_DRONE_COUNT_TEXT: str = selection["drone_count_text"]
SELECTION_VTOL_COUNT_TEXT: str = selection["vtol_count_text"]
SELECTION_CONTINUE_TEXT: str = selection["continue_text"]

# Vehicle counts

DRONE_COUNT_DEFAULT: int = config["counts"]["drone_default"]
DRONE_COUNT_MIN: int = config["counts"]["drone_min"]
DRONE_COUNT_MAX: int = config["counts"]["drone_max"]
VTOL_COUNT_DEFAULT: int = config["counts"]["vtol_default"]
VTOL_COUNT_MIN: int = config["counts"]["vtol_min"]
VTOL_COUNT_MAX: int = config["counts"]["vtol_max"]

# UI constants

WINDOW_TITLE: str = config["ui"]["window_title"]
TERMINAL_TIME_FORMAT: str = config["ui"]["terminal_time_format"]
TERMINAL_MAX_LINES: int = config["ui"]["terminal_max_lines"]
POSITION_DECIMALS: int = config["ui"]["position_decimals"]
CAMERA_UNAVAILABLE_TEXT: str = config["ui"]["camera_unavailable_text"]
CAMERA_REMOVE_TEXT: str = config["ui"]["camera_remove_text"]
CAMERA_ADD_TEXT: str = config["ui"]["camera_add_text"]
BROKER_CONNECTED_TEXT: str = config["ui"]["broker_connected_text"]
BROKER_DISCONNECTED_TEXT: str = config["ui"]["broker_disconnected_text"]

# Connection monitoring

CONNECTION_REFRESH_INTERVAL_MS: int = config["connection_monitor"]["refresh_interval_ms"]
CONNECTION_STALE_AFTER_MS: int = config["connection_monitor"]["stale_after_ms"]
CONNECTION_NO_DATA_TEXT: str = config["connection_monitor"]["no_data_text"]

# Detection review browser (shared by the competitions that use it)

detection_review = config["detection_review"]

DETECTION_REVIEW_TITLE: str = detection_review["title"]
DETECTION_REVIEW_NO_FRAMES_TEXT: str = detection_review["no_frames_text"]
DETECTION_REVIEW_MAX_FRAMES: int = detection_review["max_frames"]
DETECTION_REVIEW_APPROVE_TEXT: str = detection_review["approve_text"]
DETECTION_REVIEW_REJECT_TEXT: str = detection_review["reject_text"]
DETECTION_REVIEW_COUNTER_FORMAT: str = detection_review["counter_format"]
DETECTION_REVIEW_MISSING_VALUE_TEXT: str = detection_review["missing_value_text"]
DETECTION_REVIEW_IMAGE_MIN_HEIGHT: int = detection_review["image_min_height"]
DETECTION_REVIEW_DETAILS_FORMAT: str = detection_review["details_format"]
DETECTION_REVIEW_CONFIDENCE_DECIMALS: int = detection_review["confidence_decimals"]
DETECTION_REVIEW_COORDINATE_DECIMALS: int = detection_review["coordinate_decimals"]
DETECTION_REVIEW_ALTITUDE_DECIMALS: int = detection_review["altitude_decimals"]
DETECTION_REVIEW_PENDING_FORMAT: str = detection_review["pending_format"]

detection_keys = detection_review["payload_keys"]

DETECTION_KEY_ID: str = detection_keys["detection_id"]
DETECTION_KEY_LABEL: str = detection_keys["label"]
DETECTION_KEY_CONFIDENCE: str = detection_keys["confidence"]
DETECTION_KEY_LATITUDE: str = detection_keys["latitude"]
DETECTION_KEY_LONGITUDE: str = detection_keys["longitude"]
DETECTION_KEY_ALTITUDE: str = detection_keys["altitude"]
DETECTION_KEY_TIMESTAMP: str = detection_keys["timestamp"]
DETECTION_KEY_IMAGE: str = detection_keys["image"]
