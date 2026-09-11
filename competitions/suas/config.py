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
TOPIC_STITCH_STATE: str = subscribe_topics["stitch_state"]
TOPIC_ROUTE_PLAN: str = subscribe_topics["route_plan"]
TOPIC_TARGET_TRACK: str = subscribe_topics["target_track"]
TOPIC_TARGET_BLACKLIST: str = subscribe_topics["target_blacklist"]
TOPIC_PAYLOAD_STATE: str = subscribe_topics["payload_state"]
TOPIC_STATUSTEXT: str = subscribe_topics["statustext"]
TOPIC_COMMAND_RESULT: str = subscribe_topics["command_result"]
TOPIC_CALIBRATION_PROGRESS: str = subscribe_topics["calibration_progress"]

publish_topics = config["mqtt"]["topics"]["publish"]

TOPIC_FLIGHT_COMMAND: str = publish_topics["flight_command"]
TOPIC_CAMERA_COMMAND: str = publish_topics["camera_command"]
TOPIC_STITCH_REQUEST: str = publish_topics["stitch_request"]
TOPIC_MAPPING_EXPORT: str = publish_topics["mapping_export"]
TOPIC_MISSION_COMMAND: str = publish_topics["mission_command"]
TOPIC_AIRCRAFT_COMMAND: str = publish_topics["aircraft_command"]
TOPIC_MISSION_UPLOAD: str = publish_topics["mission_upload"]
TOPIC_CALIBRATION_COMMAND: str = publish_topics["calibration_command"]

# The aircraft's own controls, the mission upload and the calibrations, and
# what the autopilot says back. The mode and calibration tables are keyed by
# name so the FLIGHT and CALIBRATION tabs can be built from the orders in
# interface.toml.

statustext_keys = config["payloads"]["statustext"]

KEY_STATUSTEXT_SEVERITY: str = statustext_keys["severity"]
KEY_STATUSTEXT_TEXT: str = statustext_keys["text"]

command_result_keys = config["payloads"]["command_result"]

KEY_COMMAND_RESULT_ID: str = command_result_keys["command_id"]
KEY_COMMAND_RESULT_COMMAND: str = command_result_keys["command"]
KEY_COMMAND_RESULT_ACCEPTED: str = command_result_keys["accepted"]
KEY_COMMAND_RESULT_DETAIL: str = command_result_keys["detail"]

aircraft_command_keys = config["payloads"]["aircraft_command"]

KEY_AIRCRAFT_COMMAND_ID: str = aircraft_command_keys["command_id"]
KEY_AIRCRAFT_ACTION: str = aircraft_command_keys["action"]
KEY_AIRCRAFT_FLIGHT_MODE: str = aircraft_command_keys["flight_mode"]

mission_upload_keys = config["payloads"]["mission_upload"]

KEY_MISSION_UPLOAD_ID: str = mission_upload_keys["command_id"]
KEY_MISSION_ITEMS: str = mission_upload_keys["items"]

mission_item_keys = config["payloads"]["mission_item"]

KEY_ITEM_SEQUENCE: str = mission_item_keys["sequence"]
KEY_ITEM_FRAME: str = mission_item_keys["frame"]
KEY_ITEM_COMMAND: str = mission_item_keys["command"]
KEY_ITEM_PARAM1: str = mission_item_keys["param1"]
KEY_ITEM_PARAM2: str = mission_item_keys["param2"]
KEY_ITEM_PARAM3: str = mission_item_keys["param3"]
KEY_ITEM_PARAM4: str = mission_item_keys["param4"]
KEY_ITEM_LATITUDE: str = mission_item_keys["latitude"]
KEY_ITEM_LONGITUDE: str = mission_item_keys["longitude"]
KEY_ITEM_ALTITUDE: str = mission_item_keys["altitude_metres"]
KEY_ITEM_AUTOCONTINUE: str = mission_item_keys["autocontinue"]

calibration_command_keys = config["payloads"]["calibration_command"]

KEY_CALIBRATION_COMMAND_ID: str = calibration_command_keys["command_id"]
KEY_CALIBRATION_COMMAND_NAME: str = calibration_command_keys["calibration"]
KEY_CALIBRATION_ACTION: str = calibration_command_keys["action"]

calibration_progress_keys = config["payloads"]["calibration_progress"]

KEY_CALIBRATION_NAME: str = calibration_progress_keys["calibration"]
KEY_CALIBRATION_STATE: str = calibration_progress_keys["state"]
KEY_CALIBRATION_STEP: str = calibration_progress_keys["step"]
KEY_CALIBRATION_PERCENT: str = calibration_progress_keys["percent"]
KEY_CALIBRATION_DETAIL: str = calibration_progress_keys["detail"]

KEY_AIRCRAFT_BUS_TIMESTAMP: str = config["payloads"]["aircraft_bus"]["timestamp"]

aircraft_actions = config["codes"]["aircraft_command"]

ACTION_ARM: str = aircraft_actions["arm"]
ACTION_FORCE_ARM: str = aircraft_actions["force_arm"]
ACTION_FORCE_DISARM: str = aircraft_actions["force_disarm"]
ACTION_START_MISSION: str = aircraft_actions["start_mission"]
ACTION_SET_MODE: str = aircraft_actions["set_mode"]
ACTION_UPLOAD_MISSION: str = aircraft_actions["upload_mission"]

