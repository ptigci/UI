"""The autopilot's log under the map.

What the autopilot says in words, and the answer to every press on the FLIGHT
and CALIBRATION tabs, as plain timestamped lines. The full detail goes to the
session log on disk; this is what the operator reads while flying.
"""

from theme.tokens import STATE_COLORS
from widgets import Card, TerminalView, timestamped
from competitions.suas.config import LOG_PANEL_TITLE


class LogPanel(Card):
    """Timestamped, read-only autopilot log."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent, LOG_PANEL_TITLE)

        self.terminal = TerminalView(self)
        self.add_widget(self.terminal)

    def append(self, message: str, state: str | None = None) -> None:
        """One line, in the colour of its state; no state is the plain text colour."""
        self.terminal.append_line(timestamped(message), STATE_COLORS.get(state))
