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
TOPIC_CALIBRATE_COLOR: str = publish_topics["calibrate_color"]
TOPIC_WHITE_BALANCE: str = publish_topics["white_balance"]
TOPIC_QR_LOCATION: str = publish_topics["qr_location"]
TOPIC_FORMATION: str = publish_topics["formation"]
TOPIC_MISSION1: str = publish_topics["mission1"]
TOPIC_MISSION2: str = publish_topics["mission2"]
TOPIC_MISSION_PLAN: str = publish_topics["mission_plan"]
TOPIC_MISSION_PLAN_RUN: str = publish_topics["mission_plan_run"]
TOPIC_EMERGENCY: str = publish_topics["emergency"]
TOPIC_FREE: str = publish_topics["free"]
TOPIC_LINK_TEST: str = publish_topics["link_test"]
TOPIC_MESH_CHANNEL: str = publish_topics["mesh_channel"]
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
TOPIC_LINK_TEST_RESULT: str = subscribe_topics["link_test"]
TOPIC_MISSION2_STATUS: str = subscribe_topics["mission2_status"]

# Clock report source codes

clock_sources = config["mqtt"]["clock_sources"]

CLOCK_SOURCE_PPS: str = clock_sources["pps"]
CLOCK_SOURCE_PEER: str = clock_sources["peer"]
CLOCK_SOURCE_SWARM: str = clock_sources["swarm"]

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

# Color calibration window

color_calibration = config["color_calibration"]

COLOR_WINDOW_TITLE: str = color_calibration["window_title"]
COLOR_CARD_TITLE: str = color_calibration["card_title"]
COLOR_HINT: str = color_calibration["hint"]
COLOR_WAITING_TEXT: str = color_calibration["waiting_text"]
COLOR_NO_SELECTION_TEXT: str = color_calibration["no_selection_text"]
COLOR_NO_COLOR_TEXT: str = color_calibration["no_color_text"]
COLOR_NAMES: list = color_calibration["colors"]
COLOR_WINDOW_WIDTH: int = color_calibration["window_width"]
COLOR_WINDOW_HEIGHT: int = color_calibration["window_height"]
COLOR_TRIM_PERCENT: int = color_calibration["trim_percent"]
COLOR_HUE_MARGIN: int = color_calibration["hue_margin"]
COLOR_SATURATION_MARGIN: int = color_calibration["saturation_margin"]
COLOR_VALUE_FLOOR_RATIO: float = color_calibration["value_floor_ratio"]
COLOR_MINIMUM_SATURATION: int = color_calibration["minimum_saturation"]
COLOR_MAX_SAMPLE_PIXELS: int = color_calibration["max_sample_pixels"]
COLOR_BUTTON_TEXT: dict = color_calibration["buttons"]

# Developer tab — the drone nodes as they run on the companion Pis

developer = config["developer"]

DEVELOPER_HOST_PATTERN: str = developer["host_pattern"]
DEVELOPER_SSH_PROGRAM: str = developer["ssh_program"]
DEVELOPER_SSH_OPTIONS: list = developer["ssh_options"]
DEVELOPER_REPOSITORY_PATH: str = developer["repository_path"]
DEVELOPER_UNIT_NAME: str = developer["unit_name"]
DEVELOPER_STOP_WAIT_MS: int = developer["stop_wait_ms"]
DEVELOPER_MONITOR_COLUMNS: int = developer["monitor_columns"]
DEVELOPER_MONITOR_MIN_HEIGHT: int = developer["monitor_min_height"]
DEVELOPER_MONITOR_SHARE: int = developer["monitor_share"]
DEVELOPER_OUTPUT_SHARE: int = developer["output_share"]
DEVELOPER_OUTPUT_MIN_HEIGHT: int = developer["output_min_height"]
DEVELOPER_LOCAL: dict = developer["local"]
DEVELOPER_PUSH: dict = developer["push"]
DEVELOPER_LOGS: dict = developer["logs"]

DEVELOPER_COMMAND_START: str = developer["commands"]["start"]
DEVELOPER_COMMAND_STOP: str = developer["commands"]["stop"]
DEVELOPER_COMMAND_MONITOR: str = developer["commands"]["monitor"]
DEVELOPER_COMMAND_PULL: str = developer["commands"]["pull"]
DEVELOPER_COMMAND_RESTORE: str = developer["commands"]["restore"]
DEVELOPER_COMMAND_PPS_CHECK: str = developer["commands"]["pps_check"]
DEVELOPER_COMMAND_CHECKOUT: str = developer["commands"]["checkout"]
DEVELOPER_COMMAND_REBOOT: str = developer["commands"]["reboot"]
DEVELOPER_SUDO_PREFIX: str = developer["commands"]["sudo_prefix"]
DEVELOPER_SUDO_PREFIX_WITH_PASSWORD: str = developer["commands"]["sudo_prefix_with_password"]

