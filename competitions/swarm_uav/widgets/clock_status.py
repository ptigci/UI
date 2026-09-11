"""Label that shows what is steering a drone clock."""

from PyQt6.QtWidgets import QLabel

from competitions.swarm_uav.config import (
    CLOCK_NO_SYNC_TEXT,
    CLOCK_PEER_TEXT,
    CLOCK_SOURCE_PEER,
    CLOCK_SOURCE_PPS,
    CLOCK_SOURCE_SWARM,
    CLOCK_SWARM_TEXT,
    CLOCK_SYNCED_TEXT,
    CLOCK_WAITING_TEXT,
)
from theme import set_role, set_state
from theme.tokens import (
    ROLE_READOUT,
    STATE_CAUTION,
    STATE_IDLE,
    STATE_OK,
    STATE_STALE,
)


class ClockStatusLabel(QLabel):
    """Shows the clock source reported on the drone's clock topic.

    Green is a live pulse of the drone's own. Yellow is a drone flying on
    somebody else's clock: either chrony following a sibling that still has a
    pulse, or the drone reading the swarm's time off the mesh beacons because
    nothing is steering its own. Both are close enough to fly barriers on, and
    the operator still needs to see that the GPS behind them is down. Anything
    else is NO SYNC, including a companion clock that merely happens to read
    close to right. Uses the shared state vocabulary, so it agrees with every
    other health indicator in the application about what green and red mean.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        set_role(self, ROLE_READOUT)
        self.reset()

    def reset(self) -> None:
        """Back to waiting: nothing has been heard from this clock yet."""
        self.apply(CLOCK_WAITING_TEXT, STATE_IDLE)

    def show_status(self, source: str, error_ms: float | None) -> None:
        if source == CLOCK_SOURCE_PPS:
            self.apply(self.with_error(CLOCK_SYNCED_TEXT, error_ms), STATE_OK)
        elif source == CLOCK_SOURCE_PEER:
            self.apply(self.with_error(CLOCK_PEER_TEXT, error_ms), STATE_CAUTION)
        elif source == CLOCK_SOURCE_SWARM:
            self.apply(self.with_error(CLOCK_SWARM_TEXT, error_ms), STATE_CAUTION)
        else:
            self.apply(CLOCK_NO_SYNC_TEXT, STATE_STALE)

    @staticmethod
    def with_error(text: str, error_ms: float | None) -> str:
        if error_ms is None:
            return text
        return f"{text} ({error_ms:g} ms)"

    def apply(self, text: str, state: str) -> None:
        self.setText(text)
        set_state(self, state)
