"""A button that has to be held down, with the hold shown as it fills.

RTL drops the mission and TERMINATE drops the aircraft, so neither may fire on a
stray click. The obvious answer is a confirmation dialog, and we cannot have one:
rule 3.0.6 requires the map to stay visible to the judge at all times, and a
modal dialog covers it. Holding is the confirmation instead — it cannot happen by
accident, it needs no second window, and the fill shows how far along it is.

Releasing early cancels and resets. Nothing is sent until the hold completes.

The variant is passed in rather than a name: caution and danger are shared
button intents, and the fill bar takes its colour from the same one.
"""

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QProgressBar, QPushButton, QVBoxLayout, QWidget

from competitions.suas.config import (
    SAFETY_HOLD_PROGRESS_INTERVAL_MS,
    SAFETY_HOLD_TO_CONFIRM_MS,
)
from theme import flush_layout, set_scale, set_variant
from theme.tokens import SCALE_LARGE, SPACE_XS

PROGRESS_MINIMUM = 0
PROGRESS_MAXIMUM = 100


class HoldButton(QWidget):
    """Press and hold to fire; release early and nothing happens."""

    held = pyqtSignal()

    def __init__(self, text: str, variant: str, parent=None) -> None:
        super().__init__(parent)
        self.held_milliseconds = 0

        self.button = QPushButton(text, self)
        set_variant(self.button, variant)
        set_scale(self.button, SCALE_LARGE)
        self.button.pressed.connect(self.begin_hold)
        self.button.released.connect(self.cancel_hold)

        self.progress = QProgressBar(self)
        set_variant(self.progress, variant)
        self.progress.setRange(PROGRESS_MINIMUM, PROGRESS_MAXIMUM)
        self.progress.setValue(PROGRESS_MINIMUM)
        self.progress.setTextVisible(False)

        button_layout = QVBoxLayout(self)
        flush_layout(button_layout, SPACE_XS)
        button_layout.addWidget(self.button)
        button_layout.addWidget(self.progress)

        self.hold_timer = QTimer(self)
        self.hold_timer.setInterval(SAFETY_HOLD_PROGRESS_INTERVAL_MS)
        self.hold_timer.timeout.connect(self.advance_hold)

    def begin_hold(self) -> None:
        self.held_milliseconds = 0
        self.progress.setValue(PROGRESS_MINIMUM)
        self.hold_timer.start()

    def cancel_hold(self) -> None:
        self.hold_timer.stop()
        self.held_milliseconds = 0
        self.progress.setValue(PROGRESS_MINIMUM)

    def advance_hold(self) -> None:
        self.held_milliseconds += SAFETY_HOLD_PROGRESS_INTERVAL_MS
        fraction = self.held_milliseconds / SAFETY_HOLD_TO_CONFIRM_MS
        self.progress.setValue(int(min(fraction, 1.0) * PROGRESS_MAXIMUM))

        if self.held_milliseconds < SAFETY_HOLD_TO_CONFIRM_MS:
            return
        # Held long enough. Stop first, so a slow handler cannot fire it twice.
        self.hold_timer.stop()
        self.held.emit()

    def set_variant(self, variant: str) -> None:
        """Change the button's intent after it has been built.

        The camera's record button is one control that does two opposite
        things, and which one depends on what the camera is doing. Two buttons
        would mean one of them is always wrong to press.
        """
        set_variant(self.button, variant)
        set_variant(self.progress, variant)

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        if not enabled:
            self.cancel_hold()
