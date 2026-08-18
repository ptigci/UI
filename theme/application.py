"""Puts the theme onto the QApplication, once, before any window is built.

Three things happen here and they all have to happen together. Fusion is chosen
because the native Windows style draws several controls itself and ignores
large parts of a stylesheet. The palette covers what a stylesheet cannot reach —
text cursors, selection in native dialogs, disabled text. The stylesheet does
everything else.
"""

from PyQt6.QtGui import QColor, QPalette

from theme.fonts import ui_font
from theme.stylesheet import build_stylesheet
from theme.tokens import (
    ACCENT,
    ON_ACCENT,
    SURFACE_BASE,
    SURFACE_CARD,
    SURFACE_RAISED,
    SURFACE_SUNKEN,
    TEXT_DISABLED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

BASE_STYLE = "Fusion"

# The roles Qt greys out by itself when a widget is disabled.
TEXT_ROLES = (
    QPalette.ColorRole.WindowText,
    QPalette.ColorRole.Text,
    QPalette.ColorRole.ButtonText,
)


def apply_theme(application) -> None:
    application.setStyle(BASE_STYLE)
    application.setFont(ui_font())
    application.setPalette(build_palette())
    application.setStyleSheet(build_stylesheet())


def build_palette() -> QPalette:
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: SURFACE_BASE,
        QPalette.ColorRole.WindowText: TEXT_PRIMARY,
        QPalette.ColorRole.Base: SURFACE_SUNKEN,
        QPalette.ColorRole.AlternateBase: SURFACE_CARD,
        QPalette.ColorRole.Text: TEXT_PRIMARY,
        QPalette.ColorRole.Button: SURFACE_RAISED,
        QPalette.ColorRole.ButtonText: TEXT_PRIMARY,
        QPalette.ColorRole.ToolTipBase: SURFACE_RAISED,
        QPalette.ColorRole.ToolTipText: TEXT_PRIMARY,
        QPalette.ColorRole.PlaceholderText: TEXT_SECONDARY,
        QPalette.ColorRole.Highlight: ACCENT,
        QPalette.ColorRole.HighlightedText: ON_ACCENT,
        QPalette.ColorRole.Link: ACCENT,
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))

    for role in TEXT_ROLES:
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(TEXT_DISABLED))
    return palette
