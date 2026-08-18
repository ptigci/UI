"""Loads the Uluslararası İHA config/ folder and exposes it as constants.

Only what this competition needs lives here; the broker connection, logging,
the shared widget constants and the detection review browser's settings come
from the app-root config.py.
"""

from pathlib import Path

from config import load_config_folder

CONFIG_DIR = Path(__file__).with_name("config")

config: dict = load_config_folder(CONFIG_DIR)

# MQTT topics — subscribed data

subscribe_topics = config["mqtt"]["topics"]["subscribe"]

TOPIC_PASIFIK_TELEMETRY: str = subscribe_topics["pasifik_telemetry"]
TOPIC_PASIFIK_STATUS: str = subscribe_topics["pasifik_status"]
TOPIC_SCAN_PROGRESS: str = subscribe_topics["scan_progress"]
TOPIC_DETECTION_FRAME: str = subscribe_topics["detection_frame"]
TOPIC_AGENT_TELEMETRY_PATTERN: str = subscribe_topics["agent_telemetry"]
TOPIC_AGENT_STATUS_PATTERN: str = subscribe_topics["agent_status"]
TOPIC_TARGET_CONFIRMED: str = subscribe_topics["target_confirmed"]
TOPIC_TARGET_ASSIGNMENT: str = subscribe_topics["target_assignment"]
TOPIC_SYSTEM_HEALTH: str = subscribe_topics["system_health"]
TOPIC_COMMAND_ACK: str = subscribe_topics["command_ack"]

# MQTT topics — published commands

publish_topics = config["mqtt"]["topics"]["publish"]

TOPIC_DETECTION_APPROVE: str = publish_topics["detection_approve"]
TOPIC_DETECTION_REJECT: str = publish_topics["detection_reject"]
TOPIC_TARGET_VETO: str = publish_topics["target_veto"]
TOPIC_TARGET_REQUEUE: str = publish_topics["target_requeue"]
TOPIC_SYSTEM_COMMAND: str = publish_topics["system_command"]

# Payload keys — telemetry

telemetry_keys = config["payloads"]["telemetry"]

KEY_LATITUDE: str = telemetry_keys["latitude"]
KEY_LONGITUDE: str = telemetry_keys["longitude"]
KEY_ALTITUDE_AGL: str = telemetry_keys["altitude_agl"]
KEY_GROUND_SPEED: str = telemetry_keys["ground_speed"]
KEY_AIRSPEED: str = telemetry_keys["airspeed"]
KEY_HEADING: str = telemetry_keys["heading"]
KEY_BATTERY_PERCENT: str = telemetry_keys["battery_percent"]
KEY_BATTERY_VOLTAGE: str = telemetry_keys["battery_voltage"]
KEY_GPS_FIX: str = telemetry_keys["gps_fix"]
KEY_RTK_STATUS: str = telemetry_keys["rtk_status"]

# Payload keys — status

status_keys = config["payloads"]["status"]

KEY_STATE: str = status_keys["state"]
KEY_MODE: str = status_keys["mode"]
KEY_ARMED: str = status_keys["armed"]
KEY_ASSIGNED_TARGET: str = status_keys["assigned_target"]
KEY_PAYLOAD_STATE: str = status_keys["payload_state"]

# Payload keys — scan progress

scan_keys = config["payloads"]["scan"]

KEY_SCAN_PERCENT: str = scan_keys["percent"]
KEY_SCAN_LEGS_DONE: str = scan_keys["legs_done"]
KEY_SCAN_LEGS_TOTAL: str = scan_keys["legs_total"]
KEY_SCAN_SECONDS_REMAINING: str = scan_keys["seconds_remaining"]
KEY_SCAN_POLYGON: str = scan_keys["polygon"]
KEY_SCAN_LEGS: str = scan_keys["legs"]

# Payload keys — targets

target_keys = config["payloads"]["target"]

