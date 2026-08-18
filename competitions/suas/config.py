"""Loads the SUAS config/ folder and exposes it as constants.

Only what this competition needs lives here; the broker connection, logging and
the shared detection review browser's settings come from the app-root config.py.

Two things about the split. config/mission.toml holds numbers a rule fixes — the
altitude envelope, the mission clock, the boundary polygons, the waypoint
threshold — quoted from the SUAS 2026 Team Handbook, and they are not tuning.
config/mqtt.toml holds the whole bus contract, including topics no widget reads
yet; this module exports only the constants something imports today, so what is
in use stays obvious.
"""

from pathlib import Path

from config import load_config_folder

CONFIG_DIR = Path(__file__).with_name("config")

config: dict = load_config_folder(CONFIG_DIR)

# The competition folder anchors every file path in config/, so the interface
# behaves the same whatever directory it was started from.
COMPETITION_DIR = Path(__file__).parent


def competition_path(relative_path: str) -> Path:
    return COMPETITION_DIR / relative_path


# Mission — the rules

mission = config["mission"]

RUNWAY_PROFILE: str = mission["runway_profile"]

MISSION_SECONDS: int = mission["mission_seconds"]
MISSION_CAUTION_SECONDS: int = mission["caution_seconds"]
MISSION_CRITICAL_SECONDS: int = mission["critical_seconds"]

ALTITUDE_FLOOR_FEET: float = mission["altitude_floor_feet"]
ALTITUDE_CEILING_FEET: float = mission["altitude_ceiling_feet"]
WAYPOINT_THRESHOLD_LIMIT_FEET: float = mission["waypoint_threshold_limit_feet"]

BOUNDARY_CAUTION_FEET: float = mission["boundary_caution_feet"]
BOUNDARY_CRITICAL_FEET: float = mission["boundary_critical_feet"]

MAXIMUM_LAPS: int = mission["maximum_laps"]

# Scoring — 3.2.3

scoring = config["scoring"]

ENDURANCE_MAXIMUM_POINTS: float = scoring["endurance_maximum_points"]
ENDURANCE_LAP_DIVISOR: float = scoring["endurance_lap_divisor"]

# Boundaries

boundaries = config["boundaries"]


def coordinate_pairs(entries) -> list:
    return [(float(latitude), float(longitude)) for latitude, longitude in entries]


FLIGHT_BOUNDARY: list = coordinate_pairs(boundaries["flight"])

SEARCH_BOUNDARIES: dict = {
    "runway_1": coordinate_pairs(boundaries["search_runway_1"]),
    "runway_2": coordinate_pairs(boundaries["search_runway_2"]),
}

RUNWAY_OUTLINES: dict = {
    "runway_1": coordinate_pairs(boundaries["runway_1"]),
    "runway_2": coordinate_pairs(boundaries["runway_2"]),
}

WAYPOINT_FILES: dict = {
    "runway_1": config["waypoints"]["runway_1_file"],
    "runway_2": config["waypoints"]["runway_2_file"],
}

# MQTT — only the topics something subscribes to today

subscribe_topics = config["mqtt"]["topics"]["subscribe"]

TOPIC_TELEMETRY: str = subscribe_topics["telemetry"]
TOPIC_WAYPOINT: str = subscribe_topics["waypoint"]
TOPIC_MISSION_STATE: str = subscribe_topics["mission_state"]
TOPIC_HEALTH_LINK: str = subscribe_topics["health_link"]
TOPIC_COMMAND_ACK: str = subscribe_topics["command_ack"]
TOPIC_RELEASE_COUNTDOWN: str = subscribe_topics["release_countdown"]
TOPIC_CAMERA_STATE: str = subscribe_topics["camera_state"]
TOPIC_VIDEO_FRAME: str = subscribe_topics["video_frame"]

publish_topics = config["mqtt"]["topics"]["publish"]

