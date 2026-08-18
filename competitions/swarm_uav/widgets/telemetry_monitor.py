"""The readings column of the swarm tab: one block per drone.

Position, mission state, PPS clock and message age for every vehicle, inside a
scroll area so a long list of drones scrolls instead of squeezing the camera
grid beside it.

The column keeps itself as wide as the blocks in it. Readings arrive wider than
the "0.00" the blocks are built with — a position in the hundreds, a state name
like RejoiningFormation, a PPS error in brackets — and a column sized once at
startup leaves the right-hand blocks and the tail of every long reading outside
the panel, where the horizontal scrollbar is switched off and nothing can bring
them back.
"""

import math

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QScrollArea, QWidget

from config import POSITION_DECIMALS
from competitions.swarm_uav.config import (
    STATE_UNKNOWN_TEXT,
    SWARM_GRID_COLUMNS,
    SWARM_TELEMETRY_VISIBLE_DRONES,
)
from competitions.swarm_uav.widgets.clock_status import ClockStatusLabel
from theme import set_role
from theme.tokens import ROLE_HEADING, ROLE_READOUT, ROLE_READOUT_LABEL
from widgets.connection_status import ConnectionStatusLabel

POSITION_AXES = ("x", "y", "z", "v")

# rows of a drone block, under the vehicle name on row 0
STATE_ROW = len(POSITION_AXES) + 1
CLOCK_ROW = len(POSITION_AXES) + 2
AGE_ROW = len(POSITION_AXES) + 3


class TelemetryMonitor(QScrollArea):
    """Everything the swarm tab shows about the vehicles, drone by drone."""

    def __init__(self, drones: list[tuple[int, str]], parent=None) -> None:
        """drones is a list of (vehicle_id, display_name) tuples."""
        super().__init__(parent)
        self.rows: dict[int, dict] = {}

        blocks_layout = QGridLayout()
        drone_blocks = []
        for grid_index, (drone_id, drone_name) in enumerate(drones):
            drone_block = self.build_drone_block(drone_id, drone_name)
            drone_blocks.append(drone_block)
            blocks_layout.addLayout(
                drone_block,
                grid_index // SWARM_GRID_COLUMNS,
                grid_index % SWARM_GRID_COLUMNS,
            )

        blocks_widget = QWidget(self)
        blocks_widget.setLayout(blocks_layout)

        self.setWidget(blocks_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.reserve_height(blocks_layout, drone_blocks, len(drones))
        self.reserve_width()

    # Building

    def build_field_label(self, text: str) -> QLabel:
        """The name of a reading, next to the reading itself."""
        field_label = QLabel(text)
        set_role(field_label, ROLE_READOUT_LABEL)
        return field_label

    def build_value_label(self, text: str) -> QLabel:
        """The reading itself."""
        value_label = QLabel(text)
        set_role(value_label, ROLE_READOUT)
        return value_label

    def build_drone_block(self, drone_id: int, drone_name: str) -> QGridLayout:
        drone_block = QGridLayout()

        header_label = QLabel(drone_name.upper())
        set_role(header_label, ROLE_HEADING)
        drone_block.addWidget(header_label, 0, 0, 1, 2)

        value_labels = {}
        zero_text = f"{0.0:.{POSITION_DECIMALS}f}"
        for axis_row, axis_name in enumerate(POSITION_AXES, start=1):
            drone_block.addWidget(self.build_field_label(f"{axis_name}:"), axis_row, 0)
            value_label = self.build_value_label(zero_text)
            drone_block.addWidget(value_label, axis_row, 1)
            value_labels[axis_name] = value_label

        state_label = self.build_value_label(STATE_UNKNOWN_TEXT)
        drone_block.addWidget(self.build_field_label("state:"), STATE_ROW, 0)
        drone_block.addWidget(state_label, STATE_ROW, 1)

        # the label text carries its own "PPS:" prefix, so it spans the row
        clock_label = ClockStatusLabel()
        drone_block.addWidget(clock_label, CLOCK_ROW, 0, 1, 2)

        age_label = ConnectionStatusLabel()
        drone_block.addWidget(self.build_field_label("ms:"), AGE_ROW, 0)
        drone_block.addWidget(age_label, AGE_ROW, 1)

        self.rows[drone_id] = {
            "axes": value_labels,
            "state": state_label,
            "clock": clock_label,
            "age": age_label,
        }
        return drone_block

    # Size

    def reserve_height(self, blocks_layout: QGridLayout, drone_blocks: list, drone_count: int) -> None:
        """Room for the first SWARM_TELEMETRY_VISIBLE_DRONES blocks; the rest scroll."""
        visible_drone_count = min(drone_count, SWARM_TELEMETRY_VISIBLE_DRONES)
        visible_block_rows = math.ceil(visible_drone_count / SWARM_GRID_COLUMNS)
        block_height = max(block.sizeHint().height() for block in drone_blocks)
        grid_margins = blocks_layout.contentsMargins()
        self.setMinimumHeight(
            visible_block_rows * block_height
            + (visible_block_rows - 1) * blocks_layout.verticalSpacing()
            + grid_margins.top() + grid_margins.bottom()
        )

    def reserve_width(self) -> None:
        """Claim the width the blocks need, growing as the readings do.

        A widget inside a scroll area does not push on the layout around it, so
        the column has to ask for the room itself. It only ever widens: giving
        the space back on the next message would leave the digits shuffling
        sideways while someone is trying to read them.
        """
        needed_width = (
            self.widget().sizeHint().width()
            + self.verticalScrollBar().sizeHint().width()
        )
        if needed_width > self.minimumWidth():
            self.setMinimumWidth(needed_width)

    # Data updates

    def update_position(self, drone_id: int, x: float, y: float, z: float, velocity: float) -> None:
        telemetry_row = self.rows.get(drone_id)
        if telemetry_row is None:
            return
        for axis_name, value in zip(POSITION_AXES, (x, y, z, velocity)):
            telemetry_row["axes"][axis_name].setText(f"{value:.{POSITION_DECIMALS}f}")
        self.reserve_width()

    def set_connection_age(self, drone_id: int, age_milliseconds: int | None) -> None:
        telemetry_row = self.rows.get(drone_id)
        if telemetry_row is None:
            return
        telemetry_row["age"].set_age(age_milliseconds)
        self.reserve_width()

    def set_state(self, drone_id: int, state_text: str) -> None:
        telemetry_row = self.rows.get(drone_id)
        if telemetry_row is None:
            return
        telemetry_row["state"].setText(state_text)
        self.reserve_width()

    def set_clock_status(self, drone_id: int, disciplined: bool, error_ms: float | None) -> None:
        telemetry_row = self.rows.get(drone_id)
        if telemetry_row is None:
            return
        telemetry_row["clock"].show_status(disciplined, error_ms)
        self.reserve_width()
