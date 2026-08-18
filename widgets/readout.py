"""A captioned number.

Ground speed, altitude, elapsed time, distance to the boundary — the interface
is mostly this one thing repeated, so it is one widget. The caption sits above
the value in small wide type and the value is monospaced, which keeps a row of
readouts aligned and stops the digits jumping as they change.

    ground_speed = Readout("GROUND SPEED", SCALE_TITLE)
    ground_speed.set_value("42 kt")
    ground_speed.set_state(STATE_CAUTION)
"""

from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from theme.fonts import mono_font, ui_font
from theme.state import set_role, set_scale, set_state
from theme.tokens import (
    FONT_SIZE_DISPLAY,
    FONT_SIZE_MICRO,
    FONT_SIZE_TITLE,
    FONT_WEIGHT_BOLD,
    FONT_WEIGHT_SEMIBOLD,
    ROLE_READOUT,
    ROLE_READOUT_LABEL,
    SCALE_BODY,
    SCALE_DISPLAY,
    SCALE_TITLE,
    SPACE_XS,
    TRACKING_DISPLAY,
    TRACKING_EYEBROW,
)

EMPTY_VALUE = "-"

# The two sizes big enough that the stylesheet's font has to be restated here,
# because tracking can only be set on a QFont.
TRACKED_SIZES = {
    SCALE_DISPLAY: FONT_SIZE_DISPLAY,
    SCALE_TITLE: FONT_SIZE_TITLE,
}


class Readout(QWidget):
    """One caption, one value, and the state the value is in."""

    def __init__(self, caption: str, scale: str = SCALE_BODY, parent=None) -> None:
        super().__init__(parent)

        self.caption_label = QLabel(caption.upper(), self)
        set_role(self.caption_label, ROLE_READOUT_LABEL)
        self.caption_label.setFont(
            ui_font(FONT_SIZE_MICRO, FONT_WEIGHT_SEMIBOLD, TRACKING_EYEBROW)
        )

        self.value_label = QLabel(EMPTY_VALUE, self)
        set_role(self.value_label, ROLE_READOUT)

        readout_layout = QVBoxLayout(self)
        readout_layout.setContentsMargins(0, 0, 0, 0)
        readout_layout.setSpacing(SPACE_XS)
        readout_layout.addWidget(self.caption_label)
        readout_layout.addWidget(self.value_label)
        # Two lines of text and nothing else. Left to grow, a readout in a bar
        # spreads its caption and its value to opposite ends of the bar.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.set_scale(scale)

    def set_caption(self, caption: str) -> None:
        self.caption_label.setText(caption.upper())

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def set_state(self, state: str) -> None:
        set_state(self.value_label, state)

    def set_scale(self, scale: str) -> None:
        set_scale(self.value_label, scale)
        tracked_size = TRACKED_SIZES.get(scale)
        if tracked_size is None:
            return
        self.value_label.setFont(
            mono_font(tracked_size, FONT_WEIGHT_BOLD, TRACKING_DISPLAY)
        )