TOPIC_FLIGHT_COMMAND: str = publish_topics["flight_command"]
TOPIC_CAMERA_COMMAND: str = publish_topics["camera_command"]

# Payload keys — telemetry

telemetry_keys = config["payloads"]["telemetry"]

KEY_LATITUDE: str = telemetry_keys["latitude"]
KEY_LONGITUDE: str = telemetry_keys["longitude"]
KEY_ALTITUDE_AGL: str = telemetry_keys["altitude_agl_metres"]
KEY_ALTITUDE_AMSL: str = telemetry_keys["altitude_amsl_metres"]
KEY_TERRAIN_CLEARANCE: str = telemetry_keys["terrain_clearance_metres"]
KEY_GROUND_SPEED: str = telemetry_keys["ground_speed_metres_per_second"]
KEY_HEADING: str = telemetry_keys["heading_degrees"]
KEY_MODE: str = telemetry_keys["mode"]
KEY_ARMED: str = telemetry_keys["armed"]
KEY_BATTERY_VOLTAGE: str = telemetry_keys["battery_voltage"]
KEY_BATTERY_PERCENT: str = telemetry_keys["battery_percent"]
KEY_GPS_FIX: str = telemetry_keys["gps_fix"]
KEY_SATELLITE_COUNT: str = telemetry_keys["satellite_count"]

# Payload keys — waypoints, mission, links

waypoint_keys = config["payloads"]["waypoint"]

KEY_WAYPOINT_INDEX: str = waypoint_keys["current_index"]
KEY_WAYPOINT_TOTAL: str = waypoint_keys["total_count"]
KEY_WAYPOINT_DISTANCE: str = waypoint_keys["distance_metres"]
KEY_ACCEPTANCE_RADIUS: str = waypoint_keys["acceptance_radius_metres"]

mission_keys = config["payloads"]["mission"]

KEY_MISSION_STATE: str = mission_keys["state"]
KEY_LAPS_COMPLETED: str = mission_keys["laps_completed"]
KEY_LAP_WAYPOINT_INDEX: str = mission_keys["lap_waypoint_index"]
KEY_LAP_VALID: str = mission_keys["lap_valid"]
KEY_LAP_INVALID_REASON: str = mission_keys["lap_invalid_reason"]
KEY_LAPS_LOCKED: str = mission_keys["laps_locked"]

KEY_MISSION_LINK_LOSS: str = config["payloads"]["link"]["mission_link_loss_percent"]

# Payload keys — the release countdown, and the presses that drive a delivery

countdown_keys = config["payloads"]["release_countdown"]

KEY_COUNTDOWN_MODE: str = countdown_keys["mode"]
KEY_COUNTDOWN_TRACK_ID: str = countdown_keys["track_id"]
KEY_COUNTDOWN_TARGET_CLASS: str = countdown_keys["target_class"]
KEY_COUNTDOWN_METRES: str = countdown_keys["metres_to_release"]
KEY_COUNTDOWN_DISTANCE: str = countdown_keys["distance_to_target_metres"]
KEY_COUNTDOWN_THROW: str = countdown_keys["throw_metres"]
KEY_COUNTDOWN_HEADING_ERROR: str = countdown_keys["heading_error_degrees"]
KEY_COUNTDOWN_ALLOWED: str = countdown_keys["release_allowed"]
KEY_COUNTDOWN_REASON: str = countdown_keys["reason"]

flight_command_keys = config["payloads"]["flight_command"]

KEY_FLIGHT_COMMAND_ID: str = flight_command_keys["command_id"]
KEY_FLIGHT_ACTION: str = flight_command_keys["action"]

flight_actions = config["codes"]["flight_command"]

ACTION_GOTO_TARGET: str = flight_actions["goto_target"]
ACTION_RELEASE: str = flight_actions["release"]
ACTION_FINISH: str = flight_actions["finish"]

# Payload keys — the camera, and the picture it sends

camera_state_keys = config["payloads"]["camera_state"]