FLIGHT_MODES: dict = config["codes"]["flight_mode"]
CALIBRATIONS: dict = config["codes"]["calibration"]
CALIBRATION_STATES: dict = config["codes"]["calibration_state"]

calibration_action_codes = config["codes"]["calibration_action"]

CALIBRATION_ACTION_START: str = calibration_action_codes["start"]
CALIBRATION_ACTION_NEXT: str = calibration_action_codes["next"]
CALIBRATION_ACTION_CANCEL: str = calibration_action_codes["cancel"]

mission_command_keys = config["payloads"]["mission_command"]

KEY_MISSION_COMMAND_ID: str = mission_command_keys["command_id"]
KEY_MISSION_ACTION: str = mission_command_keys["action"]
ACTION_START_SURVEY: str = config["codes"]["mission_command"]["start_survey"]
ACTION_FINISH_SURVEY: str = config["codes"]["mission_command"]["finish_survey"]

# The DEV tab's link test

TOPIC_LINK_PROBE: str = publish_topics["link_probe"]
TOPIC_LINK_PROBE_REPLY: str = subscribe_topics["link_probe_reply"]

probe_keys = config["payloads"]["link_probe"]

KEY_PROBE_ID: str = probe_keys["probe_id"]
KEY_PROBE_SENT_AT: str = probe_keys["sent_at"]
KEY_PROBE_AIRCRAFT_TIME: str = config["payloads"]["link_probe_reply"]["aircraft_time"]

# Payload keys — telemetry

telemetry_keys = config["payloads"]["telemetry"]

KEY_LATITUDE: str = telemetry_keys["latitude"]
KEY_LONGITUDE: str = telemetry_keys["longitude"]
KEY_ALTITUDE_AGL: str = telemetry_keys["altitude_agl_metres"]
KEY_ALTITUDE_AMSL: str = telemetry_keys["altitude_amsl_metres"]
KEY_TERRAIN_CLEARANCE: str = telemetry_keys["terrain_clearance_metres"]
KEY_GROUND_SPEED: str = telemetry_keys["ground_speed_metres_per_second"]
KEY_AIRSPEED: str = telemetry_keys["airspeed_metres_per_second"]
KEY_HEADING: str = telemetry_keys["heading_degrees"]
KEY_MODE: str = telemetry_keys["mode"]
KEY_ARMED: str = telemetry_keys["armed"]
KEY_BATTERY_VOLTAGE: str = telemetry_keys["battery_voltage"]
KEY_BATTERY_PERCENT: str = telemetry_keys["battery_percent"]
KEY_BATTERY_SOURCE: str = telemetry_keys["battery_source"]
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
KEY_MISSION_DETAIL: str = mission_keys["detail"]
KEY_LAPS_COMPLETED: str = mission_keys["laps_completed"]
KEY_LAP_WAYPOINT_INDEX: str = mission_keys["lap_waypoint_index"]
KEY_LAP_VALID: str = mission_keys["lap_valid"]
KEY_LAP_INVALID_REASON: str = mission_keys["lap_invalid_reason"]
KEY_LAPS_LOCKED: str = mission_keys["laps_locked"]
KEY_FLIGHT_TIME_S: str = mission_keys["flight_time_s"]
KEY_FLIGHT_TIME_LEFT_S: str = mission_keys["flight_time_left_s"]

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
KEY_FLIGHT_STATION: str = flight_command_keys["station"]

flight_actions = config["codes"]["flight_command"]

ACTION_GOTO_TARGET: str = flight_actions["goto_target"]
ACTION_RELEASE: str = flight_actions["release"]
ACTION_HOLD: str = flight_actions["hold"]
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

# Payload keys — the mapping test's folder stitch

stitch_request_keys = config["payloads"]["stitch_request"]

KEY_STITCH_COMMAND_ID: str = stitch_request_keys["command_id"]
KEY_STITCH_FOLDER: str = stitch_request_keys["folder_path"]

stitch_state_keys = config["payloads"]["stitch_state"]

KEY_STITCH_STATE: str = stitch_state_keys["state"]
KEY_STITCH_REASON: str = stitch_state_keys["reason"]
KEY_STITCH_FRAMES_FOUND: str = stitch_state_keys["frames_found"]
KEY_STITCH_FRAMES_SKIPPED: str = stitch_state_keys["frames_skipped"]
KEY_STITCH_FRAMES_PLACED: str = stitch_state_keys["frames_placed"]
KEY_STITCH_FRAMES_TO_PLACE: str = stitch_state_keys["frames_to_place"]
KEY_STITCH_FRAMES_USED: str = stitch_state_keys["frames_used"]
KEY_STITCH_MOSAIC_PATH: str = stitch_state_keys["mosaic_path"]
KEY_STITCH_IMAGE: str = stitch_state_keys["image_base64"]
KEY_STITCH_FRAMES_RECEIVED: str = stitch_state_keys["frames_received"]
KEY_STITCH_ELAPSED: str = stitch_state_keys["elapsed_seconds"]
KEY_STITCH_EXPORT_PATH: str = stitch_state_keys["export_path"]