# Set in config/secrets.toml, which is not in git. Empty when nobody set one,
# and then the reboot runs under plain sudo -n.
DEVELOPER_SUDO_PASSWORD: str = developer.get("sudo_password", "")

DEVELOPER_LOG_STATES: dict = developer["log_states"]
DEVELOPER_TEXT: dict = developer["text"]

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
QR_NUMBER_MIN: int = config["input_ranges"]["qr_number_min"]
QR_NUMBER_MAX: int = config["input_ranges"]["qr_number_max"]
SPINBOX_DECIMALS: int = config["input_ranges"]["spinbox_decimals"]

# The link test window

LINK_TEST_DURATION_S: float = config["link_test"]["duration_s"]
LINK_TEST_BUTTON_TEXT: str = config["link_test"]["button_text"]
LINK_TEST_WINDOW_TITLE: str = config["link_test"]["window_title"]
LINK_TEST_RUNNING_TEXT: str = config["link_test"]["running_text"]
LINK_TEST_FILE_TEXT: str = config["link_test"]["file_text"]
LINK_TEST_AIR_ONLY_TEXT: str = config["link_test"]["air_only_text"]
LINK_TEST_AIR_ONLY_RUNNING_TEXT: str = config["link_test"]["air_only_running_text"]
LINK_TEST_RETEST_TEXT: str = config["link_test"]["retest_text"]
LINK_TEST_SWARM_ONLY_TEXT: str = config["link_test"]["swarm_only_text"]
LINK_TEST_SWARM_ONLY_HINT: str = config["link_test"]["swarm_only_hint"]
LINK_TEST_CHANNEL_MIN: int = config["link_test"]["channel_min"]
LINK_TEST_CHANNEL_MAX: int = config["link_test"]["channel_max"]
LINK_TEST_CHANNEL_CONFIG_TEXT: str = config["link_test"]["channel_config_text"]
LINK_TEST_CHANNEL_ITEM_TEXT: str = config["link_test"]["channel_item_text"]
LINK_TEST_TESTED_ON_TEXT: str = config["link_test"]["tested_on_text"]
LINK_TEST_CHANGE_CHANNEL_TEXT: str = config["link_test"]["change_channel_text"]
LINK_TEST_CHANGE_CHANNEL_TITLE: str = config["link_test"]["change_channel_title"]
LINK_TEST_CHANGE_CHANNEL_QUESTION: str = config["link_test"]["change_channel_question"]
LINK_TEST_COLLECTING_TEXT: str = config["link_test"]["collecting_text"]
LINK_TEST_PROGRESS_TICK_MS: int = config["link_test"]["progress_tick_ms"]
LINK_TEST_PAIRS_TAB_TITLE: str = config["link_test"]["pairs_tab_title"]
LINK_TEST_GCS_NAME: str = config["link_test"]["gcs_name"]
LINK_TEST_COLUMNS: list = config["link_test"]["columns"]
LINK_TEST_CHANNEL_LINE: str = config["link_test"]["channel_line"]
LINK_TEST_CHANNEL_MISSING_LINE: str = config["link_test"]["channel_missing_line"]
LINK_TEST_CHANNEL_SEPARATOR: str = config["link_test"]["channel_separator"]
LINK_TEST_AIR_TAB_TITLE: str = config["link_test"]["air_tab_title"]
LINK_TEST_AIR_SUMMARY_LINE: str = config["link_test"]["air_summary_line"]
LINK_TEST_AIR_SUMMARY_MISSING_LINE: str = config["link_test"]["air_summary_missing_line"]
LINK_TEST_AIR_SWARM_ONLY_TEXT: str = config["link_test"]["air_swarm_only_text"]
LINK_TEST_SNIFF_COLUMNS: list = config["link_test"]["sniff_columns"]
LINK_TEST_SNIFF_KIND_NAMES: dict = config["link_test"]["sniff_kind_names"]
LINK_TEST_NETWORKS_TAB_TITLE: str = config["link_test"]["networks_tab_title"]
LINK_TEST_AIR_HINT: str = config["link_test"]["air_hint"]
LINK_TEST_AIR_COLUMNS: list = config["link_test"]["air_columns"]
LINK_TEST_AIR_OVERLAP_MARK: str = config["link_test"]["air_overlap_mark"]
LINK_TEST_AIR_HIDDEN_NETWORK_TEXT: str = config["link_test"]["air_hidden_network_text"]