KEY_CAMERA_RECORDING: str = camera_state_keys["recording"]
KEY_CAMERA_REASON: str = camera_state_keys["reason"]

camera_command_keys = config["payloads"]["camera_command"]

KEY_CAMERA_COMMAND_ID: str = camera_command_keys["command_id"]
KEY_CAMERA_ACTION: str = camera_command_keys["action"]

camera_actions = config["codes"]["camera_command"]

ACTION_START_RECORDING: str = camera_actions["start_recording"]
ACTION_STOP_RECORDING: str = camera_actions["stop_recording"]

video_frame_keys = config["payloads"]["video_frame"]

KEY_VIDEO_IMAGE: str = video_frame_keys["image_base64"]
KEY_VIDEO_FRAME_TIMESTAMP: str = video_frame_keys["frame_timestamp"]

acknowledgement_keys = config["payloads"]["command_ack"]

KEY_ACK_COMMAND_ID: str = acknowledgement_keys["command_id"]
KEY_ACK_STATUS: str = acknowledgement_keys["status"]
KEY_ACK_REASON: str = acknowledgement_keys["reason"]

acknowledgement_codes = config["codes"]["command_ack"]

ACK_ACCEPTED: str = acknowledgement_codes["accepted"]
ACK_DONE: str = acknowledgement_codes["done"]
ACK_REJECTED: str = acknowledgement_codes["rejected"]

# The aircraft's two release modes, as they arrive on the countdown. The winged
# one is never commanded, so the panel offers no presses for it.
MODE_BALLISTIC: str = config["codes"]["release_mode"]["ballistic"]

# Targets — the detection review

TOPIC_TARGET_DETECTED: str = subscribe_topics["target_detected"]
TOPIC_TARGET_CONFIRM: str = config["mqtt"]["topics"]["publish"]["target_confirm"]

target_keys = config["payloads"]["target"]

KEY_TARGET_TRACK_ID: str = target_keys["track_id"]
KEY_TARGET_CLASS: str = target_keys["target_class"]
KEY_TARGET_CONFIDENCE: str = target_keys["confidence"]
KEY_TARGET_LATITUDE: str = target_keys["latitude"]
KEY_TARGET_LONGITUDE: str = target_keys["longitude"]
KEY_TARGET_IMAGE: str = target_keys["image_base64"]
KEY_TARGET_FRAME_TIMESTAMP: str = target_keys["frame_timestamp"]

confirm_keys = config["payloads"]["target_confirm"]

KEY_CONFIRM_TRACK_ID: str = confirm_keys["track_id"]
KEY_CONFIRM_DECISION: str = confirm_keys["decision"]
KEY_CONFIRM_OPERATOR: str = confirm_keys["operator_id"]

DECISION_APPROVE: str = config["codes"]["target_decision"]["approve"]
DECISION_DENY: str = config["codes"]["target_decision"]["deny"]

detection_interface = config["interface"]["detection"]

DETECTION_HINT_TEXT: str = detection_interface["hint_text"]
DETECTION_MISSING_LOCATION_TEXT: str = detection_interface["missing_location_text"]
DETECTION_UNKNOWN_CLASS_TEXT: str = detection_interface["unknown_class_text"]
DETECTION_UNKNOWN_CLASS_NAME: str = detection_interface["unknown_class_name"]
DETECTION_OPERATOR_ID: str = detection_interface["operator_id"]

# The mode a lap has to be flown in to count (3.7).
MODE_AUTONOMOUS: str = config["codes"]["mode"]["autonomous"]

# Safety

safety = config["safety"]

SAFETY_MAVLINK_ENDPOINT: str = safety["mavlink_endpoint"]
SAFETY_MAVLINK_BAUD_RATE: int = safety["mavlink_baud_rate"]
SAFETY_HOLD_TO_CONFIRM_MS: int = safety["hold_to_confirm_ms"]
SAFETY_HOLD_PROGRESS_INTERVAL_MS: int = safety["hold_progress_interval_ms"]
SAFETY_COMMAND_ACK_TIMEOUT_MS: int = safety["command_ack_timeout_ms"]
SAFETY_HEARTBEAT_TIMEOUT_MS: int = safety["heartbeat_timeout_ms"]

