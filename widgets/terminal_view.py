"""Read-only log console used by every panel."""

import html
import re

from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QTextEdit

from config import TERMINAL_MAX_LINES

# Only plain color names/hex codes are trusted into the HTML style
# attribute; a mesh-sourced color string is otherwise untrusted input.
VALID_COLOR_PATTERN = re.compile(r"^#?[a-zA-Z0-9]+$")


class TerminalView(QTextEdit):
    """Used as a promoted QTextEdit in the .ui files."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        # cap the history so long sessions do not grow memory forever
        self.document().setMaximumBlockCount(TERMINAL_MAX_LINES)

    def append_line(self, text: str, color: str | None = None) -> None:
        if color and VALID_COLOR_PATTERN.match(color):
            self.append(f'<span style="color:{color};">{html.escape(text)}</span>')
        else:
            self.append(text)
        self.moveCursor(QTextCursor.MoveOperation.End)
