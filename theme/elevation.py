"""Drop shadows for the few things that genuinely float.

On a dark interface elevation is read from the surface colour first — a card is
lighter than the page behind it — so the shadow is a finishing touch, not the
mechanism. It is switchable from config/theme.toml because a graphics effect
costs a repaint on every frame, and the map redraws with every telemetry
message.
"""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

from theme.tokens import (
    SHADOW_ALPHA,
    SHADOW_BLUR,
    SHADOW_ENABLED,
    SHADOW_OFFSET_Y,
)

SHADOW_COLOR = "#000000"
NO_HORIZONTAL_OFFSET = 0
ALPHA_CHANNEL_MAX = 255


def apply_shadow(
    widget,
    blur: int = SHADOW_BLUR,
    offset_y: int = SHADOW_OFFSET_Y,
    alpha: float = SHADOW_ALPHA,
) -> QGraphicsDropShadowEffect | None:
    """Give the widget a shadow and hand it back, or None when shadows are off."""
    if not SHADOW_ENABLED:
        return None
    effect = QGraphicsDropShadowEffect(widget)
    set_shadow_strength(effect, blur, offset_y, alpha)
    widget.setGraphicsEffect(effect)
    return effect


def set_shadow_strength(
    effect: QGraphicsDropShadowEffect, blur: int, offset_y: int, alpha: float
) -> None:
    """Used by the hover animation to grow and settle a shadow."""
    effect.setBlurRadius(blur)
    effect.setOffset(NO_HORIZONTAL_OFFSET, offset_y)
    shadow_color = QColor(SHADOW_COLOR)
    shadow_color.setAlpha(round(alpha * ALPHA_CHANNEL_MAX))
    effect.setColor(shadow_color)
