"""The operator's log under the map.

Plain sentences about what the mission did and what the operator decided. The
full detail goes to the session log on disk; this is what a human reads while
flying.
"""

from datetime import datetime

from config import TERMINAL_TIME_FORMAT
from theme.tokens import STATE_COLORS
from widgets import Card, TerminalView
from competitions.international_uav.config import LOG_PANEL_TITLE

MILLISECONDS_PER_SECOND = 1000


class LogPanel(Card):
    """Timestamped, read-only mission log."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent, LOG_PANEL_TITLE)

        self.terminal = TerminalView(self)
        self.add_widget(self.terminal)

    def append(self, message: str, state: str | None = None) -> None:
        """One line, in the colour of its state; no state is the plain text colour."""
        self.terminal.append_line(
            f"{self.timestamp()} | {message}", STATE_COLORS.get(state)
        )

    @staticmethod
    def timestamp() -> str:
        now = datetime.now()
        milliseconds = now.microsecond // MILLISECONDS_PER_SECOND
        return f"{now.strftime(TERMINAL_TIME_FORMAT)}.{milliseconds:03d}"