SAFETY_COMMAND_RETURN_TO_LAUNCH: str = safety["commands"]["return_to_launch"]
SAFETY_COMMAND_LAND: str = safety["commands"]["land"]
SAFETY_COMMAND_TERMINATE: str = safety["commands"]["terminate"]

SAFETY_MODE_RETURN_TO_LAUNCH: str = safety["modes"]["return_to_launch"]
SAFETY_MODE_LAND: str = safety["modes"]["land"]

# Interface texts and sizes

interface = config["interface"]

MISSING_VALUE_TEXT: str = interface["missing_value_text"]
REFRESH_INTERVAL_MS: int = interface["refresh_interval_ms"]

RIBBON_MODE_CAPTION: str = interface["ribbon_mode_caption"]
RIBBON_MODE_FORMAT: str = interface["ribbon_mode_format"]
RIBBON_ARMED_CAPTION: str = interface["ribbon_armed_caption"]
RIBBON_ARMED_TEXT: str = interface["ribbon_armed_text"]
RIBBON_DISARMED_TEXT: str = interface["ribbon_disarmed_text"]
RIBBON_GROUND_SPEED_CAPTION: str = interface["ribbon_ground_speed_caption"]
RIBBON_GROUND_SPEED_FORMAT: str = interface["ribbon_ground_speed_format"]
RIBBON_ALTITUDE_CAPTION: str = interface["ribbon_altitude_caption"]
RIBBON_ALTITUDE_FORMAT: str = interface["ribbon_altitude_format"]
RIBBON_BATTERY_CAPTION: str = interface["ribbon_battery_caption"]
RIBBON_BATTERY_FORMAT: str = interface["ribbon_battery_format"]
RIBBON_GPS_CAPTION: str = interface["ribbon_gps_caption"]
RIBBON_GPS_FORMAT: str = interface["ribbon_gps_format"]
RIBBON_WAYPOINT_RADIUS_CAPTION: str = interface["ribbon_waypoint_radius_caption"]
RIBBON_WAYPOINT_RADIUS_FORMAT: str = interface["ribbon_waypoint_radius_format"]
RIBBON_BOUNDARY_CAPTION: str = interface["ribbon_boundary_caption"]
RIBBON_BOUNDARY_FORMAT: str = interface["ribbon_boundary_format"]
RIBBON_BOUNDARY_OUTSIDE_TEXT: str = interface["ribbon_boundary_outside_text"]
RIBBON_HOME_CAPTION: str = interface["ribbon_home_caption"]
RIBBON_HOME_FORMAT: str = interface["ribbon_home_format"]
RIBBON_SAFETY_LINK_CAPTION: str = interface["ribbon_safety_link_caption"]
RIBBON_MISSION_LINK_CAPTION: str = interface["ribbon_mission_link_caption"]
RIBBON_LINK_UP_TEXT: str = interface["ribbon_link_up_text"]
RIBBON_LINK_DOWN_TEXT: str = interface["ribbon_link_down_text"]

CLOCK_CAPTION: str = interface["clock_caption"]
CLOCK_FORMAT: str = interface["clock_format"]
CLOCK_PHASE_CAPTION: str = interface["clock_phase_caption"]
CLOCK_PHASE_FORMAT: str = interface["clock_phase_format"]
CLOCK_PHASE_UNKNOWN_TEXT: str = interface["clock_phase_unknown_text"]
CLOCK_OVERRUN_FORMAT: str = interface["clock_overrun_format"]
CLOCK_START_TEXT: str = interface["clock_start_text"]
CLOCK_RUNNING_TEXT: str = interface["clock_running_text"]

