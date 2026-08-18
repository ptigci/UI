"""Loads the Sürü İHA config/ folder and exposes its settings as constants.

Only what this competition needs lives here; the broker connection, logging and
the widget constants every competition shares come from the app-root config.py.
"""

from pathlib import Path

from config import load_config_folder

CONFIG_DIR = Path(__file__).with_name("config")

config: dict = load_config_folder(CONFIG_DIR)

# MQTT topics — published commands

publish_topics = config["mqtt"]["topics"]["publish"]

TOPIC_DRONE_NUMBER: str = publish_topics["drone_number"]
TOPIC_ARM: str = publish_topics["arm"]
TOPIC_DISARM: str = publish_topics["disarm"]
TOPIC_FORCE_ARM: str = publish_topics["force_arm"]
TOPIC_FORCE_DISARM: str = publish_topics["force_disarm"]
TOPIC_TAKEOFF: str = publish_topics["takeoff"]
TOPIC_LAND: str = publish_topics["land"]
TOPIC_MOVE: str = publish_topics["move"]
TOPIC_CALIBRATE_TAU: str = publish_topics["calibrate_tau"]
TOPIC_CALIBRATE_LATENCY: str = publish_topics["calibrate_latency"]
TOPIC_FORMATION: str = publish_topics["formation"]
TOPIC_MISSION1: str = publish_topics["mission1"]
TOPIC_MISSION2: str = publish_topics["mission2"]
TOPIC_MISSION_PLAN: str = publish_topics["mission_plan"]
TOPIC_MISSION_PLAN_RUN: str = publish_topics["mission_plan_run"]
TOPIC_EMERGENCY: str = publish_topics["emergency"]
TOPIC_FREE: str = publish_topics["free"]
TOPIC_OBJECT_DETECTION_APPROVE: str = publish_topics["object_detection_approve"]
TOPIC_OBJECT_DETECTION_CANCEL: str = publish_topics["object_detection_cancel"]
TOPIC_SIMULATION: str = publish_topics["simulation"]

# MQTT topics — subscribed data

subscribe_topics = config["mqtt"]["topics"]["subscribe"]

TOPIC_TELEMETRY_PATTERN: str = subscribe_topics["telemetry"]
TOPIC_CAMERA_PATTERN: str = subscribe_topics["camera"]
TOPIC_STATE_PATTERN: str = subscribe_topics["state"]
TOPIC_HEALTH_PATTERN: str = subscribe_topics["health"]
TOPIC_CLOCK_PATTERN: str = subscribe_topics["clock"]
TOPIC_PLAN_STATUS_PATTERN: str = subscribe_topics["plan_status"]
TOPIC_QR_CONTENT: str = subscribe_topics["qr_content"]
TOPIC_COLOR_ZONE: str = subscribe_topics["color_zone"]
TOPIC_OBJECT_DETECTION_FRAMES: str = subscribe_topics["object_detection"]
TOPIC_ESP_LOG: str = subscribe_topics["esp_log"]

# Formation payload codes

formation_codes = config["mqtt"]["formation_codes"]

FORMATION_CODE_LINE: str = formation_codes["line"]
FORMATION_CODE_V: str = formation_codes["v"]
FORMATION_CODE_INVERSE_V: str = formation_codes["inverse_v"]

# Mission plan — the operator-built plan and the wire format the drones read

mission_plan = config["mission_plan"]

PLAN_MAX_STEPS: int = mission_plan["max_steps"]
PLAN_DEFAULT_TAKEOFF_ALTITUDE: float = mission_plan["default_takeoff_altitude"]
PLAN_DEFAULT_ALTITUDE_CHANGE: float = mission_plan["default_altitude_change"]
PLAN_DEFAULT_FORMATION_DISTANCE: float = mission_plan["default_formation_distance"]
PLAN_DEFAULT_FORMATION_ANGLE: float = mission_plan["default_formation_angle"]

PLAN_KEY_PLAN: str = mission_plan["payload"]["plan_key"]
PLAN_KEY_STEPS: str = mission_plan["payload"]["steps_key"]
PLAN_STATUS_KEY_PLAN: str = mission_plan["status_payload"]["plan_key"]
PLAN_STATUS_KEY_INDEX: str = mission_plan["status_payload"]["index_key"]
PLAN_STATUS_KEY_STATUS: str = mission_plan["status_payload"]["status_key"]

