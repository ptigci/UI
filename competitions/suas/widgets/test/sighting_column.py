"""What the model saw, newest first.

The list is what tells a detector that is scoring well from one that is scoring
often. Newest at the top because the bench is usually holding something in front
of the camera and wants to see what came of it, and capped at the limit in the
config because a detector left running over a lunch break will otherwise fill
the machine with thumbnails nobody will ever scroll back to.

Every sighting gets a row, including one whose crop would not decode. The score
and the place are what the page is here for, and a row with no picture on it
beats a sighting the operator never hears about.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from competitions.suas.config import TEST_DETECTION_TEXT, TEST_LAYOUT
from theme import flush_layout, set_role
from theme.tokens import ROLE_HINT, SPACE_MD, SPACE_XS
from widgets import Card

NEWEST_ROW = 0

CROP_WIDTH = TEST_LAYOUT["sighting_crop_width"]
CROP_HEIGHT = TEST_LAYOUT["sighting_crop_height"]


class SightingColumn(Card):
    """A scrolling list of sightings, the newest at the top."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TEST_DETECTION_TEXT["sighting_title"])

        self.waiting_label = QLabel(TEST_DETECTION_TEXT["sighting_waiting_text"], self)
        set_role(self.waiting_label, ROLE_HINT)

        self.rows = QWidget(self)
        self.rows_layout = QVBoxLayout(self.rows)
        flush_layout(self.rows_layout, SPACE_MD)
        # The rows sit at the top of the scroll instead of spreading down it.
        self.rows_layout.addStretch()

        scroll_area = QScrollArea(self)
        scroll_area.setWidget(self.rows)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(TEST_LAYOUT["monitor_minimum_height"])

        self.add_widget(self.waiting_label)
        self.add_widget(scroll_area)

    def add_sighting(self, pixmap: QPixmap, sighting) -> None:
        """Put one sighting at the top and drop the oldest once the list is full."""
        self.rows_layout.insertWidget(NEWEST_ROW, self.build_row(pixmap, sighting))
        self.waiting_label.setVisible(False)
        while self.sighting_count() > TEST_DETECTION_TEXT["sighting_limit"]:
            self.remove_row(self.sighting_count() - 1)

    def clear(self) -> None:
        while self.sighting_count() > 0:
            self.remove_row(self.sighting_count() - 1)
        self.waiting_label.setVisible(True)

    def sighting_count(self) -> int:
        """The rows, not counting the stretch that holds them at the top."""
        return self.rows_layout.count() - 1

    def remove_row(self, row_index: int) -> None:
        row = self.rows_layout.takeAt(row_index)
        row.widget().deleteLater()

    def build_row(self, pixmap: QPixmap, sighting) -> QWidget:
        """The crop on the left, what it was and where it was on the right."""
        row = QWidget(self.rows)
        row_layout = QHBoxLayout(row)
        flush_layout(row_layout, SPACE_MD)
        row_layout.addWidget(build_crop(pixmap, row))
        row_layout.addWidget(build_details(sighting, row))
        row_layout.addStretch()
        return row


def build_crop(pixmap: QPixmap, parent) -> QLabel:
    """The picture, or the words that stand in for one that would not decode."""
    crop_label = QLabel(parent)
    crop_label.setFixedSize(CROP_WIDTH, CROP_HEIGHT)
    crop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    crop_label.setWordWrap(True)

    if pixmap.isNull():
        crop_label.setText(TEST_DETECTION_TEXT["sighting_no_picture_text"])
        set_role(crop_label, ROLE_HINT)
        return crop_label

    crop_label.setPixmap(
        pixmap.scaled(
            CROP_WIDTH,
            CROP_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )
    return crop_label


def build_details(sighting, parent) -> QWidget:
    """What the model called it and how sure it was, over where it put it."""
    details = QWidget(parent)
    details_layout = QVBoxLayout(details)
    flush_layout(details_layout, SPACE_XS)

    label = QLabel(
        TEST_DETECTION_TEXT["sighting_label_format"].format(
            target_class=sighting.target_class, confidence=sighting.confidence
        ),
        details,
    )
    place_label = QLabel(place_text(sighting), details)
    set_role(place_label, ROLE_HINT)
    place_label.setWordWrap(True)

    details_layout.addWidget(label)
    details_layout.addWidget(place_label)
    details_layout.addStretch()
    return details


def place_text(sighting) -> str:
    """Where the projection put it, or why it put it nowhere."""
    position = sighting.position()
    if position is None:
        return TEST_DETECTION_TEXT["sighting_no_place_text"]
    return TEST_DETECTION_TEXT["sighting_place_format"].format(
        latitude=position[0], longitude=position[1]
    )