# Link health, judged on the drones' fixed-rate position stream

LINK_TELEMETRY_RATE_HZ: float = config["link_health"]["telemetry_rate_hz"]
LINK_HEALTH_WINDOW_S: float = config["link_health"]["window_s"]
LINK_LOSS_WARN_PERCENT: float = config["link_health"]["loss_warn_percent"]
LINK_HEALTH_TEXT: str = config["link_health"]["text"]

# Calibration tab

calibration = config["calibration"]

CALIBRATION_TAB_TITLE: str = calibration["tab_title"]
CALIBRATION_DRONES_TITLE: str = calibration["drones_title"]
CALIBRATION_DRONES_HINT: str = calibration["drones_hint"]
CALIBRATION_NO_DRONES_TEXT: str = calibration["no_drones_text"]
CALIBRATION_STEPS_TITLE: str = calibration["steps_title"]
CALIBRATION_RESULTS_TITLE: str = calibration["results_title"]
CALIBRATION_RESULTS_COLUMNS: list = calibration["results_columns"]
CALIBRATION_RESULTS_EMPTY_TEXT: str = calibration["results_empty_text"]
CALIBRATION_RESULTS_MAX_ROWS: int = calibration["results_max_rows"]
CALIBRATION_RESULTS_MIN_HEIGHT: int = calibration["results_min_height"]
CALIBRATION_UNKNOWN_DRONE_TEXT: str = calibration["unknown_drone_text"]
CALIBRATION_MEASURED_LABELS: dict = calibration["measured_labels"]
CALIBRATION_STATUS_STATES: dict = calibration["status_states"]
CALIBRATION_STEPS: list = calibration["step"]

# UI constants

SWARM_GRID_COLUMNS: int = config["ui"]["swarm_grid_columns"]
SWARM_CAMERA_ROWS: int = config["ui"]["swarm_camera_rows"]
SWARM_CAMERA_MIN_HEIGHT: int = config["ui"]["swarm_camera_min_height"]
SWARM_CAMERA_HEADER_HEIGHT: int = config["ui"]["swarm_camera_header_height"]
SWARM_TELEMETRY_VISIBLE_DRONES: int = config["ui"]["swarm_telemetry_visible_drones"]
STATE_UNKNOWN_TEXT: str = config["ui"]["state_unknown_text"]
CLOCK_WAITING_TEXT: str = config["ui"]["clock_waiting_text"]
CLOCK_SYNCED_TEXT: str = config["ui"]["clock_synced_text"]
CLOCK_PEER_TEXT: str = config["ui"]["clock_peer_text"]
CLOCK_SWARM_TEXT: str = config["ui"]["clock_swarm_text"]
CLOCK_NO_SYNC_TEXT: str = config["ui"]["clock_no_sync_text"]
MISSION_WITHOUT_PPS_TEXT: str = config["ui"]["mission_without_pps_text"]
MISSION_TARGET_AUTO_TEXT: str = config["ui"]["mission_target_auto_text"]
MISSION2_START_TEXT: str = config["ui"]["mission2_start_text"]
MISSION2_STOP_TEXT: str = config["ui"]["mission2_stop_text"]
MISSION2_WAITING_TEXT: str = config["ui"]["mission2_waiting_text"]
MISSION2_ALL_IN_TEXT: str = config["ui"]["mission2_all_in_text"]
MISSION2_STILL_IN_TEXT: str = config["ui"]["mission2_still_in_text"]
QR_PANEL_TITLE: str = config["ui"]["qr_panel_title"]
QR_NO_DATA_TEXT: str = config["ui"]["qr_no_data_text"]
QR_TAB_LABEL: str = config["ui"]["qr_tab_label"]
QR_FREE_SCAN_TAB_LABEL: str = config["ui"]["qr_free_scan_tab_label"]
QR_INDENT_SPACES: int = config["ui"]["qr_indent_spaces"]
MISSION_ACTIVE_STATES: frozenset = frozenset(config["ui"]["mission_active_states"])
