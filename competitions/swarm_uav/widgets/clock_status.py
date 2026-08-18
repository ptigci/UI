"""Label that shows whether a drone's PPS clock is disciplined by chrony."""

from PyQt6.QtWidgets import QLabel

from competitions.swarm_uav.config import (
    CLOCK_NO_SYNC_TEXT,
    CLOCK_SYNCED_TEXT,
    CLOCK_WAITING_TEXT,
)
from theme import set_role, set_state
from theme.tokens import ROLE_READOUT, STATE_IDLE, STATE_OK, STATE_STALE


class ClockStatusLabel(QLabel):
    """Shows the clock sync state reported on the drone's clock topic.

    Uses the shared state vocabulary, so it agrees with every other health
    indicator in the application about what green and red mean.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        set_role(self, ROLE_READOUT)
        self.apply(CLOCK_WAITING_TEXT, STATE_IDLE)

    def show_status(self, disciplined: bool, error_ms: float | None) -> None:
        if not disciplined:
            self.apply(CLOCK_NO_SYNC_TEXT, STATE_STALE)
            return
        if error_ms is None:
            self.apply(CLOCK_SYNCED_TEXT, STATE_OK)
        else:
            self.apply(f"{CLOCK_SYNCED_TEXT} ({error_ms:g} ms)", STATE_OK)

    def apply(self, text: str, state: str) -> None:
        self.setText(text)
        set_state(self, state)
