"""Panel showing the latest decoded QR payload.

The spec requires the decoded QR content to be visible at the ground
station at least once per mission; this panel renders the payload the
ground station forwarded, together with the QR id, the decoding drone and
a timestamp so the referees can verify it. It sits in the swarm tab's
camera grid as an extra output; the grid header carries its title.
"""

import json
from datetime import datetime

from PyQt6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from config import TERMINAL_TIME_FORMAT
from competitions.swarm_uav.config import QR_NO_DATA_TEXT
from theme import flush_layout, set_role
from theme.tokens import ROLE_READOUT


class QRContentPanel(QWidget):
    """Read-only view of the most recent QR payload."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        panel_layout = QVBoxLayout(self)
        flush_layout(panel_layout)

        self.meta_label = QLabel(QR_NO_DATA_TEXT, self)
        set_role(self.meta_label, ROLE_READOUT)
        panel_layout.addWidget(self.meta_label)

        self.content_view = QTextEdit(self)
        self.content_view.setReadOnly(True)
        panel_layout.addWidget(self.content_view)

    def show_qr(self, qr_id, payload, source_drone) -> None:
        """Render a decoded QR payload with its origin and receive time."""
        received_at = datetime.now().strftime(TERMINAL_TIME_FORMAT)
        self.meta_label.setText(
            f"QR {qr_id} | drone {source_drone} | {received_at}"
        )
        self.content_view.setPlainText(json.dumps(payload, indent=2))
