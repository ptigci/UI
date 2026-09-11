"""Panel showing every decoded QR, one tab each.

The spec requires the decoded QR content to be visible at the ground
station at least once per mission; this panel renders what the ground
station forwarded — the full text the reading drone decoded, or the parsed
slice until that arrives — with the QR id, the decoding drone and a
timestamp so the referees can verify it. A QR carries its tasks as JSON on
one long line, so it is laid out over several lines here: the whole point is
that a referee, and the operator, can read it. Every QR gets a tab in the row
above the text, the newest decode comes to the front, and a QR decoded
again refreshes its own tab. It sits in the swarm tab's camera grid as an
extra output; the grid header carries its title.
"""

import json
from datetime import datetime

from PyQt6.QtWidgets import QLabel, QTabBar, QTextEdit, QVBoxLayout, QWidget

from config import TERMINAL_TIME_FORMAT
from competitions.swarm_uav.config import (
    QR_FREE_SCAN_TAB_LABEL,
    QR_INDENT_SPACES,
    QR_NO_DATA_TEXT,
    QR_TAB_LABEL,
)
from theme import flush_layout, set_role
from theme.tokens import ROLE_READOUT

FREE_SCAN_KEY = "free"


def readable(payload) -> str:
    """The decoded QR laid out over several lines.

    A drone sends the QR text exactly as it read it, which is one long line
    of JSON that runs off the side of the panel. Anything that parses as JSON
    is laid out; anything else is shown as it came, because a QR that is not
    JSON is still worth seeing.
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return payload
    return json.dumps(payload, indent=QR_INDENT_SPACES, ensure_ascii=False)


class QRContentPanel(QWidget):
    """Read-only view of the decoded QRs, the latest one in front."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        panel_layout = QVBoxLayout(self)
        flush_layout(panel_layout)

        self.tabs = QTabBar(self)
        self.tabs.currentChanged.connect(self.show_tab)
        panel_layout.addWidget(self.tabs)

        self.meta_label = QLabel(QR_NO_DATA_TEXT, self)
        set_role(self.meta_label, ROLE_READOUT)
        panel_layout.addWidget(self.meta_label)

        self.content_view = QTextEdit(self)
        self.content_view.setReadOnly(True)
        panel_layout.addWidget(self.content_view)

        self.entries = {}   # tab key -> (meta line, content)
        self.tab_keys = []  # tab index -> tab key

    def show_qr(self, qr_id, payload, source_drone) -> None:
        """Store a decoded QR under its tab and bring that tab to the front."""
        received_at = datetime.now().strftime(TERMINAL_TIME_FORMAT)
        if qr_id is None:
            key = FREE_SCAN_KEY
            label = QR_FREE_SCAN_TAB_LABEL
        else:
            key = f"qr{qr_id}"
            label = QR_TAB_LABEL.format(qr_id=qr_id)
        content = readable(payload)
        self.entries[key] = (f"{label} | drone {source_drone} | {received_at}", content)
        if key not in self.tab_keys:
            self.tab_keys.append(key)
            self.tabs.addTab(label)
        index = self.tab_keys.index(key)
        if self.tabs.currentIndex() == index:
            self.show_tab(index)
        else:
            self.tabs.setCurrentIndex(index)

    def show_tab(self, index: int) -> None:
        """Render the QR behind the selected tab."""
        if index < 0 or index >= len(self.tab_keys):
            return
        meta_line, content = self.entries[self.tab_keys[index]]
        self.meta_label.setText(meta_line)
        self.content_view.setPlainText(content)

    def clear_qr(self) -> None:
        """Drop every QR on screen, back to the empty panel."""
        self.entries.clear()
        self.tab_keys.clear()
        while self.tabs.count():
            self.tabs.removeTab(0)
        self.meta_label.setText(QR_NO_DATA_TEXT)
        self.content_view.clear()
