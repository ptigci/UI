"""The big presses on this screen: one click each, at a size a glove can hit.

RTL, TERMINATE, the two survey presses and the delivery steps used to be held
down for a second and a half with a bar filling underneath them. That is gone.
Mission Time scores every second (3.1.2), and outdoors on a trackpad a hold
that slips reads as a control that does not work — which is the last thing the
operator should be wondering about while reaching for TERMINATE.

Nothing is lost by dropping it, because the hold was never what made these
commands safe. None of them is believed because it was pressed: the panel says
SENT, and only says ACKNOWLEDGED once the autopilot or the aircraft comes back
in the state that was asked for. What keeps a press from being made by mistake
is where it sits — TERMINATE is nobody's neighbour, and a button that cannot
work right now is disabled rather than waiting to be held.
"""

from PyQt6.QtWidgets import QPushButton

from theme import set_scale, set_variant
from theme.tokens import SCALE_LARGE


def command_button(text: str, variant: str, parent=None) -> QPushButton:
    """A mission control: one press, and big enough to be certain about."""
    button = QPushButton(text, parent)
    set_variant(button, variant)
    set_scale(button, SCALE_LARGE)
    return button
