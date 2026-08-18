"""The card: the box every group of related information lives in.

Nothing in the interface is placed straight onto the window background. A panel
is a card, a readout cluster is a card, a dialog's contents are a card. They all
get the same padding, the same corner radius and the same rail down the left
edge, so a screen the operator has never seen still parses the same way.

    card = Card(self, "LINK HEALTH")
    card.add_widget(link_table)
    card.set_state(STATE_CRITICAL)   # the rail turns red, nothing moves

The parent comes first so the class can also be promoted in a .ui file.
"""

from PyQt6.QtCore import QEvent, pyqtProperty
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from theme.animation import animate
from theme.elevation import apply_shadow, set_shadow_strength
from theme.fonts import ui_font
from theme.state import set_role, set_state, set_surface
from theme.tokens import (
    AS_CARD,
    DURATION_FAST,
    FONT_SIZE_CAPTION,
    FONT_WEIGHT_BOLD,
    ROLE_HEADING,
    SHADOW_ALPHA,
    SHADOW_BLUR,
    SHADOW_HOVER_ALPHA,
    SHADOW_HOVER_BLUR,
    SHADOW_HOVER_OFFSET_Y,
    SHADOW_OFFSET_Y,
    SPACE_LG,
    SPACE_MD,
    TRACKING_EYEBROW,
)

AT_REST = 0.0
FULLY_RAISED = 1.0


class Card(QFrame):
    """A titled panel. The title is optional; the padding never is."""

    def __init__(self, parent=None, title: str = "") -> None:
        super().__init__(parent)
        set_surface(self, AS_CARD)

        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        self.card_layout.setSpacing(SPACE_MD)

        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(SPACE_MD)

        self.heading_label = QLabel(self)
        set_role(self.heading_label, ROLE_HEADING)
        # A heading takes the height of its text and no more, otherwise a card
        # with room to spare shares that room with its own title.
        self.heading_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        # Qt ignores letter-spacing in a stylesheet, so the wide heading
        # tracking is set on the font here.
        self.heading_label.setFont(
            ui_font(FONT_SIZE_CAPTION, FONT_WEIGHT_BOLD, TRACKING_EYEBROW)
        )
        self.header_layout.addWidget(self.heading_label)
        self.header_layout.addStretch()
        self.card_layout.addLayout(self.header_layout)

        self.set_title(title)

        self.shadow = apply_shadow(self)
        self.raised_amount = AT_REST

    # Contents

    def add_widget(self, widget, stretch: int = 0):
        self.card_layout.addWidget(widget, stretch)
        return widget

    def add_layout(self, layout, stretch: int = 0):
        self.card_layout.addLayout(layout, stretch)
        return layout

    def add_header_widget(self, widget):
        """Sits at the right-hand end of the title row — a count, a chip, a toggle."""
        self.header_layout.addWidget(widget)
        return widget

    def add_stretch(self) -> None:
        self.card_layout.addStretch()

    # Appearance

    def set_title(self, title: str) -> None:
        self.heading_label.setText(title.upper())
        self.heading_label.setVisible(bool(title))

    def set_state(self, state: str) -> None:
        """Colour the rail. The card's own geometry never changes with state."""
        set_state(self, state)

    # Hover

    def get_raised(self) -> float:
        return self.raised_amount

    def set_raised(self, amount: float) -> None:
        self.raised_amount = amount
        if self.shadow is None:
            return
        set_shadow_strength(
            self.shadow,
            round(SHADOW_BLUR + (SHADOW_HOVER_BLUR - SHADOW_BLUR) * amount),
            round(SHADOW_OFFSET_Y + (SHADOW_HOVER_OFFSET_Y - SHADOW_OFFSET_Y) * amount),
            SHADOW_ALPHA + (SHADOW_HOVER_ALPHA - SHADOW_ALPHA) * amount,
        )

    raised = pyqtProperty(float, get_raised, set_raised)

    def enterEvent(self, event: QEvent) -> None:
        super().enterEvent(event)
        animate(self, "raised", self.raised_amount, FULLY_RAISED, DURATION_FAST)

    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        animate(self, "raised", self.raised_amount, AT_REST, DURATION_FAST)
