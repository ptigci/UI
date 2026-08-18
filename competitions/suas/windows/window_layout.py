"""How the window is put together: the panels, the columns, the wiring.

Split out of ``main_window.py`` for size. It is a mixin rather than a separate
builder so the window keeps its own ``build_layout`` under its own name and
nothing that called it had to change.

The one rule the layout exists to keep is §3.0.6: the map is never covered,
never behind a tab and never smaller than it has to be. So the clock, the ribbon
and the map controls take the height their contents need, the side column is a
fixed width, and every pixel left over is the map's. Resizing the window can
only ever give the map more room.

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
    MAP_FOLLOW_ON_TEXT,
    MAP_RECENTRE_TEXT,
    MAP_STRETCH,
    SIDE_COLUMN_STRETCH,
    SIDE_COLUMN_WIDTH,
)
from competitions.suas.widgets import (
    CameraPanel, DetectionColumn, DropTestPanel, LapTracker, MapView, MissionClock,
    SafetyPanel, TelemetryRibbon,
)
from theme import flush_layout, set_variant, space_layout
from theme.layout import NO_SPACING
from theme.tokens import SPACE_LG, SPACE_MD, VARIANT_GHOST

# The clock, the ribbon and the map controls are sized by their contents. Every
# pixel left over goes to the map, which 3.0.6 makes the point of the window.
CLOCK_ROW_STRETCH = 0
RIBBON_ROW_STRETCH = 0
CONTROLS_ROW_STRETCH = 0
MAP_ROW_STRETCH = 1


class WindowLayoutMixin:
    """Builds the window's widgets and connects them to each other."""

    def build_layout(self) -> None:
        self.mission_clock = MissionClock(self)
        self.map_view = MapView(self)
        self.telemetry_ribbon = TelemetryRibbon(self)
        self.lap_tracker = LapTracker(self)
        self.detection_column = DetectionColumn(self)
        self.safety_panel = SafetyPanel(self)
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

        self.follow_button = self.build_map_button(MAP_FOLLOW_ON_TEXT)
        self.fit_button = self.build_map_button(MAP_RECENTRE_TEXT)

        map_controls = QWidget(self)
        controls_layout = QHBoxLayout(map_controls)
        flush_layout(controls_layout, SPACE_MD)
        controls_layout.addWidget(self.follow_button)
        controls_layout.addWidget(self.fit_button)
        controls_layout.addStretch()

        # The controls take their own height and the map takes everything else,
        # or a row of buttons ends up with as much of the window as the map.
        map_column = QWidget(self)
        map_layout = QVBoxLayout(map_column)
        flush_layout(map_layout, SPACE_MD)
        map_layout.addWidget(self.map_view, MAP_ROW_STRETCH)
        map_layout.addWidget(map_controls, CONTROLS_ROW_STRETCH)

        # The three side panels want more height than a laptop screen has
        # once the clock and the ribbon have taken theirs, so the column
        # scrolls. Without this Qt shrinks them below the size they can draw
        # in and they overlap each other -- the safety buttons ended up on top
        # of the detection browser, which is the one place that must never
        # happen.
        side_contents = QWidget(self)
        side_layout = QVBoxLayout(side_contents)
        flush_layout(side_layout, SPACE_MD)
        side_layout.addWidget(self.lap_tracker)
        # High in the column, because the picture is what the operator glances
        # at between everything else.
        if self.camera_panel is not None:
            side_layout.addWidget(self.camera_panel)
        side_layout.addWidget(self.detection_column, DETECTION_COLUMN_STRETCH)
        if self.drop_test_panel is not None:
            side_layout.addWidget(self.drop_test_panel)
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

        # A fixed-width side column and a stretching map, so resizing the window
        # can only ever give the map more room, never less.
        columns = QWidget(self)
        columns_layout = QHBoxLayout(columns)
        space_layout(columns_layout, SPACE_LG, SPACE_LG)
        columns_layout.addWidget(map_column, MAP_STRETCH)
        columns_layout.addWidget(side_column, SIDE_COLUMN_STRETCH)

        # The clock and the ribbon take the height they need; everything left
        # over goes to the map, which 3.0.6 makes the point of the window. Both
        # run edge to edge, so the map keeps every pixel in between.
        flush_layout(self.rootlayout, NO_SPACING)
        self.rootlayout.addWidget(self.mission_clock, CLOCK_ROW_STRETCH)
        self.rootlayout.addWidget(columns, MAP_ROW_STRETCH)
        self.rootlayout.addWidget(self.telemetry_ribbon, RIBBON_ROW_STRETCH)

    def build_map_button(self, text: str) -> QPushButton:
        """Quiet controls: nothing beside the map competes with the map."""
        button = QPushButton(text, self)
        set_variant(button, VARIANT_GHOST)
        return button

    def connect_widgets(self) -> None:
        self.follow_button.clicked.connect(self.toggle_follow)
        self.fit_button.clicked.connect(self.map_view.fit_flight_boundary)
        self.map_view.follow_changed.connect(self.show_follow_state)

        self.detection_column.approve_requested.connect(self.approve_detection)
        self.detection_column.reject_requested.connect(self.reject_detection)
        self.safety_panel.return_to_launch_requested.connect(self.return_to_launch)
        self.safety_panel.terminate_requested.connect(self.terminate_flight)

        if self.camera_panel is not None:
            self.camera_panel.start_recording_requested.connect(self.start_recording)
            self.camera_panel.stop_recording_requested.connect(self.stop_recording)

        if self.drop_test_panel is None:
            return
        self.drop_test_panel.goto_target_requested.connect(self.go_to_drop_zone)
        self.drop_test_panel.release_requested.connect(self.release_payload)
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
        self.safety_heartbeat_received.connect(self.handle_safety_heartbeat)
        self.safety_command_acknowledged.connect(self.handle_safety_acknowledgement)
