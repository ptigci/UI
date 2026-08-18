"""Label that shows how long ago a vehicle was last heard from."""

from PyQt6.QtWidgets import QLabel

from config import CONNECTION_NO_DATA_TEXT, CONNECTION_STALE_AFTER_MS
from theme.state import set_state
from theme.tokens import STATE_IDLE, STATE_OK, STATE_STALE


class ConnectionStatusLabel(QLabel):
    """Shows the age of the last received message in milliseconds.

    Used as a promoted QLabel in the .ui files, so the constructor must take
    only the parent argument. The colour comes from the shared state vocabulary
    — idle before anything has arrived, ok, then stale.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.prefix = ""
        self.set_age(None)

    def set_prefix(self, prefix: str) -> None:
        self.prefix = prefix

    def set_age(self, age_milliseconds: int | None) -> None:
        if age_milliseconds is None:
            age_text = CONNECTION_NO_DATA_TEXT
            state = STATE_IDLE
        else:
            age_text = f"{age_milliseconds} ms"
            if age_milliseconds > CONNECTION_STALE_AFTER_MS:
                state = STATE_STALE
            else:
                state = STATE_OK

        self.setText(self.prefix + age_text)
        set_state(self, state)