KEY_TARGET_ID: str = target_keys["target_id"]
KEY_TARGET_LABEL: str = target_keys["label"]
KEY_TARGET_LATITUDE: str = target_keys["latitude"]
KEY_TARGET_LONGITUDE: str = target_keys["longitude"]
KEY_TARGET_CONFIDENCE: str = target_keys["confidence"]
KEY_TARGET_PRIORITY: str = target_keys["priority"]
KEY_TARGET_STATE: str = target_keys["state"]
KEY_TARGET_AGENT: str = target_keys["agent_id"]

# Payload keys — link health

health_keys = config["payloads"]["health"]

KEY_HEALTH_LINKS: str = health_keys["links"]
KEY_LINK_NAME: str = health_keys["link_name"]
KEY_LINK_LATENCY_MS: str = health_keys["latency_ms"]
KEY_LINK_LOSS_PERCENT: str = health_keys["loss_percent"]
KEY_LINK_LAST_SEEN_MS: str = health_keys["last_seen_ms"]
KEY_LINK_SIGNAL: str = health_keys["signal_strength"]
KEY_HEALTH_TRACKER: str = health_keys["tracker"]
KEY_HEALTH_RECORDING: str = health_keys["recording"]
KEY_TRACKER_LOCKED: str = health_keys["tracker_locked"]
KEY_TRACKER_ERROR_DEGREES: str = health_keys["tracker_error_degrees"]

# Payload keys — commands and verdicts

command_keys = config["payloads"]["command"]

KEY_COMMAND: str = command_keys["command"]
KEY_COMMAND_VEHICLE: str = command_keys["vehicle"]
KEY_COMMAND_TARGET: str = command_keys["target_id"]
KEY_VERDICT: str = command_keys["verdict"]

COMMAND_DISPATCH: str = config["codes"]["command"]["dispatch"]
COMMAND_HOLD: str = config["codes"]["command"]["hold"]
COMMAND_ABORT: str = config["codes"]["command"]["abort"]
COMMAND_RESUME: str = config["codes"]["command"]["resume"]
COMMAND_START_RECORDING: str = config["codes"]["command"]["start_recording"]
COMMAND_STOP_RECORDING: str = config["codes"]["command"]["stop_recording"]

VERDICT_APPROVED: str = config["codes"]["verdict"]["approved"]
VERDICT_REJECTED: str = config["codes"]["verdict"]["rejected"]

target_state_codes = config["codes"]["target_state"]

TARGET_STATE_CANDIDATE: str = target_state_codes["candidate"]
TARGET_STATE_CONFIRMED: str = target_state_codes["confirmed"]
TARGET_STATE_ASSIGNED: str = target_state_codes["assigned"]
TARGET_STATE_DELIVERING: str = target_state_codes["delivering"]
TARGET_STATE_DELIVERED: str = target_state_codes["delivered"]
TARGET_STATE_FAILED: str = target_state_codes["failed"]
TARGET_STATE_VETOED: str = target_state_codes["vetoed"]

# Mission

mission = config["mission"]

MISSION_UNKNOWN_STATE_TEXT: str = mission["unknown_state_text"]
COMMAND_ACK_TIMEOUT_MS: int = mission["command_ack_timeout_ms"]
VEHICLE_STALE_AFTER_MS: int = mission["vehicle_stale_after_ms"]
MISSION_ACTIVE_STATES: frozenset = frozenset(mission["active_states"])

# Interface texts and sizes

interface = config["interface"]

