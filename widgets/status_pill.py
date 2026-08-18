"""A small filled chip that says a status in words.

Used wherever a colour alone would not be enough — AUTONOMY HELD, LINK DOWN,
3 WAITING. The wording is the caller's; the colour comes from the state.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QSizePolicy

from theme.state import set_role, set_state
from theme.tokens import ROLE_PILL, STATE_IDLE


class StatusPill(QLabel):

    def __init__(self, parent=None, text: str = "", state: str = STATE_IDLE) -> None:
        super().__init__(text.upper(), parent)
        set_role(self, ROLE_PILL)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # A chip is the size of its wording. In a tall bar an expanding pill
        # becomes a coloured block the height of the bar.
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.set_state(state)

    def set_text(self, text: str) -> None:
        self.setText(text.upper())

    def set_state(self, state: str) -> None:
        set_state(self, state)

    def show_status(self, text: str, state: str) -> None:
        """The usual call: the wording and the colour change together."""
        self.set_text(text)
        self.set_state(state)
