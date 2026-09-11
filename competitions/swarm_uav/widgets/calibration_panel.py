"""CALIBRATION tab: the numbers every drone has to measure about itself.

A drone's command latency and its velocity response are properties of that
airframe, not of the fleet, so each one measures its own and writes the answer
into its own config. This tab ticks the drones, runs a measurement on all of
them at once and collects the answers as they come back over the mesh.

The steps are laid out in the order they have to be run and each says what
state the drones must be in, because getting that wrong is how a measurement
comes back looking fine and wrong. The measurements themselves live on the
drones; this file only asks for them.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from competitions.swarm_uav.config import (
    CALIBRATION_DRONES_HINT,
    CALIBRATION_DRONES_TITLE,
    CALIBRATION_MEASURED_LABELS,
    CALIBRATION_NO_DRONES_TEXT,
    CALIBRATION_RESULTS_COLUMNS,
    CALIBRATION_RESULTS_EMPTY_TEXT,
    CALIBRATION_RESULTS_MAX_ROWS,
    CALIBRATION_RESULTS_MIN_HEIGHT,
    CALIBRATION_RESULTS_TITLE,
    CALIBRATION_STATUS_STATES,
    CALIBRATION_STEPS,
    CALIBRATION_STEPS_TITLE,
    CALIBRATION_UNKNOWN_DRONE_TEXT,
)
from theme import flush_layout, set_role, set_variant, space_layout
from theme.tokens import ROLE_HINT, STATE_CRITICAL
from widgets.card import Card
from widgets.status_pill import StatusPill

NEWEST_ROW = 0
DRONE_COLUMN, STATUS_COLUMN, MEASURED_COLUMN, NOTE_COLUMN = range(4)


class CalibrationPanel(QWidget):
    """Tick the drones, press a measurement, read the answers."""

    # Carries the step name from the config and the ticked drone ids; the main
    # window owns the controller and turns it into a command.
    calibration_requested = pyqtSignal(str, list)

    def __init__(self, drones: list[tuple[int, str]], parent=None) -> None:
        """drones is a list of (vehicle_id, display_name) tuples."""
        super().__init__(parent)
        self.drone_names = dict(drones)
        self.drone_checkboxes: dict[int, QCheckBox] = {}
        # Kept so a resize can give each of them the height its text needs.
        self.hint_labels: list[QLabel] = []

        # Four measurements, each with the state its drones have to be in, are
        # taller than the window is allowed to get, so the page scrolls rather
        # than squeezing the hints under the buttons.
        page = QWidget(self)
        page_layout = QVBoxLayout(page)
        space_layout(page_layout)
        page_layout.addWidget(self.build_drones_card())
        page_layout.addWidget(self.build_steps_card())
        page_layout.addWidget(self.build_results_card(), 1)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(page)
        panel_layout = QVBoxLayout(self)
        flush_layout(panel_layout)
        panel_layout.addWidget(scroll_area)

    # Construction

    def build_drones_card(self) -> Card:
        card = Card(self, CALIBRATION_DRONES_TITLE)

        selection_layout = QHBoxLayout()
        flush_layout(selection_layout)
        for vehicle_id, vehicle_name in self.drone_names.items():
            drone_checkbox = QCheckBox(vehicle_name.upper(), self)
            drone_checkbox.setChecked(True)
            selection_layout.addWidget(drone_checkbox)
            self.drone_checkboxes[vehicle_id] = drone_checkbox
        selection_layout.addStretch()
        card.add_layout(selection_layout)

        card.add_widget(self.hint_label(CALIBRATION_DRONES_HINT))
        return card

    def build_steps_card(self) -> Card:
        card = Card(self, CALIBRATION_STEPS_TITLE)
        for step in CALIBRATION_STEPS:
            card.add_layout(self.build_step_layout(step))
        return card

    def build_step_layout(self, step: dict) -> QVBoxLayout:
        """One numbered measurement: what it is, what it needs, and its button."""
        step_layout = QVBoxLayout()
        flush_layout(step_layout)

        title_label = QLabel(step["title"], self)
        set_role(title_label, ROLE_HINT)
        step_layout.addWidget(title_label)

        step_layout.addWidget(self.hint_label(step["hint"].format(**step)))

        step_button = QPushButton(step["button"], self)
        if "variant" in step:
            set_variant(step_button, step["variant"])
        step_button.clicked.connect(lambda: self.request_step(step))
        step_layout.addWidget(step_button)
        return step_layout

    def build_results_card(self) -> Card:
        card = Card(self, CALIBRATION_RESULTS_TITLE)

        self.results_table = QTableWidget(0, len(CALIBRATION_RESULTS_COLUMNS), self)
        self.results_table.setHorizontalHeaderLabels(CALIBRATION_RESULTS_COLUMNS)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setMinimumHeight(CALIBRATION_RESULTS_MIN_HEIGHT)
        # The name and the chip are as wide as their wording; the two columns
        # carrying sentences take what is left, or a reason is cut off mid-word.
        header = self.results_table.horizontalHeader()
        for column in (DRONE_COLUMN, STATUS_COLUMN):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        for column in (MEASURED_COLUMN, NOTE_COLUMN):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        card.add_widget(self.results_table, 1)

        self.results_empty_label = self.hint_label(CALIBRATION_RESULTS_EMPTY_TEXT)
        card.add_widget(self.results_empty_label)
        return card

    def hint_label(self, text: str) -> QLabel:
        hint = QLabel(text, self)
        set_role(hint, ROLE_HINT)
        hint.setWordWrap(True)
        self.hint_labels.append(hint)
        return hint

    def resizeEvent(self, event) -> None:
        """Give every wrapped hint the height its own text needs.

        A vertical layout asks a label how tall it is without telling it how
        wide it will be, and inside the cards that question never reaches the
        label at all, so a wrapped hint was drawn one line tall and cut off
        once the window came near its smallest width. These hints carry the
        propellers-on and propellers-off warnings, so they have to be readable
        whole at every width the window allows.

        The text is measured rather than the widget asked: a label answers with
        the height it has already been given, so setting that back on it only
        ever grows it, and the hints crept down the tab on every resize.
        """
        super().resizeEvent(event)
        for hint in self.hint_labels:
            hint.setMinimumHeight(wrapped_text_height(hint))

    # Asking for a measurement

    def selected_drone_ids(self) -> list[int]:
        return [
            vehicle_id
            for vehicle_id, drone_checkbox in self.drone_checkboxes.items()
            if drone_checkbox.isChecked()
        ]

    def request_step(self, step: dict) -> None:
        """Check the tick boxes, ask the operator when the step spins or flies,
        then hand the step to the main window."""
        drone_ids = self.selected_drone_ids()
        if not drone_ids:
            QMessageBox.warning(self, step["title"], CALIBRATION_NO_DRONES_TEXT)
            return
        if "confirm_question" in step and not self.operator_confirms(step):
            return
        self.calibration_requested.emit(step["name"], drone_ids)

    def operator_confirms(self, step: dict) -> bool:
        answer = QMessageBox.question(
            self,
            step["confirm_title"],
            step["confirm_question"].format(**step),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    # Answers

    def show_result(self, result: dict) -> None:
        """Add one drone's answer to the top of the table."""
        self.results_empty_label.setVisible(False)
        self.results_table.insertRow(NEWEST_ROW)
        drone_name = self.drone_names.get(
            result.get("drone_id"), CALIBRATION_UNKNOWN_DRONE_TEXT
        )
        note = result.get("reason") or result.get("note") or ""
        self.set_cell(DRONE_COLUMN, drone_name.upper())
        self.set_cell(MEASURED_COLUMN, measured_text(result))
        self.set_cell(NOTE_COLUMN, str(note))
        pill = StatusPill(self, str(result.get("status", "")), result_state(result))
        self.results_table.setCellWidget(NEWEST_ROW, STATUS_COLUMN, centered(pill))
        while self.results_table.rowCount() > CALIBRATION_RESULTS_MAX_ROWS:
            self.results_table.removeRow(self.results_table.rowCount() - 1)

    def set_cell(self, column: int, text: str) -> None:
        self.results_table.setItem(NEWEST_ROW, column, QTableWidgetItem(text))


