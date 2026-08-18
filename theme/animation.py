"""The small amount of motion the interface uses.

Qt stylesheets cannot animate, so anything that moves does it through a
property animation. The rules are the same everywhere: one easing curve, three
durations, and nothing moves that the operator did not ask to move.
"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
from PyQt6.QtWidgets import QGraphicsOpacityEffect

from theme.tokens import DURATION_BASE

EASING = QEasingCurve.Type.OutCubic

TRANSPARENT = 0.0
OPAQUE = 1.0


def animate(target, property_name: str, start, end, duration: int = DURATION_BASE):
    """Run one property animation and keep it alive until it is done.

    The animation is parented to its target, and deletes itself on stop, so
    callers never have to hold a reference just to stop it being collected.
    """
    animation = QPropertyAnimation(target, property_name.encode(), target)
    animation.setDuration(duration)
    animation.setEasingCurve(EASING)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return animation


def fade_in(widget, duration: int = DURATION_BASE) -> None:
    """Bring a page or a window up rather than snapping it on.

    A widget carries one graphics effect at a time, so anything that already
    has a shadow is left alone; fade its container instead.
    """
    if widget.graphicsEffect() is not None:
        return

    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(TRANSPARENT)
    widget.setGraphicsEffect(effect)

    animation = animate(effect, "opacity", TRANSPARENT, OPAQUE, duration)
    # Drop the effect once it has served its purpose: leaving it in place makes
    # every later repaint go through the effect pipeline for nothing.
    animation.finished.connect(lambda: widget.setGraphicsEffect(None))