stitch_states = config["codes"]["stitch_state"]

STITCH_STATE_RUNNING: str = stitch_states["running"]
STITCH_STATE_COMPLETE: str = stitch_states["complete"]
STITCH_STATE_FAILED: str = stitch_states["failed"]
STITCH_STATE_EXPORTED: str = stitch_states["exported"]

# The route the aircraft announces before it flies it

route_keys = config["payloads"]["route"]

KEY_ROUTE_ID: str = route_keys["route_id"]
KEY_ROUTE_TRACK_ID: str = route_keys["track_id"]
KEY_ROUTE_TARGET_CLASS: str = route_keys["target_class"]
KEY_ROUTE_RELEASE_STYLE: str = route_keys["release_style"]
KEY_ROUTE_WAYPOINTS: str = route_keys["waypoints"]
KEY_ROUTE_HOVER_POINT: str = route_keys["hover_point"]
KEY_ROUTE_RELEASE_POINT: str = route_keys["release_point"]
KEY_ROUTE_LENGTH: str = route_keys["length_metres"]
KEY_ROUTE_ESTIMATED_TIME: str = route_keys["estimated_time_seconds"]

route_point_keys = config["payloads"]["route_point"]

KEY_ROUTE_POINT_LATITUDE: str = route_point_keys["latitude"]
KEY_ROUTE_POINT_LONGITUDE: str = route_point_keys["longitude"]

# The tracks and the denied ground, for the map

track_keys = config["payloads"]["track"]

KEY_TRACK_ID: str = track_keys["track_id"]
KEY_TRACK_CLASS: str = track_keys["target_class"]
KEY_TRACK_LATITUDE: str = track_keys["latitude"]
KEY_TRACK_LONGITUDE: str = track_keys["longitude"]
KEY_TRACK_DECISION: str = track_keys["decision_state"]
KEY_TRACK_SCORE: str = track_keys["score"]

KEY_BLACKLIST_ZONES: str = config["payloads"]["blacklist"]["zones"]

zone_keys = config["payloads"]["blacklist_zone"]

KEY_ZONE_ID: str = zone_keys["zone_id"]
KEY_ZONE_CLASS: str = zone_keys["target_class"]
KEY_ZONE_LATITUDE: str = zone_keys["latitude"]
KEY_ZONE_LONGITUDE: str = zone_keys["longitude"]
KEY_ZONE_RADIUS: str = zone_keys["radius_metres"]

decision_states = config["codes"]["target_decision_state"]

TARGET_DECISION_PENDING: str = decision_states["pending"]
TARGET_DECISION_APPROVED: str = decision_states["approved"]
TARGET_DECISION_DENIED: str = decision_states["denied"]
TARGET_DECISION_DELIVERED: str = decision_states["delivered"]

# The payload stations

KEY_PAYLOAD_STATIONS: str = config["payloads"]["payload_state"]["stations"]

station_keys = config["payloads"]["station"]

KEY_STATION_CLASS: str = station_keys["target_class"]
KEY_STATION_STATE: str = station_keys["state"]
KEY_STATION_RELEASED_TRACK: str = station_keys["released_track_id"]

STATION_STATE_SPENT: str = config["codes"]["station_state"]["spent"]

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
KEY_TARGET_AVERAGE_CONFIDENCE: str = target_keys["average_confidence"]
KEY_TARGET_OBSERVATION_COUNT: str = target_keys["observation_count"]
KEY_TARGET_SCORE: str = target_keys["score"]
KEY_TARGET_STATION: str = target_keys["bound_station"]

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
DETECTION_CARD_LABEL_FORMAT: str = config["interface"]["detection_card_label_format"]

# The mode a lap has to be flown in to count (3.7).
MODE_AUTONOMOUS: str = config["codes"]["mode"]["autonomous"]

# Safety

safety = config["safety"]

SAFETY_MAVLINK_ENDPOINT: str = safety["mavlink_endpoint"]
SAFETY_SIMULATION_ENDPOINT: str = safety["simulation_mavlink_endpoint"]
SAFETY_MAVLINK_BAUD_RATE: int = safety["mavlink_baud_rate"]
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
RIBBON_AIRSPEED_CAPTION: str = interface["ribbon_airspeed_caption"]
RIBBON_AIRSPEED_FORMAT: str = interface["ribbon_airspeed_format"]
RIBBON_ALTITUDE_CAPTION: str = interface["ribbon_altitude_caption"]
RIBBON_ALTITUDE_FORMAT: str = interface["ribbon_altitude_format"]
RIBBON_BATTERY_CAPTION: str = interface["ribbon_battery_caption"]
RIBBON_BATTERY_FORMAT: str = interface["ribbon_battery_format"]
RIBBON_BATTERY_SOURCE_FORMAT: str = interface["ribbon_battery_source_format"]
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
DROP_RELEASE_FORMAT: str = interface["drop_release_format"]
DROP_HOLD_FORMAT: str = interface["drop_hold_format"]
DROP_RELEASE_WAITING_TEXT: str = interface["drop_release_waiting_text"]
DROP_RETURN_TEXT: str = interface["drop_return_text"]
DROP_LAND_TEXT: str = interface["drop_land_text"]
DROP_COMMAND_SENT_TEXT: str = interface["drop_command_sent_text"]
DROP_COMMAND_ACCEPTED_TEXT: str = interface["drop_command_accepted_text"]
DROP_COMMAND_REJECTED_FORMAT: str = interface["drop_command_rejected_format"]
DROP_COMMAND_TIMEOUT_TEXT: str = interface["drop_command_timeout_text"]
DROP_WATCH_ONLY_TEXT: str = interface["drop_watch_only_text"]

