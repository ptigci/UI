"""The two payload stations: what each carries, what it drops on, and whether
it is still aboard.

Thirty points per delivery are for dropping the right object on the right
target, and this is where the operator sees that pairing is what the aircraft
believes too. A spent station reads as spent for the rest of the flight; it
never rearms.
"""

from PyQt6.QtWidgets import QHBoxLayout

from competitions.suas.config import (
    PAYLOAD_PANEL_TITLE,
    PAYLOAD_STATION_FORMAT,
    PAYLOAD_WAITING_TEXT,
    STATION_STATE_SPENT,
)
from theme import flush_layout
from theme.tokens import SPACE_MD, STATE_NONE, STATE_OK
from widgets import Card, Readout


class PayloadPanel(Card):
    """One readout per station."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent, PAYLOAD_PANEL_TITLE)
        self.readouts: dict = {}
        self.row = QHBoxLayout()
        flush_layout(self.row, SPACE_MD)
        self.add_layout(self.row)
        self.placeholder = Readout(PAYLOAD_WAITING_TEXT, parent=self)
        self.row.addWidget(self.placeholder)

    def show_stations(self, payload_state) -> None:
        """Draw every station the aircraft reported."""
        if not payload_state.stations:
            return
        self.placeholder.setVisible(False)

        for station in payload_state.stations:
            readout = self.readouts.get(station.name)
            if readout is None:
                readout = Readout(station.name.upper(), parent=self)
                self.readouts[station.name] = readout
                self.row.addWidget(readout)
            readout.set_value(PAYLOAD_STATION_FORMAT.format(
                target_class=station.target_class, state=station.state,
            ))
            if station.state == STATION_STATE_SPENT:
                readout.set_state(STATE_OK)
            else:
                readout.set_state(STATE_NONE)
