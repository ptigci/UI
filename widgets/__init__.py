"""The shared components every competition builds its screens from.

None of these know which competition they are in. A competition-specific need
either generalises into one of them, or it stays in that competition's folder —
it never becomes a flag here.
"""

from widgets.camera_view import CameraView
from widgets.card import Card
from widgets.connection_status import ConnectionStatusLabel
from widgets.readout import Readout
from widgets.status_dot import StatusDot
from widgets.status_pill import StatusPill
from widgets.terminal_view import TerminalView

__all__ = [
    "CameraView",
    "Card",
    "ConnectionStatusLabel",
    "Readout",
    "StatusDot",
    "StatusPill",
    "TerminalView",
]