CAMERA_PANEL_ENABLED: bool = interface["camera_panel_enabled"]
CAMERA_STALE_SECONDS: float = interface["camera_stale_seconds"]
MISSION_LINK_STALE_MS: int = interface["mission_link_stale_ms"]
CAMERA_PANEL_TITLE: str = interface["camera_panel_title"]
CAMERA_NO_SIGNAL_TEXT: str = interface["camera_no_signal_text"]
CAMERA_WAITING_TEXT: str = interface["camera_waiting_text"]
CAMERA_RECORD_TEXT: str = interface["camera_record_text"]
CAMERA_STOP_TEXT: str = interface["camera_stop_text"]
CAMERA_RECORDING_TEXT: str = interface["camera_recording_text"]
CAMERA_IDLE_TEXT: str = interface["camera_idle_text"]
CAMERA_UNKNOWN_TEXT: str = interface["camera_unknown_text"]
CAMERA_COMMAND_SENT_TEXT: str = interface["camera_command_sent_text"]
CAMERA_COMMAND_REJECTED_FORMAT: str = interface["camera_command_rejected_format"]

MAPPING_PANEL_ENABLED: bool = interface["mapping_panel_enabled"]
MAPPING_BENCH_ENABLED: bool = interface["mapping_bench_enabled"]
MAPPING_RESULTS_FOLDER_IS_LOCAL: bool = interface["mapping_results_folder_is_local"]
MAPPING_PANEL_TITLE: str = interface["mapping_panel_title"]
MAPPING_WAITING_TEXT: str = interface["mapping_waiting_text"]
MAPPING_FRAMES_CAPTION: str = interface["mapping_frames_caption"]
MAPPING_FRAMES_FORMAT: str = interface["mapping_frames_format"]
MAPPING_CLOCK_CAPTION: str = interface["mapping_clock_caption"]
MAPPING_CLOCK_FORMAT: str = interface["mapping_clock_format"]
MAPPING_OPEN_FOLDER_TEXT: str = interface["mapping_open_folder_text"]
MAPPING_EXPORT_TEXT: str = interface["mapping_export_text"]
MAPPING_EXPORTED_FORMAT: str = interface["mapping_exported_format"]

MISSION_PANEL_TITLE: str = interface["mission_panel_title"]
MISSION_PHASE_CAPTION: str = interface["mission_phase_caption"]
MISSION_PHASE_UNKNOWN_TEXT: str = interface["mission_phase_unknown_text"]
MISSION_PHASE_TIME_LEFT_FORMAT: str = interface["mission_phase_time_left_format"]
MISSION_START_SURVEY_TEXT: str = interface["mission_start_survey_text"]
MISSION_START_HINT_TEXT: str = interface["mission_start_hint_text"]
MISSION_FINISH_SURVEY_TEXT: str = interface["mission_finish_survey_text"]
MISSION_FINISH_HINT_TEXT: str = interface["mission_finish_hint_text"]
MISSION_COMMAND_SENT_TEXT: str = interface["mission_command_sent_text"]
MISSION_START_ACCEPTED_TEXT: str = interface["mission_start_accepted_text"]
MISSION_FINISH_ACCEPTED_TEXT: str = interface["mission_finish_accepted_text"]
MISSION_COMMAND_REJECTED_FORMAT: str = interface["mission_command_rejected_format"]
MISSION_COMMAND_TIMEOUT_TEXT: str = interface["mission_command_timeout_text"]
MISSION_PHASE_TEXTS: dict = interface["mission_phase_texts"]
MISSION_SURVEY_STATES: list = interface["mission_phase_groups"]["survey_states"]
MISSION_PROBLEM_STATES: list = interface["mission_phase_groups"]["problem_states"]
MISSION_START_SURVEY_STATES: list = interface["mission_phase_groups"]["start_survey_states"]
MISSION_FINISH_SURVEY_STATES: list = interface["mission_phase_groups"]["finish_survey_states"]

PAYLOAD_PANEL_TITLE: str = interface["payload_panel_title"]
PAYLOAD_STATION_FORMAT: str = interface["payload_station_format"]
PAYLOAD_WAITING_TEXT: str = interface["payload_waiting_text"]

