"""How the window is put together: the panels, the columns, the wiring.

Split out of ``main_window.py`` for size. It is a mixin rather than a separate
builder so the window keeps its own ``build_layout`` under its own name and
nothing that called it had to change.

Three columns between the clock and the ribbon, and everything on one screen.

The left column is the two things the operator looks at rather than reads: the
live picture, and the detection crop under it. Both are always on the screen
and neither is scrolled, because they are what a verdict is made from. The map
is in the middle. The right column is everything that is read -- the phase, the
laps, the payload, the way out -- and it is the one that scrolls when a laptop
screen runs out of height.

Both side columns are a fixed width and the map takes what is left, so widening
the window can only ever give the map more room and nothing ever slides off the
side. §3.0.6 asks for a map the judge can always see, which this is; it does not
ask for a big one, and the picture and the crop earn their half of the screen.

That page is the MISSION tab. The aircraft's own controls — import a mission,
start it, arm, the modes — sit in the right column directly under the mission
panel, with the mission controls the operator already uses, and the
autopilot's log is under the map, because both are used while flying. The
calibrations are not: they sit on a CALIBRATION tab beside the mission
(``dev_tab.py`` builds the tabs), for the bench and the minutes before takeoff.
Developer mode adds TEST and DEV after it.

Two panels are optional and both are decided in ``config/general.toml``. A
scored mission has no delivery buttons, because §3.3 pays 200 points for a
mission that runs without anybody pressing anything.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from competitions.suas.config import (
    CAMERA_PANEL_ENABLED,
    DETECTION_COLUMN_STRETCH,
    DROP_PANEL_ENABLED,
    LOG_ROW_STRETCH,
    MAP_FOLLOW_ON_TEXT,
    MAP_RECENTRE_TEXT,
    MAP_ROW_STRETCH,
    MAP_STRETCH,
    MAPPING_PANEL_ENABLED,
    REVIEW_COLUMN_STRETCH,
    REVIEW_COLUMN_WIDTH,
    SIDE_COLUMN_STRETCH,
    SIDE_COLUMN_WIDTH,
)
from competitions.suas.widgets import (
    CalibrationPanel, CameraPanel, DetectionColumn, DropTestPanel, FlightPanel,
    LapTracker, LogPanel, MappingPanel, MapView, MissionClock, MissionPanel,
    PayloadPanel, SafetyPanel, TelemetryRibbon,
)
from theme import flush_layout, set_variant, space_layout
from theme.layout import NO_SPACING
from theme.tokens import SPACE_LG, SPACE_MD, VARIANT_GHOST

# The clock, the ribbon and the map controls are sized by their contents. Every
# pixel left over goes to the columns, and inside them to the map, which 3.0.6
# makes the point of the window.
CLOCK_ROW_STRETCH = 0
RIBBON_ROW_STRETCH = 0
CONTROLS_ROW_STRETCH = 0
COLUMNS_ROW_STRETCH = 1


class WindowLayoutMixin:
    """Builds the window's widgets and connects them to each other."""

    def build_layout(self) -> None:
        self.mission_clock = MissionClock(self)
        self.map_view = MapView(self)
        self.telemetry_ribbon = TelemetryRibbon(self)
        self.mission_panel = MissionPanel(self)
        self.lap_tracker = LapTracker(self)
        self.detection_column = DetectionColumn(self)
        self.payload_panel = PayloadPanel(self)
        self.safety_panel = SafetyPanel(self)
        self.log_panel = LogPanel(self)
        self.flight_panel = FlightPanel(self)
        self.calibration_panel = CalibrationPanel(self)
        # Only on the screen for a delivery test. A scored mission delivers with
        # nobody pressing anything, and the map gets the room back.
        if DROP_PANEL_ENABLED:
            self.drop_test_panel = DropTestPanel(self)
        else:
            self.drop_test_panel = None

        if CAMERA_PANEL_ENABLED:
            self.camera_panel = CameraPanel(self)
        else:
            self.camera_panel = None

        # The mapping bench: stitch a folder of recorded frames and look at
        # the result. A test tool like the delivery panel, off for a scored
        # mission for the same reason.
        if MAPPING_PANEL_ENABLED:
            self.mapping_panel = MappingPanel(self)
        else:
            self.mapping_panel = None

        self.follow_button = self.build_map_button(MAP_FOLLOW_ON_TEXT)
        self.fit_button = self.build_map_button(MAP_RECENTRE_TEXT)

        map_controls = QWidget(self)
        controls_layout = QHBoxLayout(map_controls)
        flush_layout(controls_layout, SPACE_MD)
        controls_layout.addWidget(self.follow_button)
        controls_layout.addWidget(self.fit_button)
        controls_layout.addStretch()

        # The controls take their own height, the autopilot's log under them
        # takes a little, and the map takes everything else -- or a row of
        # buttons ends up with as much of the window as the map.
        map_column = QWidget(self)
        map_layout = QVBoxLayout(map_column)
        flush_layout(map_layout, SPACE_MD)
        map_layout.addWidget(self.map_view, MAP_ROW_STRETCH)
        map_layout.addWidget(map_controls, CONTROLS_ROW_STRETCH)
        map_layout.addWidget(self.log_panel, LOG_ROW_STRETCH)

        # The picture at the height that keeps it 16:9, and the crop under it
        # taking everything else. Neither is ever scrolled: these are the two
        # the operator judges a target from, so a verdict never waits on
        # finding them.
        review_column = QWidget(self)
        review_layout = QVBoxLayout(review_column)
        flush_layout(review_layout, SPACE_MD)
        if self.camera_panel is not None:
            review_layout.addWidget(self.camera_panel)
        review_layout.addWidget(self.detection_column, DETECTION_COLUMN_STRETCH)
        review_column.setMinimumWidth(REVIEW_COLUMN_WIDTH)
        review_column.setMaximumWidth(REVIEW_COLUMN_WIDTH)

        # The panels that are read rather than looked at. Together they want
        # more height than a laptop screen has once the clock and the ribbon
        # have taken theirs, so this column scrolls. Without it Qt shrinks them
        # below the size they can draw in and they overlap each other.
        side_contents = QWidget(self)
        side_layout = QVBoxLayout(side_contents)
        flush_layout(side_layout, SPACE_MD)
        side_layout.addWidget(self.mission_panel)
        side_layout.addWidget(self.flight_panel)
        side_layout.addWidget(self.lap_tracker)
        if self.drop_test_panel is not None:
            side_layout.addWidget(self.drop_test_panel)
        if self.mapping_panel is not None:
            side_layout.addWidget(self.mapping_panel)
        side_layout.addWidget(self.payload_panel)
        side_layout.addWidget(self.safety_panel)

        side_column = QScrollArea(self)
        side_column.setWidget(side_contents)
        side_column.setWidgetResizable(True)
        side_column.setFrameShape(QFrame.Shape.NoFrame)
        side_column.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        side_column.setMinimumWidth(SIDE_COLUMN_WIDTH)
        side_column.setMaximumWidth(SIDE_COLUMN_WIDTH)

        # Two fixed-width columns and a stretching map between them, so resizing
        # the window can only ever give the map more room, never less, and
        # nothing is ever wide enough to need scrolling sideways to reach.
        columns = QWidget(self)
        columns_layout = QHBoxLayout(columns)
        space_layout(columns_layout, SPACE_LG, SPACE_LG)
        columns_layout.addWidget(review_column, REVIEW_COLUMN_STRETCH)
        columns_layout.addWidget(map_column, MAP_STRETCH)
        columns_layout.addWidget(side_column, SIDE_COLUMN_STRETCH)

        # The clock and the ribbon take the height they need; everything left
        # over goes to the map, which 3.0.6 makes the point of the window. Both
        # run edge to edge, so the map keeps every pixel in between. This page
        # is the MISSION tab, with CALIBRATION beside it.
        mission_page = QWidget(self)
        mission_layout = QVBoxLayout(mission_page)
        flush_layout(mission_layout, NO_SPACING)
        mission_layout.addWidget(self.mission_clock, CLOCK_ROW_STRETCH)
        mission_layout.addWidget(columns, COLUMNS_ROW_STRETCH)
        mission_layout.addWidget(self.telemetry_ribbon, RIBBON_ROW_STRETCH)
        flush_layout(self.rootlayout, NO_SPACING)
        self.rootlayout.addWidget(self.wrap_in_tabs(mission_page, self.calibration_panel))

    def build_map_button(self, text: str) -> QPushButton:
        """Quiet controls: nothing beside the map competes with the map."""
        button = QPushButton(text, self)
        set_variant(button, VARIANT_GHOST)
        return button

    def connect_widgets(self) -> None:
        self.follow_button.clicked.connect(self.toggle_follow)
        self.fit_button.clicked.connect(self.map_view.fit_flight_boundary)
        self.map_view.follow_changed.connect(self.show_follow_state)

        self.mission_panel.start_survey_requested.connect(self.start_survey)
        self.mission_panel.finish_survey_requested.connect(self.finish_survey)
        self.detection_column.approve_requested.connect(self.approve_detection)
        self.detection_column.reject_requested.connect(self.reject_detection)
        self.safety_panel.return_to_launch_requested.connect(self.return_to_launch)
        self.safety_panel.terminate_requested.connect(self.terminate_flight)

        self.flight_panel.mission_file_chosen.connect(self.import_mission)
        self.flight_panel.command_requested.connect(self.send_aircraft_command)
        self.flight_panel.mode_requested.connect(self.set_aircraft_mode)
        self.calibration_panel.calibration_requested.connect(self.send_calibration_command)

        if self.camera_panel is not None:
            self.camera_panel.start_recording_requested.connect(self.start_recording)
            self.camera_panel.stop_recording_requested.connect(self.stop_recording)

        if self.mapping_panel is not None:
            self.mapping_panel.stitch_requested.connect(self.start_folder_stitch)
            self.mapping_panel.export_requested.connect(self.controller.send_export_request)

        if self.drop_test_panel is None:
            return
        self.drop_test_panel.goto_target_requested.connect(self.go_to_drop_zone)
        self.drop_test_panel.release_requested.connect(self.release_payload)
        self.drop_test_panel.hold_requested.connect(self.hold_payload)
        self.drop_test_panel.return_to_launch_requested.connect(self.return_to_launch)
        self.drop_test_panel.land_requested.connect(self.land_aircraft)

    def connect_controller(self) -> None:
        self.controller.on_telemetry = self.telemetry_received.emit
        self.controller.on_mission_changed = self.mission_changed.emit
        self.controller.on_waypoint_changed = self.waypoint_changed.emit
        self.controller.on_detection = self.detection_received.emit
        self.controller.on_release_changed = self.release_countdown_received.emit
        self.controller.on_flight_command_answered = self.flight_command_answered.emit
        self.controller.on_video_frame = self.video_frame_received.emit
        self.controller.on_camera_changed = self.camera_changed.emit
        self.controller.on_camera_command_answered = self.camera_command_answered.emit
        self.controller.on_mission_command_answered = self.mission_command_answered.emit
        self.controller.on_stitch_changed = self.stitch_state_received.emit
        self.controller.on_route_changed = self.route_changed.emit
        self.controller.on_targets_changed = self.targets_changed.emit
        self.controller.on_payload_changed = self.payload_changed.emit
        self.controller.on_statustext = self.autopilot_message.emit
        self.controller.on_command_result = self.command_result_received.emit
        self.controller.on_calibration_progress = self.calibration_progressed.emit
        self.controller.on_aircraft_command_answered = self.aircraft_command_answered.emit
        self.controller.on_calibration_command_answered = self.calibration_command_answered.emit
        self.safety_link.on_heartbeat = self.safety_heartbeat_received.emit
        self.safety_link.on_command_acknowledged = self.safety_command_acknowledged.emit

        self.telemetry_received.connect(self.handle_telemetry)
        self.mission_changed.connect(self.handle_mission_changed)
        self.waypoint_changed.connect(self.handle_waypoint_changed)
        self.detection_received.connect(self.handle_detection)
        self.release_countdown_received.connect(self.handle_release_countdown)
        self.flight_command_answered.connect(self.handle_flight_command_answer)
        self.video_frame_received.connect(self.handle_video_frame)
        self.camera_changed.connect(self.handle_camera_changed)
        self.camera_command_answered.connect(self.handle_camera_command_answer)
        self.mission_command_answered.connect(self.handle_mission_command_answer)
        self.stitch_state_received.connect(self.handle_stitch_state)
        self.route_changed.connect(self.handle_route_changed)
        self.targets_changed.connect(self.handle_targets_changed)
        self.payload_changed.connect(self.handle_payload_changed)
        self.autopilot_message.connect(self.handle_statustext)
        self.command_result_received.connect(self.handle_command_result)
        self.calibration_progressed.connect(self.handle_calibration_progress)
        self.aircraft_command_answered.connect(self.handle_aircraft_command_answer)
        self.calibration_command_answered.connect(self.handle_calibration_command_answer)
        self.safety_heartbeat_received.connect(self.handle_safety_heartbeat)
        self.safety_command_acknowledged.connect(self.handle_safety_acknowledgement)
