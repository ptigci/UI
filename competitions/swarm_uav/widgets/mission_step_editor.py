"""The task picker of the mission plan window.

Pick a task, fill in the values it needs, press ADD. Only the inputs the chosen
task actually uses are shown, so a plain ARM row has nothing to fill in and a
GO TO row shows its three coordinates plus the formation-rotation switch.

The widget hands finished steps up as PlanStep objects and keeps no plan of its
own — the window owns the list.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from competitions.swarm_uav.config import (
    ALTITUDE_CHANGE_MAX,
    ALTITUDE_CHANGE_MIN,
    FORMATION_ANGLE_MAX,
    FORMATION_ANGLE_MIN,
    FORMATION_CODE_INVERSE_V,
    FORMATION_CODE_V,
    FORMATION_DISTANCE_MAX,
    MIN_FORMATION_ANGLE,
    MIN_FORMATION_DISTANCE,
    MIN_TAKEOFF_ALTITUDE,
    MOVE_AXIS_MAX,
    MOVE_AXIS_MIN,
    PLAN_DEFAULT_ALTITUDE_CHANGE,
    PLAN_DEFAULT_FORMATION_ANGLE,
    PLAN_DEFAULT_FORMATION_DISTANCE,
    PLAN_DEFAULT_TAKEOFF_ALTITUDE,
    PLAN_FORMATION_LABELS,
    PLAN_STEP_TAKEOFF,
    PLAN_TEXT,
    SPINBOX_DECIMALS,
    TAKEOFF_ALTITUDE_MAX,
)
from competitions.swarm_uav.controller.mission_plan import STEP_KINDS, PlanStep


class MissionStepEditor(QWidget):
    """Builds one plan step at a time and emits it on ADD."""

    step_requested = pyqtSignal(object)  # PlanStep

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.kind_selector = QComboBox(self)
        for step_kind in STEP_KINDS:
            self.kind_selector.addItem(step_kind.label)
        self.kind_selector.currentIndexChanged.connect(self.show_inputs_for_kind)

        self.add_button = QPushButton(PLAN_TEXT["add_button"], self)
        self.add_button.clicked.connect(self.request_step)

        editor_layout = QVBoxLayout(self)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addLayout(self.build_kind_row())
        editor_layout.addWidget(self.build_position_row())
        editor_layout.addWidget(self.build_altitude_row())
        editor_layout.addWidget(self.build_formation_row())

        self.show_inputs_for_kind()

    # Row construction

    def build_kind_row(self) -> QHBoxLayout:
        kind_row = QHBoxLayout()
        kind_row.addWidget(QLabel("Task:", self))
        kind_row.addWidget(self.kind_selector, 1)
        kind_row.addWidget(self.add_button)
        return kind_row

    def build_position_row(self) -> QWidget:
        self.north_input = self.build_spinbox(MOVE_AXIS_MIN, MOVE_AXIS_MAX, 0.0)
        self.east_input = self.build_spinbox(MOVE_AXIS_MIN, MOVE_AXIS_MAX, 0.0)
        self.rotation_checkbox = QCheckBox(PLAN_TEXT["rotation_switch"], self)
        self.rotation_checkbox.setToolTip(PLAN_TEXT["rotation_tooltip"])

        self.position_row = QWidget(self)
        position_layout = QVBoxLayout(self.position_row)
        position_layout.setContentsMargins(0, 0, 0, 0)

        coordinate_layout = QHBoxLayout()
        coordinate_layout.addWidget(QLabel("North (m):", self.position_row))
        coordinate_layout.addWidget(self.north_input, 1)
        coordinate_layout.addWidget(QLabel("East (m):", self.position_row))
        coordinate_layout.addWidget(self.east_input, 1)
        position_layout.addLayout(coordinate_layout)
        position_layout.addWidget(self.rotation_checkbox)
        return self.position_row

    def build_altitude_row(self) -> QWidget:
        # The limits and the label belong to the chosen task, so they are set
        # in apply_altitude_limits rather than here.
        self.altitude_input = self.build_spinbox(
            MIN_TAKEOFF_ALTITUDE, TAKEOFF_ALTITUDE_MAX, PLAN_DEFAULT_TAKEOFF_ALTITUDE
        )
        self.altitude_row = QWidget(self)
        self.altitude_label = QLabel(PLAN_TEXT["takeoff_altitude_label"], self.altitude_row)
        altitude_layout = QHBoxLayout(self.altitude_row)
        altitude_layout.setContentsMargins(0, 0, 0, 0)
        altitude_layout.addWidget(self.altitude_label)
        altitude_layout.addWidget(self.altitude_input, 1)
        return self.altitude_row

    def build_formation_row(self) -> QWidget:
        self.formation_selector = QComboBox(self)
        for formation_code, formation_label in PLAN_FORMATION_LABELS.items():
            self.formation_selector.addItem(formation_label, formation_code)
        self.distance_input = self.build_spinbox(
            MIN_FORMATION_DISTANCE, FORMATION_DISTANCE_MAX, PLAN_DEFAULT_FORMATION_DISTANCE
        )
        self.angle_input = self.build_spinbox(
            FORMATION_ANGLE_MIN, FORMATION_ANGLE_MAX, PLAN_DEFAULT_FORMATION_ANGLE
        )

        self.formation_row = QWidget(self)
        formation_layout = QHBoxLayout(self.formation_row)
        formation_layout.setContentsMargins(0, 0, 0, 0)
        formation_layout.addWidget(QLabel("Formation:", self.formation_row))
        formation_layout.addWidget(self.formation_selector, 1)
        formation_layout.addWidget(QLabel("Distance (m):", self.formation_row))
        formation_layout.addWidget(self.distance_input, 1)
        formation_layout.addWidget(QLabel("Angle (°):", self.formation_row))
        formation_layout.addWidget(self.angle_input, 1)
        return self.formation_row

    def build_spinbox(self, minimum: float, maximum: float, value: float) -> QDoubleSpinBox:
        spinbox = QDoubleSpinBox(self)
        spinbox.setDecimals(SPINBOX_DECIMALS)
        spinbox.setRange(minimum, maximum)
        spinbox.setValue(value)
        return spinbox

    # Behaviour

    def selected_kind(self):
        return STEP_KINDS[self.kind_selector.currentIndex()]

    def show_inputs_for_kind(self) -> None:
        """Leave only the inputs the chosen task uses on screen."""
        step_kind = self.selected_kind()
        self.position_row.setVisible(step_kind.needs_position)
        self.altitude_row.setVisible(step_kind.needs_altitude)
        self.formation_row.setVisible(step_kind.needs_formation)
        if step_kind.needs_altitude:
            self.apply_altitude_limits(step_kind)

    def apply_altitude_limits(self, step_kind) -> None:
        """Point the altitude field at what the chosen task does with it.

        A take-off climbs to a height and needs a real one. A go-to only
        changes the height it is already flying at, so it starts at no change
        and takes a negative value to descend.
        """
        if step_kind.code == PLAN_STEP_TAKEOFF:
            self.altitude_label.setText(PLAN_TEXT["takeoff_altitude_label"])
            self.altitude_input.setToolTip("")
            self.altitude_input.setRange(MIN_TAKEOFF_ALTITUDE, TAKEOFF_ALTITUDE_MAX)
            self.altitude_input.setValue(PLAN_DEFAULT_TAKEOFF_ALTITUDE)
            return

        self.altitude_label.setText(PLAN_TEXT["altitude_change_label"])
        self.altitude_input.setToolTip(PLAN_TEXT["altitude_change_tooltip"])
        self.altitude_input.setRange(ALTITUDE_CHANGE_MIN, ALTITUDE_CHANGE_MAX)
        self.altitude_input.setValue(PLAN_DEFAULT_ALTITUDE_CHANGE)

    def request_step(self) -> None:
        """Validate the inputs and hand the finished step to the window."""
        step_kind = self.selected_kind()
        step = PlanStep(step_kind.code)

        if step_kind.needs_altitude:
            if not self.check_altitude(step_kind):
                return
            step.altitude = self.altitude_input.value()
        if step_kind.needs_position:
            step.north = self.north_input.value()
            step.east = self.east_input.value()
            step.rotate_formation = self.rotation_checkbox.isChecked()
        if step_kind.needs_formation and not self.fill_formation(step):
            return

        self.step_requested.emit(step)

    def check_altitude(self, step_kind) -> bool:
        """Only a take-off needs a real altitude; a go-to may hold or descend."""
        if step_kind.code != PLAN_STEP_TAKEOFF:
            return True
        if self.altitude_input.value() > MIN_TAKEOFF_ALTITUDE:
            return True
        QMessageBox.warning(
            self,
            "Invalid step",
            f"{step_kind.label} needs an altitude greater than "
            f"{MIN_TAKEOFF_ALTITUDE:g} m.",
        )
        return False

    def fill_formation(self, step: PlanStep) -> bool:
        formation_code = self.formation_selector.currentData()
        distance = self.distance_input.value()
        angle = self.angle_input.value()

        if distance <= MIN_FORMATION_DISTANCE:
            QMessageBox.warning(
                self,
                "Invalid step",
                f"Formation distance must be greater than {MIN_FORMATION_DISTANCE:g} m.",
            )
            return False
        needs_angle = formation_code in (FORMATION_CODE_V, FORMATION_CODE_INVERSE_V)
        if needs_angle and angle < MIN_FORMATION_ANGLE:
            QMessageBox.warning(
                self,
                "Invalid step",
                f"Angle must be at least {MIN_FORMATION_ANGLE:g}° for V formations.",
            )
            return False

        step.formation_code = formation_code
        step.formation_distance = distance
        step.formation_angle = angle
        return True