ROUTE_HOVER_LABEL: str = interface["route_hover_label"]
ROUTE_RELEASE_LABEL: str = interface["route_release_label"]
TARGET_LABEL_FORMAT: str = interface["target_label_format"]
MAPPING_BROWSE_TEXT: str = interface["mapping_browse_text"]
MAPPING_START_TEXT: str = interface["mapping_start_text"]
MAPPING_FOLDER_DIALOG_TITLE: str = interface["mapping_folder_dialog_title"]
MAPPING_NO_FOLDER_TEXT: str = interface["mapping_no_folder_text"]
MAPPING_PREVIEW_PLACEHOLDER_TEXT: str = interface["mapping_preview_placeholder_text"]
MAPPING_REQUEST_SENT_TEXT: str = interface["mapping_request_sent_text"]
MAPPING_RUNNING_FORMAT: str = interface["mapping_running_format"]
MAPPING_PLACING_FORMAT: str = interface["mapping_placing_format"]
MAPPING_COMPLETE_FORMAT: str = interface["mapping_complete_format"]
MAPPING_FAILED_FORMAT: str = interface["mapping_failed_format"]

MAP_TILES_MISSING_TEXT: str = interface["map_tiles_missing_text"]
MAP_RECENTRE_TEXT: str = interface["map_recentre_text"]
MAP_FOLLOW_ON_TEXT: str = interface["map_follow_on_text"]
MAP_FOLLOW_OFF_TEXT: str = interface["map_follow_off_text"]

LOG_PANEL_TITLE: str = interface["log_panel_title"]
AUTOPILOT_LINE_FORMAT: str = interface["autopilot_line_format"]
AUTOPILOT_TAG: str = interface["autopilot_tag"]
AUTOPILOT_CRITICAL_MAX_SEVERITY: int = interface["autopilot_critical_max_severity"]
AUTOPILOT_CAUTION_MAX_SEVERITY: int = interface["autopilot_caution_max_severity"]

# The window's tabs, the FLIGHT card, the mission file reader and the
# CALIBRATION tab, each handed over as its own table of texts.
TABS_TEXT: dict = interface["tabs"]
FLIGHT_TEXT: dict = interface["flight"]
MISSION_FILE_TEXT: dict = interface["mission_file"]
CALIBRATION_TEXT: dict = interface["calibration"]

layout = interface["layout"]

MAP_STRETCH: int = layout["map_stretch"]
MAP_ROW_STRETCH: int = layout["map_row_stretch"]
LOG_ROW_STRETCH: int = layout["log_row_stretch"]
SIDE_COLUMN_STRETCH: int = layout["side_column_stretch"]
REVIEW_COLUMN_STRETCH: int = layout["review_column_stretch"]
DETECTION_COLUMN_STRETCH: int = layout["detection_column_stretch"]
SIDE_COLUMN_WIDTH: int = layout["side_column_width"]
REVIEW_COLUMN_WIDTH: int = layout["review_column_width"]
RIBBON_MINIMUM_HEIGHT: int = layout["ribbon_minimum_height"]
RIBBON_COLUMNS: int = layout["ribbon_columns"]
CLOCK_MINIMUM_HEIGHT: int = layout["clock_minimum_height"]
VIDEO_HEIGHT: int = layout["video_height"]
MAPPING_PREVIEW_MINIMUM_HEIGHT: int = layout["mapping_preview_minimum_height"]

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
MAP_READOUT: dict = map_settings["readout"]

map_sizes = map_settings["sizes"]

MAP_FLIGHT_BOUNDARY_WIDTH: int = map_sizes["flight_boundary_width"]
MAP_SEARCH_BOUNDARY_WIDTH: int = map_sizes["search_boundary_width"]
MAP_RUNWAY_WIDTH: int = map_sizes["runway_width"]
MAP_WAYPOINT_RADIUS_WIDTH: int = map_sizes["waypoint_radius_width"]
MAP_WAYPOINT_MARKER_RADIUS: int = map_sizes["waypoint_marker_radius"]
MAP_WAYPOINT_CURRENT_MARKER_RADIUS: int = map_sizes["waypoint_current_marker_radius"]
MAP_AIRCRAFT_MARKER_RADIUS: int = map_sizes["aircraft_marker_radius"]
MAP_AIRCRAFT_HEADING_LENGTH: int = map_sizes["aircraft_heading_length"]
MAP_AIRCRAFT_HEADING_WIDTH: int = map_sizes["aircraft_heading_width"]
MAP_NEXT_LEG_WIDTH: int = map_sizes["next_leg_width"]
MAP_TRACK_WIDTH: int = map_sizes["track_width"]
MAP_LABEL_OFFSET: int = map_sizes["label_offset"]
MAP_ROUTE_WIDTH: int = map_sizes["route_width"]
MAP_ROUTE_MARKER_RADIUS: int = map_sizes["route_marker_radius"]
MAP_TARGET_MARKER_RADIUS: int = map_sizes["target_marker_radius"]
MAP_BLACKLIST_WIDTH: int = map_sizes["blacklist_width"]

# Developer mode — the DEV tab

developer = config["developer"]

