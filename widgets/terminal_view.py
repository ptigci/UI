"""Read-only log console used by every panel."""

import html
import re
from datetime import datetime

from PyQt6.QtGui import QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QTextEdit

from config import TERMINAL_MAX_LINES, TERMINAL_TIME_FORMAT

# Only plain color names/hex codes are trusted into the HTML style
# attribute; a mesh-sourced color string is otherwise untrusted input.
VALID_COLOR_PATTERN = re.compile(r"^#?[a-zA-Z0-9]+$")


def timestamped(text: str) -> str:
    """The form every terminal line takes: the time, then the message."""
    now = datetime.now()
    return f"{now.strftime(TERMINAL_TIME_FORMAT)}.{now.microsecond // 1000:03d} | {text}"


class TerminalView(QTextEdit):
    """Used as a promoted QTextEdit in the .ui files."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        # cap the history so long sessions do not grow memory forever
        self.document().setMaximumBlockCount(TERMINAL_MAX_LINES)

    def append_line(self, text: str, color: str | None = None) -> None:
        # Somebody reading an older part of the log keeps their place; the
        # view only follows new lines while it is already at the bottom.
        scroll_bar = self.verticalScrollBar()
        was_at_bottom = scroll_bar.value() == scroll_bar.maximum()
        if color and VALID_COLOR_PATTERN.match(color):
            self.append(f'<span style="color:{color};">{html.escape(text)}</span>')
        else:
            # A colored line leaves its color on the cursor, and every plain
            # line appended after it inherited it — one zone detection turned
            # the whole rest of the session red. Clearing the format hands the
            # line back to the stylesheet instead of naming a color here.
            self.setCurrentCharFormat(QTextCharFormat())
            self.append(text)
        if was_at_bottom:
            self.moveCursor(QTextCursor.MoveOperation.End)
