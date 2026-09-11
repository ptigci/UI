"""Where the objects really are, typed in by hand, with the error beside each.

These points never leave this laptop. Nobody knows where the mannequin really is
except whoever walked out and put it there, so the aircraft cannot be asked and
must not be told — a detector marked against a number it was given would pass
every time. The error is worked out on the ground, from the sightings that came
down the link.

That error is the whole reason for the page. A delivery lands on where the
aircraft thinks the target is, so the metres between that and where it actually
is are the difference between a hit and a miss, and nothing else on this ground
station measures them.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from competitions.suas.config import TEST_DETECTION_TEXT, TEST_LAYOUT
from competitions.suas.widgets.command_button import command_button
from theme import flush_layout, set_role, set_variant
from theme.tokens import (
    ROLE_HINT,
    ROLE_READOUT_LABEL,
    SPACE_SM,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
)
from widgets import Card

CLASS_COLUMN = 0
LATITUDE_COLUMN = 1
LONGITUDE_COLUMN = 2
ERROR_COLUMN = 3
REMOVE_COLUMN = 4

COORDINATE_DECIMALS = TEST_DETECTION_TEXT["coordinate_decimals"]


class TruthPointTable(Card):
    """The points somebody measured, and how far off the detector was from each."""

    truth_point_added = pyqtSignal(str, float, float)
    truth_point_removed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TEST_DETECTION_TEXT["truth_title"])

        hint_label = QLabel(TEST_DETECTION_TEXT["truth_hint_text"], self)
        set_role(hint_label, ROLE_HINT)
        hint_label.setWordWrap(True)

        self.empty_label = QLabel(TEST_DETECTION_TEXT["truth_empty_text"], self)
        set_role(self.empty_label, ROLE_HINT)

        self.add_widget(hint_label)
        self.add_layout(self.build_inputs())
        self.add_widget(self.empty_label)
        self.add_widget(self.build_table())

    def build_inputs(self) -> QHBoxLayout:
        """The class and the two coordinates, and the press that takes them."""
        self.class_input = QLineEdit(self)
        self.latitude_input = coordinate_input(
            TEST_DETECTION_TEXT["latitude_minimum"],
            TEST_DETECTION_TEXT["latitude_maximum"],
            self,
        )
        self.longitude_input = coordinate_input(
            TEST_DETECTION_TEXT["longitude_minimum"],
            TEST_DETECTION_TEXT["longitude_maximum"],
            self,
        )

        self.add_button = command_button(
            TEST_DETECTION_TEXT["truth_add_text"], VARIANT_PRIMARY, self
        )
        self.add_button.clicked.connect(self.request_add)
        # A point with no class could never be matched to a sighting, so the
        # press is off until there is one rather than refusing afterwards.
        self.add_button.setEnabled(False)
        self.class_input.textChanged.connect(self.follow_class_input)

        inputs = QHBoxLayout()
        flush_layout(inputs, SPACE_SM)
        inputs.addWidget(caption(TEST_DETECTION_TEXT["truth_class_caption"], self))
        inputs.addWidget(self.class_input)
        inputs.addWidget(caption(TEST_DETECTION_TEXT["truth_latitude_caption"], self))
        inputs.addWidget(self.latitude_input)
        inputs.addWidget(caption(TEST_DETECTION_TEXT["truth_longitude_caption"], self))
        inputs.addWidget(self.longitude_input)
        inputs.addWidget(self.add_button)
        return inputs

    def build_table(self) -> QTableWidget:
        columns = TEST_DETECTION_TEXT["truth_columns"]
        self.table = QTableWidget(0, len(columns), self)
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(TEST_LAYOUT["monitor_minimum_height"])
        return self.table

    # The operator's side

    def follow_class_input(self, target_class: str) -> None:
        self.add_button.setEnabled(bool(target_class.strip()))

    def request_add(self) -> None:
        target_class = self.class_input.text().strip()
        if not target_class:
            return
        self.truth_point_added.emit(
            target_class, self.latitude_input.value(), self.longitude_input.value()
        )
        self.class_input.clear()

    def build_remove_button(self, point_id: str) -> QPushButton:
        remove_button = QPushButton(TEST_DETECTION_TEXT["truth_remove_text"], self.table)
        set_variant(remove_button, VARIANT_GHOST)
        remove_button.clicked.connect(lambda: self.truth_point_removed.emit(point_id))
        return remove_button

    # What the sightings came to

    def show_errors(self, truth_points) -> None:
        """Redraw every row: the points, and how far off each one was.

        Parameters:
            truth_points (TruthPointStore): the points and the sightings they
                are measured against.
        """
        self.empty_label.setVisible(not truth_points.points)
        self.table.setRowCount(len(truth_points.points))
        for row_index, point in enumerate(truth_points.points):
            metres, sighting_count = truth_points.error_for(point)
            self.fill_row(row_index, point, metres, sighting_count)

    def fill_row(self, row_index: int, point, metres, sighting_count: int) -> None:
        self.set_cell(row_index, CLASS_COLUMN, point.target_class)
        self.set_cell(row_index, LATITUDE_COLUMN, coordinate_text(point.latitude))
        self.set_cell(row_index, LONGITUDE_COLUMN, coordinate_text(point.longitude))
        self.set_cell(row_index, ERROR_COLUMN, error_text(metres, sighting_count))
        self.table.setCellWidget(
            row_index, REMOVE_COLUMN, self.build_remove_button(point.point_id)
        )

    def set_cell(self, row_index: int, column: int, text: str) -> None:
        self.table.setItem(row_index, column, QTableWidgetItem(text))


def caption(text: str, parent) -> QLabel:
    caption_label = QLabel(text, parent)
    set_role(caption_label, ROLE_READOUT_LABEL)
    return caption_label


def coordinate_input(minimum: float, maximum: float, parent) -> QDoubleSpinBox:
    """A degrees box that cannot be given a coordinate off the planet."""
    box = QDoubleSpinBox(parent)
    box.setDecimals(COORDINATE_DECIMALS)
    box.setRange(minimum, maximum)
    box.setSingleStep(TEST_DETECTION_TEXT["coordinate_step"])
    return box


def coordinate_text(degrees: float) -> str:
    return f"{degrees:.{COORDINATE_DECIMALS}f}"


def error_text(metres, sighting_count: int) -> str:
    """The metres and what they were measured from, or the line saying neither."""
    if metres is None:
        return TEST_DETECTION_TEXT["error_waiting_text"]
    return " ".join((
        TEST_DETECTION_TEXT["error_format"].format(metres=metres),
        TEST_DETECTION_TEXT["error_count_format"].format(count=sighting_count),
    ))