DEVELOPER_SSH_PROGRAM: str = developer["ssh_program"]
DEVELOPER_SSH_OPTIONS: list = developer["ssh_options"]
DEVELOPER_STOP_WAIT_MS: int = developer["stop_wait_ms"]
DEVELOPER_STATUS_POLL_S: float = developer["status_poll_s"]
DEVELOPER_MONITOR_MIN_HEIGHT: int = developer["monitor_min_height"]
DEVELOPER_VTOL: dict = developer["vtol"]
DEVELOPER_LOCAL: dict = developer["local"]
DEVELOPER_PUSH: dict = developer["push"]
DEVELOPER_COMMANDS: dict = developer["commands"]
# Only ever set in the git-ignored secrets.toml, never in developer.toml.
DEVELOPER_SUDO_PASSWORD: str = developer.get("sudo_password", "")
DEVELOPER_WIFI: dict = developer["wifi"]
DEVELOPER_NETWORK: dict = developer["network"]
DEVELOPER_DIAGNOSIS: dict = developer["diagnosis"]
DEVELOPER_LOG_STATES: dict = developer["log_states"]
DEVELOPER_LINK_TEST: dict = developer["link_test"]
DEVELOPER_TEXT: dict = developer["text"]
WIFI_DIALOG_TEXT: dict = developer["text"]["wifi_dialog"]
NETWORK_TEXT: dict = developer["text"]["network"]


# The TEST tab — the bench page for the camera, the release mechanism, the
# mapping stitch and the waypoint triggers.
#
# Its texts stay in dictionaries rather than becoming a hundred constants: the
# DEV tab does the same, and both are one page each read from one config file.

test = config["test"]

TEST_TAB_ENABLED: bool = test["enabled"]
TEST_TAB_TITLE: str = test["tab_title"]
TEST_PAGE_TITLES: dict = test["page_titles"]
TEST_COMMAND_ACK_TIMEOUT_MS: int = test["command_ack_timeout_ms"]
TEST_REFRESH_INTERVAL_MS: int = test["refresh_interval_ms"]
TEST_GIMBAL_STALE_SECONDS: float = test["gimbal_stale_seconds"]
TEST_LAYOUT: dict = test["layout"]
TEST_CAMERA_TEXT: dict = test["camera"]
TEST_TRANSFER_TEXT: dict = test["camera"]["transfer"]
TEST_CARD_TEXT: dict = test["camera"]["card"]
TEST_GIMBAL_TEXT: dict = test["gimbal"]
TEST_DROP_TEXT: dict = test["drop"]
TEST_WAYPOINT_TEXT: dict = test["waypoints"]
TEST_MAPPING_TEXT: dict = test["mapping"]
TEST_DETECTION_TEXT: dict = test["detection"]
TEST_LOGGING: dict = test["logging"]
TEST_SIGHTING_LOG: dict = test["sighting_log"]

# The TEST tab's own topics

TOPIC_GIMBAL_STATE: str = subscribe_topics["gimbal_state"]
TOPIC_CAMERA_MEDIA_LIST: str = subscribe_topics["camera_media_list"]
TOPIC_CAMERA_MEDIA_CHUNK: str = subscribe_topics["camera_media_chunk"]
TOPIC_CAMERA_TRANSFER: str = subscribe_topics["camera_transfer"]
TOPIC_PAYLOAD_SERVO: str = subscribe_topics["payload_servo"]
TOPIC_WAYPOINT_WATCH: str = subscribe_topics["waypoint_watch"]

TOPIC_GIMBAL_COMMAND: str = publish_topics["gimbal_command"]
TOPIC_WAYPOINT_WATCH_COMMAND: str = publish_topics["waypoint_watch_command"]

# The camera page's presses. The two columns send the same four actions to two
# different places, so they are read as one table and named by their prefix.
CAMERA_TEST_ACTIONS: dict = config["codes"]["camera_test_command"]

KEY_CAMERA_RATE: str = camera_command_keys["rate_hz"]
KEY_CAMERA_FILE_NAMES: str = camera_command_keys["file_names"]

# The mapping capture, started and stopped from the TEST tab

TOPIC_MAPPING_REQUEST: str = publish_topics["mapping_request"]
TOPIC_MAPPING_PROGRESS: str = subscribe_topics["mapping_progress"]

mapping_request_keys = config["payloads"]["mapping_request"]

KEY_MAPPING_COMMAND_ID: str = mapping_request_keys["command_id"]
KEY_MAPPING_ACTION: str = mapping_request_keys["action"]

MAPPING_ACTIONS: dict = config["codes"]["mapping_request"]

mapping_progress_keys = config["payloads"]["mapping_progress"]

KEY_MAPPING_FRAMES_CAPTURED: str = mapping_progress_keys["frames_captured"]
KEY_MAPPING_FRAMES_QUEUED: str = mapping_progress_keys["frames_queued"]
KEY_MAPPING_FRAMES_SENT: str = mapping_progress_keys["frames_sent"]
KEY_MAPPING_SESSION_ID: str = mapping_progress_keys["session_id"]

# The gimbal

gimbal_command_keys = config["payloads"]["gimbal_command"]

KEY_GIMBAL_COMMAND_ID: str = gimbal_command_keys["command_id"]
KEY_GIMBAL_ACTION: str = gimbal_command_keys["action"]
KEY_GIMBAL_COMMAND_YAW: str = gimbal_command_keys["yaw_degrees"]
KEY_GIMBAL_COMMAND_PITCH: str = gimbal_command_keys["pitch_degrees"]
KEY_GIMBAL_COMMAND_ZOOM: str = gimbal_command_keys["zoom"]

GIMBAL_ACTIONS: dict = config["codes"]["gimbal_command"]

gimbal_state_keys = config["payloads"]["gimbal_state"]