MISSING_VALUE_TEXT: str = interface["missing_value_text"]
MISSION_STATE_PREFIX: str = interface["mission_state_prefix"]
SCAN_CAPTION: str = interface["scan_caption"]
SCAN_PROGRESS_FORMAT: str = interface["scan_progress_format"]
SCAN_WAITING_TEXT: str = interface["scan_waiting_text"]
ELAPSED_CAPTION: str = interface["elapsed_caption"]
ELAPSED_FORMAT: str = interface["elapsed_format"]
ACK_CAPTION: str = interface["ack_caption"]
ACK_NONE_TEXT: str = interface["ack_none_text"]
DISPATCH_TEXT: str = interface["dispatch_text"]
HOLD_TEXT: str = interface["hold_text"]
RESUME_TEXT: str = interface["resume_text"]
ABORT_TEXT: str = interface["abort_text"]
RECORDING_ON_TEXT: str = interface["recording_on_text"]
RECORDING_OFF_TEXT: str = interface["recording_off_text"]
RECORD_TEXT: str = interface["record_text"]
RECORD_STOP_TEXT: str = interface["record_stop_text"]
ACK_PENDING_FORMAT: str = interface["ack_pending_format"]
ACK_COMPLETE_FORMAT: str = interface["ack_complete_format"]
ACK_TIMEOUT_FORMAT: str = interface["ack_timeout_format"]
DISPATCH_CONFIRM_TITLE: str = interface["dispatch_confirm_title"]
DISPATCH_CONFIRM_QUESTION: str = interface["dispatch_confirm_question"]
HOLD_CONFIRM_TITLE: str = interface["hold_confirm_title"]
HOLD_CONFIRM_QUESTION: str = interface["hold_confirm_question"]
ABORT_CONFIRM_TITLE: str = interface["abort_confirm_title"]
ABORT_CONFIRM_QUESTION: str = interface["abort_confirm_question"]

PASIFIK_TITLE: str = interface["pasifik_title"]
AGENT_TITLE_FORMAT: str = interface["agent_title_format"]
CARD_STATE_FORMAT: str = interface["card_state_format"]
CARD_MODE_FORMAT: str = interface["card_mode_format"]
CARD_ARMED_TEXT: str = interface["card_armed_text"]
CARD_DISARMED_TEXT: str = interface["card_disarmed_text"]
CARD_BATTERY_FORMAT: str = interface["card_battery_format"]
CARD_POSITION_FORMAT: str = interface["card_position_format"]
CARD_ALTITUDE_FORMAT: str = interface["card_altitude_format"]
CARD_SPEED_FORMAT: str = interface["card_speed_format"]
CARD_AIRSPEED_FORMAT: str = interface["card_airspeed_format"]
CARD_GPS_FORMAT: str = interface["card_gps_format"]
CARD_TARGET_FORMAT: str = interface["card_target_format"]
CARD_PAYLOAD_FORMAT: str = interface["card_payload_format"]
CARD_NO_TARGET_TEXT: str = interface["card_no_target_text"]
CARD_STALE_FORMAT: str = interface["card_stale_format"]
BATTERY_WARNING_PERCENT: float = interface["battery_warning_percent"]
BATTERY_CRITICAL_PERCENT: float = interface["battery_critical_percent"]

TARGET_PANEL_TITLE: str = interface["target_panel_title"]
TARGET_CONFIRMED_TITLE: str = interface["target_confirmed_title"]
TARGET_CANDIDATE_TITLE: str = interface["target_candidate_title"]
TARGET_ROW_FORMAT: str = interface["target_row_format"]
TARGET_CONFIDENCE_FORMAT: str = interface["target_confidence_format"]
TARGET_POSITION_FORMAT: str = interface["target_position_format"]
TARGET_SORT_LABELS: dict = interface["target_sort_labels"]
TARGET_STATE_FORMAT: str = interface["target_state_format"]
TARGET_AGENT_FORMAT: str = interface["target_agent_format"]
TARGET_NO_AGENT_TEXT: str = interface["target_no_agent_text"]
TARGET_EMPTY_TEXT: str = interface["target_empty_text"]
VETO_TEXT: str = interface["veto_text"]
REQUEUE_TEXT: str = interface["requeue_text"]
VETO_CONFIRM_TITLE: str = interface["veto_confirm_title"]
VETO_CONFIRM_QUESTION: str = interface["veto_confirm_question"]

LOG_PANEL_TITLE: str = interface["log_panel_title"]