PLAN_STEP_ARM: str = mission_plan["step_codes"]["arm"]
PLAN_STEP_DISARM: str = mission_plan["step_codes"]["disarm"]
PLAN_STEP_TAKEOFF: str = mission_plan["step_codes"]["takeoff"]
PLAN_STEP_LAND: str = mission_plan["step_codes"]["land"]
PLAN_STEP_GOTO: str = mission_plan["step_codes"]["goto"]
PLAN_STEP_FORMATION: str = mission_plan["step_codes"]["formation"]

PLAN_STATUS_STARTED: str = mission_plan["status_codes"]["started"]
PLAN_STATUS_DONE: str = mission_plan["status_codes"]["done"]
PLAN_STATUS_FAILED: str = mission_plan["status_codes"]["failed"]
PLAN_STATUS_MISSING: str = mission_plan["status_codes"]["missing"]

PLAN_STEP_LABELS: dict = mission_plan["step_labels"]
PLAN_STEP_TEXT: dict = mission_plan["step_text"]
PLAN_TEXT: dict = mission_plan["text"]

# Formation picker entries, in the order they appear in the plan window.
PLAN_FORMATION_LABELS: dict = {
    FORMATION_CODE_LINE: mission_plan["formation_labels"]["line"],
    FORMATION_CODE_V: mission_plan["formation_labels"]["v"],
    FORMATION_CODE_INVERSE_V: mission_plan["formation_labels"]["inverse_v"],
}

# Validation limits

MIN_TAKEOFF_ALTITUDE: float = config["validation"]["min_takeoff_altitude"]
MIN_FORMATION_DISTANCE: float = config["validation"]["min_formation_distance"]
MIN_FORMATION_ANGLE: float = config["validation"]["min_formation_angle"]

# Input ranges

MOVE_AXIS_MIN: float = config["input_ranges"]["move_axis_min"]
MOVE_AXIS_MAX: float = config["input_ranges"]["move_axis_max"]
TAKEOFF_ALTITUDE_MAX: float = config["input_ranges"]["takeoff_altitude_max"]
ALTITUDE_CHANGE_MIN: float = config["input_ranges"]["altitude_change_min"]
ALTITUDE_CHANGE_MAX: float = config["input_ranges"]["altitude_change_max"]
FORMATION_DISTANCE_MAX: float = config["input_ranges"]["formation_distance_max"]
FORMATION_ANGLE_MIN: float = config["input_ranges"]["formation_angle_min"]
FORMATION_ANGLE_MAX: float = config["input_ranges"]["formation_angle_max"]
ROTATION_MIN: float = config["input_ranges"]["rotation_min"]
ROTATION_MAX: float = config["input_ranges"]["rotation_max"]
SPINBOX_DECIMALS: int = config["input_ranges"]["spinbox_decimals"]

# UI constants

LATENCY_PROPS_TITLE: str = config["ui"]["latency_props_title"]
LATENCY_PROPS_QUESTION: str = config["ui"]["latency_props_question"]
SWARM_GRID_COLUMNS: int = config["ui"]["swarm_grid_columns"]
SWARM_CAMERA_ROWS: int = config["ui"]["swarm_camera_rows"]
SWARM_CAMERA_MIN_HEIGHT: int = config["ui"]["swarm_camera_min_height"]
SWARM_CAMERA_HEADER_HEIGHT: int = config["ui"]["swarm_camera_header_height"]
SWARM_TELEMETRY_VISIBLE_DRONES: int = config["ui"]["swarm_telemetry_visible_drones"]
STATE_UNKNOWN_TEXT: str = config["ui"]["state_unknown_text"]
CLOCK_WAITING_TEXT: str = config["ui"]["clock_waiting_text"]
CLOCK_SYNCED_TEXT: str = config["ui"]["clock_synced_text"]
CLOCK_NO_SYNC_TEXT: str = config["ui"]["clock_no_sync_text"]
MISSION_TARGET_AUTO_TEXT: str = config["ui"]["mission_target_auto_text"]
MISSION2_START_TEXT: str = config["ui"]["mission2_start_text"]
MISSION2_STOP_TEXT: str = config["ui"]["mission2_stop_text"]
QR_PANEL_TITLE: str = config["ui"]["qr_panel_title"]
QR_NO_DATA_TEXT: str = config["ui"]["qr_no_data_text"]
MISSION_ACTIVE_STATES: frozenset = frozenset(config["ui"]["mission_active_states"])
