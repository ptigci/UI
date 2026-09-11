"""Measuring one drone's HSV band on its own camera view.

The painted circles never change; the light on them does. This window shows
the live stream of one drone, the operator drags a box over the circle, and
the pixels inside it become the HSV band that drone flies with. Nothing is
computed for the swarm — each drone has its own lens and its own exposure, so
each is calibrated on what it can actually see.
"""

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from config import WINDOW_TITLE
from competitions.swarm_uav.config import (
    COLOR_BUTTON_TEXT,
    COLOR_CARD_TITLE,
    COLOR_HINT,
    COLOR_NAMES,
    COLOR_NO_COLOR_TEXT,
    COLOR_NO_SELECTION_TEXT,
    COLOR_WAITING_TEXT,
    COLOR_WINDOW_HEIGHT,
    COLOR_WINDOW_TITLE,
    COLOR_WINDOW_WIDTH,
)
from competitions.swarm_uav.controller.hsv_band import (
    band_text,
    bands_from_samples,
    joined_samples,
    sample_hsv,
)
from competitions.swarm_uav.widgets.frame_selector import FrameSelector
from theme import fade_in, flush_layout, set_role, set_variant, space_layout
from widgets.card import Card
from theme.tokens import (
    ROLE_HINT,
    ROLE_READOUT,
    SPACE_LG,
    SPACE_XL,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
)

logger = logging.getLogger(__name__)


class ColorCalibrationWindow(QDialog):
    """One drone, one color, one box drawn over the circle."""

    calibration_requested = pyqtSignal(str, object)
    white_balance_requested = pyqtSignal()

    def __init__(self, vehicle_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{WINDOW_TITLE} - {COLOR_WINDOW_TITLE}")
        self.resize(COLOR_WINDOW_WIDTH, COLOR_WINDOW_HEIGHT)
        # The pixels behind each colour's band, kept so ADD can measure a
        # second box into them. CALIBRATE throws them away and starts again.
        self.samples_taken = {}

        window_layout = QVBoxLayout(self)
        space_layout(window_layout, SPACE_XL, SPACE_LG)

        card = Card(self, f"{COLOR_CARD_TITLE} - {vehicle_name.upper()}")
        window_layout.addWidget(card)

        self.selector = FrameSelector(COLOR_WAITING_TEXT, self)
        card.add_widget(self.selector, stretch=1)

        hint_label = QLabel(COLOR_HINT, self)
        hint_label.setWordWrap(True)
        set_role(hint_label, ROLE_HINT)
        card.add_widget(hint_label)

        self.measured_label = QLabel(self)
        set_role(self.measured_label, ROLE_READOUT)
        card.add_widget(self.measured_label)

        card.add_layout(self.build_controls())

    def build_controls(self) -> QHBoxLayout:
        control_layout = QHBoxLayout()
        flush_layout(control_layout)

        self.color_picker = QComboBox(self)
        self.color_picker.addItems([color_name.upper() for color_name in COLOR_NAMES])
        control_layout.addWidget(self.color_picker)
        control_layout.addStretch()

        # Left of the measuring buttons, because it belongs before them: the
        # bands are measured through whatever balance the camera is holding.
        white_balance_button = QPushButton(COLOR_BUTTON_TEXT["white_balance"], self)
        set_variant(white_balance_button, VARIANT_GHOST)
        white_balance_button.clicked.connect(self.white_balance_requested)
        control_layout.addWidget(white_balance_button)

        clear_button = QPushButton(COLOR_BUTTON_TEXT["clear"], self)
        set_variant(clear_button, VARIANT_GHOST)
        clear_button.clicked.connect(self.selector.clear_selection)
        control_layout.addWidget(clear_button)

        add_button = QPushButton(COLOR_BUTTON_TEXT["add"], self)
        set_variant(add_button, VARIANT_GHOST)
        add_button.clicked.connect(lambda: self.send_calibration(True))
        control_layout.addWidget(add_button)

        send_button = QPushButton(COLOR_BUTTON_TEXT["calibrate"], self)
        set_variant(send_button, VARIANT_PRIMARY)
        send_button.clicked.connect(lambda: self.send_calibration(False))
        control_layout.addWidget(send_button)

        close_button = QPushButton(COLOR_BUTTON_TEXT["close"], self)
        close_button.clicked.connect(self.accept)
        control_layout.addWidget(close_button)
        return control_layout

    def show_frame(self, image) -> None:
        """Hand the window a live frame from the drone it was opened for."""
        self.selector.show_frame(image)

    def send_calibration(self, keep_earlier: bool) -> None:
        """Measure the box and send the band; the window stays open to redo it.

        With keep_earlier the pixels join whatever was already measured for
        this colour instead of replacing it. That is how one circle is taken
        in open sun and again under cloud: the band then spans both, and the
        drone keeps matching while the light moves between them.
        """
        selection = self.selector.selected_image_rect()
        if selection is None:
            QMessageBox.warning(self, COLOR_WINDOW_TITLE, COLOR_NO_SELECTION_TEXT)
            return

        color_name = COLOR_NAMES[self.color_picker.currentIndex()]
        samples = sample_hsv(self.selector.frame_image, selection)
        if keep_earlier:
            samples = joined_samples(self.samples_taken.get(color_name), samples)

        bands = bands_from_samples(*samples)
        if bands is None:
            QMessageBox.warning(self, COLOR_WINDOW_TITLE, COLOR_NO_COLOR_TEXT)
            return

        self.samples_taken[color_name] = samples
        self.measured_label.setText(f"{color_name}: {band_text(bands)}")
        logger.info(f"Color calibration measured for {color_name}: {bands}")
        self.calibration_requested.emit(color_name, bands)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        fade_in(self)