LINK_PANEL_TITLE: str = interface["link_panel_title"]
LINK_ROW_FORMAT: str = interface["link_row_format"]
LINK_LATENCY_FORMAT: str = interface["link_latency_format"]
LINK_LOSS_FORMAT: str = interface["link_loss_format"]
LINK_AGE_FORMAT: str = interface["link_age_format"]
LINK_NO_DATA_TEXT: str = interface["link_no_data_text"]
LINK_EMPTY_TEXT: str = interface["link_empty_text"]
TRACKER_LOCKED_FORMAT: str = interface["tracker_locked_format"]
TRACKER_LOST_TEXT: str = interface["tracker_lost_text"]
TRACKER_UNKNOWN_TEXT: str = interface["tracker_unknown_text"]
LINK_LATENCY_WARNING_MS: float = interface["link_latency_warning_ms"]
LINK_LOSS_WARNING_PERCENT: float = interface["link_loss_warning_percent"]

DETECTION_HINT_TEXT: str = interface["detection_hint_text"]
DETECTION_APPROVED_FORMAT: str = interface["detection_approved_format"]
DETECTION_REJECTED_FORMAT: str = interface["detection_rejected_format"]
DETECTION_MISSING_LOCATION_TEXT: str = interface["detection_missing_location_text"]

REFRESH_INTERVAL_MS: int = interface["refresh_interval_ms"]
SIDE_COLUMN_WIDTH: int = interface["side_column_width"]
DETECTION_COLUMN_WIDTH: int = interface["detection_column_width"]
TARGET_LIST_MIN_HEIGHT: int = interface["target_list_min_height"]

layout = interface["layout"]

VEHICLE_LIST_STRETCH: int = layout["vehicle_list_stretch"]
LINK_HEALTH_STRETCH: int = layout["link_health_stretch"]
MAP_STRETCH: int = layout["map_stretch"]
LOG_STRETCH: int = layout["log_stretch"]
TARGET_PANEL_STRETCH: int = layout["target_panel_stretch"]
DETECTION_PANEL_STRETCH: int = layout["detection_panel_stretch"]
LEFT_COLUMN_STRETCH: int = layout["left_column_stretch"]
CENTRE_COLUMN_STRETCH: int = layout["centre_column_stretch"]
RIGHT_COLUMN_STRETCH: int = layout["right_column_stretch"]

# Map

MAP_DEFAULT_LATITUDE: float = config["map"]["default_latitude"]
MAP_DEFAULT_LONGITUDE: float = config["map"]["default_longitude"]
MAP_DEFAULT_SPAN_METRES: float = config["map"]["default_span_metres"]
MAP_TRACK_LENGTH: int = config["map"]["track_length"]

MAP_COLORS: dict = config["map"]["colors"]
MAP_TARGET_COLORS: dict = config["map"]["target_colors"]

map_sizes = config["map"]["sizes"]

MAP_VEHICLE_MARKER_RADIUS: int = map_sizes["vehicle_marker_radius"]
MAP_VEHICLE_HEADING_LENGTH: int = map_sizes["vehicle_heading_length"]
MAP_TARGET_MARKER_RADIUS: int = map_sizes["target_marker_radius"]
MAP_SELECTED_TARGET_RING: int = map_sizes["selected_target_ring"]
MAP_TRACK_WIDTH: int = map_sizes["track_width"]
MAP_POLYGON_WIDTH: int = map_sizes["polygon_width"]
MAP_LEG_WIDTH: int = map_sizes["leg_width"]
MAP_ASSIGNMENT_WIDTH: int = map_sizes["assignment_width"]
MAP_LABEL_OFFSET: int = map_sizes["label_offset"]
MAP_FIT_MARGIN: float = map_sizes["fit_margin"]
MAP_ZOOM_STEP: float = map_sizes["zoom_step"]
MAP_ZOOM_MIN: float = map_sizes["zoom_min"]
MAP_ZOOM_MAX: float = map_sizes["zoom_max"]
MAP_GRID_SPACING_METRES: float = map_sizes["grid_spacing_metres"]
MAP_SCALE_BAR_WIDTH_PIXELS: int = map_sizes["scale_bar_width_pixels"]
