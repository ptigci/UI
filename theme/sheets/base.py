"""The window itself, and the chrome Qt draws around the content.

Scrollbars, menus, tooltips and splitter handles are the parts nobody designs
and everybody sees. They are here so that every window gets them for free.
"""

from theme.tokens import (
    ACCENT,
    BORDER_HAIRLINE,
    BORDER_LINE,
    BORDER_LINE_STRONG,
    RADIUS_MD,
    RADIUS_SM,
    SCROLLBAR_WIDTH,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    SURFACE_BASE,
    SURFACE_OVERLAY,
    SURFACE_RAISED,
    SURFACE_SUNKEN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

# A scrollbar handle short enough to disappear is worse than no scrollbar.
SCROLLBAR_HANDLE_MINIMUM = 40
SCROLLBAR_HANDLE_INSET = 2


def base_sheet() -> str:
    handle_radius = (SCROLLBAR_WIDTH - SCROLLBAR_HANDLE_INSET * 2) // 2
    return f"""
QMainWindow, QDialog {{
    background-color: {SURFACE_BASE};
}}

QWidget#appSurface {{
    background-color: {SURFACE_BASE};
}}

QToolTip {{
    background-color: {SURFACE_OVERLAY};
    color: {TEXT_PRIMARY};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE_STRONG};
    border-radius: {RADIUS_SM}px;
    padding: {SPACE_XS}px {SPACE_SM}px;
}}

QStatusBar {{
    background-color: {SURFACE_SUNKEN};
    color: {TEXT_MUTED};
    border-top: {BORDER_HAIRLINE}px solid {BORDER_LINE};
}}
QStatusBar::item {{
    border: none;
}}

QSplitter::handle {{
    background-color: {BORDER_LINE};
}}
QSplitter::handle:horizontal {{
    width: {BORDER_HAIRLINE}px;
}}
QSplitter::handle:vertical {{
    height: {BORDER_HAIRLINE}px;
}}
QSplitter::handle:hover {{
    background-color: {ACCENT};
}}

/* A scroll area is a container, not a surface: whatever it holds provides the
   background, so it never paints its own. */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: {SCROLLBAR_WIDTH}px;
    margin: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: {SCROLLBAR_WIDTH}px;
    margin: 0px;
}}
QScrollBar::handle {{
    background-color: {BORDER_LINE_STRONG};
    border-radius: {handle_radius}px;
}}
QScrollBar::handle:vertical {{
    margin: {SCROLLBAR_HANDLE_INSET}px;
    min-height: {SCROLLBAR_HANDLE_MINIMUM}px;
}}
QScrollBar::handle:horizontal {{
    margin: {SCROLLBAR_HANDLE_INSET}px;
    min-width: {SCROLLBAR_HANDLE_MINIMUM}px;
}}
QScrollBar::handle:hover {{
    background-color: {ACCENT};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
    border: none;
    background: none;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
}}

QMenuBar {{
    background-color: {SURFACE_BASE};
    color: {TEXT_SECONDARY};
}}
QMenuBar::item {{
    background: transparent;
    padding: {SPACE_SM}px {SPACE_MD}px;
}}
QMenuBar::item:selected {{
    color: {ACCENT};
}}

QMenu {{
    background-color: {SURFACE_OVERLAY};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE_STRONG};
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_XS}px;
}}
QMenu::item {{
    color: {TEXT_SECONDARY};
    padding: {SPACE_SM}px {SPACE_MD}px;
    border-radius: {RADIUS_SM}px;
}}
QMenu::item:selected {{
    background-color: {SURFACE_RAISED};
    color: {TEXT_PRIMARY};
}}
QMenu::separator {{
    height: {BORDER_HAIRLINE}px;
    background-color: {BORDER_LINE};
    margin: {SPACE_XS}px {SPACE_SM}px;
}}
"""