LAP_PANEL_TITLE: str = interface["lap_panel_title"]
LAP_MARKS_CAPTION: str = interface["lap_marks_caption"]
LAP_PROGRESS_CAPTION: str = interface["lap_progress_caption"]
LAP_PROGRESS_FORMAT: str = interface["lap_progress_format"]
LAP_PROGRESS_WAITING_TEXT: str = interface["lap_progress_waiting_text"]
LAP_AUTO_HELD_TEXT: str = interface["lap_auto_held_text"]
LAP_AUTO_LOST_TEXT: str = interface["lap_auto_lost_text"]
LAP_POINTS_FORMAT: str = interface["lap_points_format"]
LAP_NEXT_LAP_FORMAT: str = interface["lap_next_lap_format"]
LAP_LOCKED_TEXT: str = interface["lap_locked_text"]
LAP_DONE_MARK: str = interface["lap_done_mark"]
LAP_CURRENT_MARK: str = interface["lap_current_mark"]
LAP_TODO_MARK: str = interface["lap_todo_mark"]
LAP_INVALID_FORMAT: str = interface["lap_invalid_format"]

SAFETY_PANEL_TITLE: str = interface["safety_panel_title"]
SAFETY_RETURN_TEXT: str = interface["safety_return_text"]
SAFETY_TERMINATE_TEXT: str = interface["safety_terminate_text"]
SAFETY_HOLD_HINT_TEXT: str = interface["safety_hold_hint_text"]
SAFETY_SENT_TEXT: str = interface["safety_sent_text"]
SAFETY_ACKNOWLEDGED_TEXT: str = interface["safety_acknowledged_text"]
SAFETY_TIMEOUT_TEXT: str = interface["safety_timeout_text"]
SAFETY_LINK_DOWN_TEXT: str = interface["safety_link_down_text"]

DROP_PANEL_ENABLED: bool = interface["drop_panel_enabled"]
DROP_PANEL_TITLE: str = interface["drop_panel_title"]
DROP_COUNTDOWN_CAPTION: str = interface["drop_countdown_caption"]
DROP_COUNTDOWN_FORMAT: str = interface["drop_countdown_format"]
DROP_COUNTDOWN_READY_TEXT: str = interface["drop_countdown_ready_text"]
DROP_TARGET_CAPTION: str = interface["drop_target_caption"]
DROP_TARGET_FORMAT: str = interface["drop_target_format"]
DROP_GEOMETRY_CAPTION: str = interface["drop_geometry_caption"]
DROP_GEOMETRY_FORMAT: str = interface["drop_geometry_format"]
DROP_WAITING_TEXT: str = interface["drop_waiting_text"]
DROP_GOTO_TEXT: str = interface["drop_goto_text"]
DROP_RELEASE_TEXT: str = interface["drop_release_text"]
DROP_RETURN_TEXT: str = interface["drop_return_text"]
DROP_LAND_TEXT: str = interface["drop_land_text"]
DROP_HOLD_HINT_TEXT: str = interface["drop_hold_hint_text"]
DROP_COMMAND_SENT_TEXT: str = interface["drop_command_sent_text"]
DROP_COMMAND_ACCEPTED_TEXT: str = interface["drop_command_accepted_text"]
DROP_COMMAND_REJECTED_FORMAT: str = interface["drop_command_rejected_format"]
DROP_COMMAND_TIMEOUT_TEXT: str = interface["drop_command_timeout_text"]
DROP_WATCH_ONLY_TEXT: str = interface["drop_watch_only_text"]

