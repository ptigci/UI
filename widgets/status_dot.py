"""A lit dot: the smallest way to show that something is alive or is not.

It sits next to a label rather than replacing one — colour on its own is not a
status. The dot breathes while a state is critical, because a red that never
changes stops being noticed after twenty minutes in front of the screen.
"""

from PyQt6.QtCore import QPropertyAnimation, QRectF, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from theme.tokens import (
    DOT_HALO,
    DOT_SIZE,
    PULSE_DEPTH,
    PULSE_DURATION,
    STATE_COLORS,
    STATE_CRITICAL,
    STATE_IDLE,
    STATE_STALE,
)

# The two states worth a moving light. Anything else is read, not noticed.
ALARM_STATES = (STATE_CRITICAL, STATE_STALE)

FULL_BRIGHTNESS = 1.0
HALO_ALPHA = 0.22
ALPHA_CHANNEL_MAX = 255

PULSE_MIDPOINT = 0.5
PULSE_FOREVER = -1


class StatusDot(QWidget):

    def __init__(self, state: str = STATE_IDLE, parent=None) -> None:
        super().__init__(parent)
        self.dot_state = None
        self.brightness_value = FULL_BRIGHTNESS
        self.setFixedSize(DOT_SIZE + DOT_HALO * 2, DOT_SIZE + DOT_HALO * 2)

        self.pulse = QPropertyAnimation(self, b"brightness", self)
        self.pulse.setDuration(PULSE_DURATION)
        self.pulse.setLoopCount(PULSE_FOREVER)
        self.pulse.setKeyValueAt(0.0, FULL_BRIGHTNESS)
        self.pulse.setKeyValueAt(PULSE_MIDPOINT, PULSE_DEPTH)
        self.pulse.setKeyValueAt(1.0, FULL_BRIGHTNESS)

        self.set_state(state)

    def set_state(self, state: str) -> None:
        # Guarded: this is called from the same refresh that redraws telemetry,
        # and restarting the pulse every tick would leave it standing still.
        if state == self.dot_state:
            return
        self.dot_state = state
        if state in ALARM_STATES:
            self.pulse.start()
        else:
            self.pulse.stop()
            self.set_brightness(FULL_BRIGHTNESS)
        self.update()

    def get_brightness(self) -> float:
        return self.brightness_value

    def set_brightness(self, brightness: float) -> None:
        self.brightness_value = brightness
        self.update()

    brightness = pyqtProperty(float, get_brightness, set_brightness)

    def paintEvent(self, event) -> None:
        color = QColor(STATE_COLORS.get(self.dot_state, STATE_COLORS[STATE_IDLE]))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        halo_color = QColor(color)
        halo_color.setAlpha(round(HALO_ALPHA * self.brightness_value * ALPHA_CHANNEL_MAX))
        painter.setBrush(halo_color)
        painter.drawEllipse(QRectF(self.rect()))

        core_color = QColor(color)
        core_color.setAlpha(round(self.brightness_value * ALPHA_CHANNEL_MAX))
        core_area = QRectF(self.rect()).adjusted(DOT_HALO, DOT_HALO, -DOT_HALO, -DOT_HALO)
        painter.setBrush(core_color)
        painter.drawEllipse(core_area)