def wrapped_text_height(hint: QLabel) -> int:
    """How tall this label's text is once wrapped to the width it has now.

    Measured off the font rather than off the widget, so the answer does not
    depend on how tall the label happens to be at the time.
    """
    text_width = hint.contentsRect().width()
    if text_width <= 0:
        return 0
    metrics = QFontMetrics(hint.font())
    text_rect = metrics.boundingRect(
        0, 0, text_width, 0, Qt.TextFlag.TextWordWrap, hint.text()
    )
    padding = hint.height() - hint.contentsRect().height()
    return text_rect.height() + padding


def centered(pill: StatusPill) -> QWidget:
    """Hold a chip in a table cell without letting it fill it.

    Dropped straight into a cell, a pill is stretched to the whole column and
    reads as a block of colour rather than as a chip.
    """
    holder = QWidget()
    holder_layout = QHBoxLayout(holder)
    flush_layout(holder_layout)
    holder_layout.addStretch()
    holder_layout.addWidget(pill)
    holder_layout.addStretch()
    return holder


def result_state(result: dict) -> str:
    """A status nobody listed is treated as a failure, so it still stands out."""
    return CALIBRATION_STATUS_STATES.get(result.get("status"), STATE_CRITICAL)


def measured_text(result: dict) -> str:
    """The numbers in an answer, named. A result only carries the keys its own
    measurement produced, so this picks out whichever of them turned up."""
    parts = [
        label.format(value=result[key])
        for key, label in CALIBRATION_MEASURED_LABELS.items()
        if key in result
    ]
    return ", ".join(parts)