KEY_GIMBAL_REACHABLE: str = gimbal_state_keys["reachable"]
KEY_GIMBAL_YAW: str = gimbal_state_keys["yaw_degrees"]
KEY_GIMBAL_PITCH: str = gimbal_state_keys["pitch_degrees"]
KEY_GIMBAL_ROLL: str = gimbal_state_keys["roll_degrees"]
KEY_GIMBAL_ZOOM: str = gimbal_state_keys["zoom"]
KEY_GIMBAL_RECORDING: str = gimbal_state_keys["recording"]
KEY_GIMBAL_CARD_STATE: str = gimbal_state_keys["card_state"]
KEY_GIMBAL_CARD_FREE: str = gimbal_state_keys["card_free_megabytes"]
KEY_GIMBAL_STREAM_UP: str = gimbal_state_keys["stream_up"]
KEY_GIMBAL_REASON: str = gimbal_state_keys["reason"]

# The camera's card, and the copy off it

media_list_keys = config["payloads"]["camera_media_list"]

KEY_MEDIA_FILES: str = media_list_keys["files"]
KEY_MEDIA_PHOTO_COUNT: str = media_list_keys["photo_count"]
KEY_MEDIA_VIDEO_COUNT: str = media_list_keys["video_count"]
KEY_MEDIA_REASON: str = media_list_keys["reason"]

media_file_keys = config["payloads"]["camera_media_file"]

KEY_MEDIA_NAME: str = media_file_keys["name"]
KEY_MEDIA_KIND: str = media_file_keys["kind"]
KEY_MEDIA_SIZE: str = media_file_keys["size_bytes"]
KEY_MEDIA_FETCHED: str = media_file_keys["fetched"]

MEDIA_KIND_PHOTO: str = config["codes"]["camera_media_kind"]["photo"]
MEDIA_KIND_VIDEO: str = config["codes"]["camera_media_kind"]["video"]

chunk_keys = config["payloads"]["camera_media_chunk"]

KEY_CHUNK_FILE_NAME: str = chunk_keys["file_name"]
KEY_CHUNK_KIND: str = chunk_keys["kind"]
KEY_CHUNK_INDEX: str = chunk_keys["chunk_index"]
KEY_CHUNK_COUNT: str = chunk_keys["chunk_count"]
KEY_CHUNK_SIZE: str = chunk_keys["size_bytes"]
KEY_CHUNK_DATA: str = chunk_keys["data_base64"]

transfer_keys = config["payloads"]["camera_transfer"]

KEY_TRANSFER_STATE: str = transfer_keys["state"]
KEY_TRANSFER_FILE_NAME: str = transfer_keys["file_name"]
KEY_TRANSFER_FILES_DONE: str = transfer_keys["files_done"]
KEY_TRANSFER_FILES_TOTAL: str = transfer_keys["files_total"]
KEY_TRANSFER_BYTES_DONE: str = transfer_keys["bytes_done"]
KEY_TRANSFER_BYTES_TOTAL: str = transfer_keys["bytes_total"]
KEY_TRANSFER_SENDING_PHOTOS: str = transfer_keys["sending_photos"]
KEY_TRANSFER_SENDING_VIDEOS: str = transfer_keys["sending_videos"]
KEY_TRANSFER_WATCHING: str = transfer_keys["watching"]
KEY_TRANSFER_REASON: str = transfer_keys["reason"]

transfer_states = config["codes"]["camera_transfer_state"]

TRANSFER_STATE_IDLE: str = transfer_states["idle"]
TRANSFER_STATE_LISTING: str = transfer_states["listing"]
TRANSFER_STATE_FETCHING: str = transfer_states["fetching"]
TRANSFER_STATE_COMPLETE: str = transfer_states["complete"]
TRANSFER_STATE_FAILED: str = transfer_states["failed"]

# The release servos

KEY_SERVO_STATIONS: str = config["payloads"]["payload_servo"]["stations"]

servo_station_keys = config["payloads"]["servo_station"]

KEY_SERVO_STATION: str = servo_station_keys["station"]
KEY_SERVO_STATE: str = servo_station_keys["state"]
KEY_SERVO_PULSE: str = servo_station_keys["pwm_us"]
KEY_SERVO_OUTPUT: str = servo_station_keys["servo_output"]
KEY_SERVO_SIMULATED: str = servo_station_keys["simulated"]
KEY_SERVO_MOVED_AT: str = servo_station_keys["moved_at"]

SERVO_STATE_UNKNOWN: str = config["codes"]["servo_state"]["unknown"]

# A drop on a place the operator names: plan the route, look at it, fly it

TOPIC_ROUTE_COMMAND: str = publish_topics["route_command"]

route_command_keys = config["payloads"]["route_command"]

KEY_ROUTE_COMMAND_ID: str = route_command_keys["command_id"]
KEY_ROUTE_COMMAND_ACTION: str = route_command_keys["action"]
KEY_ROUTE_COMMAND_ROUTE_ID: str = route_command_keys["route_id"]
KEY_ROUTE_COMMAND_LATITUDE: str = route_command_keys["latitude"]
KEY_ROUTE_COMMAND_LONGITUDE: str = route_command_keys["longitude"]
KEY_ROUTE_COMMAND_ALTITUDE: str = route_command_keys["altitude_agl_metres"]
KEY_ROUTE_COMMAND_RADIUS: str = route_command_keys["acceptance_radius_metres"]
KEY_ROUTE_COMMAND_STATION: str = route_command_keys["station"]