CAMERA_PANEL_ENABLED: bool = interface["camera_panel_enabled"]
CAMERA_STALE_SECONDS: float = interface["camera_stale_seconds"]
CAMERA_PANEL_TITLE: str = interface["camera_panel_title"]
CAMERA_NO_SIGNAL_TEXT: str = interface["camera_no_signal_text"]
CAMERA_WAITING_TEXT: str = interface["camera_waiting_text"]
CAMERA_RECORD_TEXT: str = interface["camera_record_text"]
CAMERA_STOP_TEXT: str = interface["camera_stop_text"]
CAMERA_HOLD_HINT_TEXT: str = interface["camera_hold_hint_text"]
CAMERA_RECORDING_TEXT: str = interface["camera_recording_text"]
CAMERA_IDLE_TEXT: str = interface["camera_idle_text"]
CAMERA_UNKNOWN_TEXT: str = interface["camera_unknown_text"]
CAMERA_COMMAND_SENT_TEXT: str = interface["camera_command_sent_text"]
CAMERA_COMMAND_REJECTED_FORMAT: str = interface["camera_command_rejected_format"]

MAP_TILES_MISSING_TEXT: str = interface["map_tiles_missing_text"]
MAP_RECENTRE_TEXT: str = interface["map_recentre_text"]
MAP_FOLLOW_ON_TEXT: str = interface["map_follow_on_text"]
MAP_FOLLOW_OFF_TEXT: str = interface["map_follow_off_text"]

layout = interface["layout"]

MAP_STRETCH: int = layout["map_stretch"]
SIDE_COLUMN_STRETCH: int = layout["side_column_stretch"]
DETECTION_COLUMN_STRETCH: int = layout["detection_column_stretch"]
SIDE_COLUMN_WIDTH: int = layout["side_column_width"]
RIBBON_MINIMUM_HEIGHT: int = layout["ribbon_minimum_height"]
RIBBON_COLUMNS: int = layout["ribbon_columns"]
CLOCK_MINIMUM_HEIGHT: int = layout["clock_minimum_height"]
VIDEO_MINIMUM_HEIGHT: int = layout["video_minimum_height"]

# Map

map_settings = config["map"]

MAP_TILE_FILE: str = map_settings["tile_file"]
MAP_DEFAULT_LATITUDE: float = map_settings["default_latitude"]
MAP_DEFAULT_LONGITUDE: float = map_settings["default_longitude"]
MAP_DEFAULT_ZOOM: float = map_settings["default_zoom"]
MAP_MINIMUM_ZOOM: float = map_settings["minimum_zoom"]
MAP_MAXIMUM_ZOOM: float = map_settings["maximum_zoom"]
MAP_TILE_SIZE_PIXELS: int = map_settings["tile_size_pixels"]
MAP_TILE_CACHE_LIMIT: int = map_settings["tile_cache_limit"]
MAP_FIT_MARGIN_FRACTION: float = map_settings["fit_margin_fraction"]
MAP_ZOOM_STEP: float = map_settings["zoom_step"]
MAP_TRACK_LENGTH: int = map_settings["track_length"]

MAP_COLORS: dict = map_settings["colors"]

map_sizes = map_settings["sizes"]

MAP_FLIGHT_BOUNDARY_WIDTH: int = map_sizes["flight_boundary_width"]
MAP_SEARCH_BOUNDARY_WIDTH: int = map_sizes["search_boundary_width"]
MAP_RUNWAY_WIDTH: int = map_sizes["runway_width"]
MAP_WAYPOINT_RADIUS_WIDTH: int = map_sizes["waypoint_radius_width"]
MAP_WAYPOINT_MARKER_RADIUS: int = map_sizes["waypoint_marker_radius"]
MAP_AIRCRAFT_MARKER_RADIUS: int = map_sizes["aircraft_marker_radius"]
MAP_AIRCRAFT_HEADING_LENGTH: int = map_sizes["aircraft_heading_length"]
MAP_TRACK_WIDTH: int = map_sizes["track_width"]
MAP_LABEL_OFFSET: int = map_sizes["label_offset"]


def active_waypoint_file() -> Path:
    return competition_path(WAYPOINT_FILES[RUNWAY_PROFILE])


def tile_file_path() -> Path:
    return competition_path(MAP_TILE_FILE)