ROUTE_ACTIONS: dict = config["codes"]["route_command"]

KEY_ROUTE_STATE: str = route_keys["state"]
KEY_ROUTE_REASON: str = route_keys["reason"]
KEY_ROUTE_STATION: str = route_keys["station"]

route_states = config["codes"]["route_state"]

ROUTE_STATE_PROPOSED: str = route_states["proposed"]
ROUTE_STATE_APPROVED: str = route_states["approved"]
ROUTE_STATE_FLYING: str = route_states["flying"]
ROUTE_STATE_REJECTED: str = route_states["rejected"]
ROUTE_STATE_DONE: str = route_states["done"]

# The waypoint monitor

watch_command_keys = config["payloads"]["waypoint_watch_command"]

KEY_WATCH_COMMAND_ID: str = watch_command_keys["command_id"]
KEY_WATCH_ACTION: str = watch_command_keys["action"]
KEY_WATCH_COMMAND_INDEX: str = watch_command_keys["waypoint_index"]

WATCH_ACTIONS: dict = config["codes"]["waypoint_watch_command"]

watch_keys = config["payloads"]["waypoint_watch"]

KEY_WATCH_START_INDEX: str = watch_keys["start_index"]
KEY_WATCH_FINISH_INDEX: str = watch_keys["finish_index"]
KEY_WATCH_WAYPOINT_INDEX: str = watch_keys["waypoint_index"]
KEY_WATCH_WAYPOINT_COUNT: str = watch_keys["waypoint_count"]
KEY_WATCH_TRIGGERED: str = watch_keys["triggered"]
KEY_WATCH_TRIGGERED_INDEX: str = watch_keys["triggered_index"]
KEY_WATCH_TRIGGERED_AT: str = watch_keys["triggered_at"]
KEY_WATCH_REASON: str = watch_keys["reason"]

WAYPOINT_TRIGGER_START: str = config["codes"]["waypoint_trigger"]["start"]
WAYPOINT_TRIGGER_FINISH: str = config["codes"]["waypoint_trigger"]["finish"]

# The detection bench

TOPIC_DETECTOR_COMMAND: str = publish_topics["detector_command"]
TOPIC_DETECTOR_STATE: str = subscribe_topics["detector_state"]
TOPIC_DETECTOR_SIGHTING: str = subscribe_topics["detector_sighting"]

detector_command_keys = config["payloads"]["detector_command"]

KEY_DETECTOR_COMMAND_ID: str = detector_command_keys["command_id"]
KEY_DETECTOR_ACTION: str = detector_command_keys["action"]
KEY_DETECTOR_COMMAND_BACKEND: str = detector_command_keys["backend"]
KEY_DETECTOR_COMMAND_CONFIDENCE: str = detector_command_keys["minimum_confidence"]

DETECTOR_ACTIONS: dict = config["codes"]["detector_command"]
DETECTOR_BACKENDS: dict = config["codes"]["detector_backend"]

detector_state_keys = config["payloads"]["detector_state"]

KEY_DETECTOR_RUNNING: str = detector_state_keys["running"]
KEY_DETECTOR_BACKEND: str = detector_state_keys["backend"]
KEY_DETECTOR_REQUESTED_BACKEND: str = detector_state_keys["requested_backend"]
KEY_DETECTOR_MINIMUM_CONFIDENCE: str = detector_state_keys["minimum_confidence"]
KEY_DETECTOR_FRAMES_PER_SECOND: str = detector_state_keys["frames_per_second"]
KEY_DETECTOR_FRAMES_SEEN: str = detector_state_keys["frames_seen"]
KEY_DETECTOR_SIGHTINGS: str = detector_state_keys["sightings"]
KEY_DETECTOR_REASON: str = detector_state_keys["reason"]

sighting_keys = config["payloads"]["detector_sighting"]

KEY_SIGHTING_ID: str = sighting_keys["sighting_id"]
KEY_SIGHTING_CLASS: str = sighting_keys["target_class"]
KEY_SIGHTING_CONFIDENCE: str = sighting_keys["confidence"]
KEY_SIGHTING_LATITUDE: str = sighting_keys["latitude"]
KEY_SIGHTING_LONGITUDE: str = sighting_keys["longitude"]
KEY_SIGHTING_IMAGE: str = sighting_keys["image_base64"]
KEY_SIGHTING_FRAME_TIMESTAMP: str = sighting_keys["frame_timestamp"]
KEY_SIGHTING_BACKEND: str = sighting_keys["backend"]
KEY_SIGHTING_POSITION_ERROR: str = sighting_keys["position_error_m"]
KEY_SIGHTING_PROJECTION_INPUTS: str = sighting_keys["projection_inputs"]


def active_waypoint_file() -> Path:
    return competition_path(WAYPOINT_FILES[RUNWAY_PROFILE])


def tile_file_path() -> Path:
    return competition_path(MAP_TILE_FILE)
