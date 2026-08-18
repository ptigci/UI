"""The things content sits on: cards, bars, tabs and sunken wells.

The card is the unit of layout. Nothing is placed straight onto the window
background, so a screen reads as a set of grouped panels instead of a wall of
labels. A card carries its state on the rail down its left edge, which is why
the rail is always there — it changes colour, never width, so nothing inside
the card moves when the state does.
"""

from theme.fonts import first_installed_family
from theme.tokens import (
    ACCENT,
    AS_APP_BAR,
    AS_CARD,
    AS_MAP,
    AS_PANEL,
    AS_STRIP,
    BORDER_HAIRLINE,
    BORDER_LINE,
    BORDER_LINE_STRONG,
    BORDER_RAIL,
    FONT_MONO_FAMILY,
    FONT_SIZE_LABEL,
    FONT_WEIGHT_SEMIBOLD,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    ROLE_DIVIDER,
    SPACE_LG,
    SPACE_SM,
    SPACE_XS,
    STATE_COLORS,
    SURFACE_CARD,
    SURFACE_RAISED,
    SURFACE_SUNKEN,
    TAB_UNDERLINE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def surfaces_sheet() -> str:
    return "\n".join([card_rules(), bar_rules(), tab_rules(), well_rules()])


def card_rules() -> str:
    state_rails = "\n".join(
        f'*[surface="{AS_CARD}"][state="{state}"] {{ border-left-color: {color}; }}'
        for state, color in STATE_COLORS.items()
    )
    return f"""
*[surface="{AS_CARD}"] {{
    background-color: {SURFACE_CARD};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    border-left: {BORDER_RAIL}px solid {BORDER_LINE};
    border-radius: {RADIUS_LG}px;
}}
*[surface="{AS_CARD}"]:hover {{
    border-color: {BORDER_LINE_STRONG};
}}
{state_rails}

/* A container with nothing to report: no rail, no state. */
*[surface="{AS_PANEL}"] {{
    background-color: {SURFACE_CARD};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    border-radius: {RADIUS_LG}px;
}}

*[role="{ROLE_DIVIDER}"] {{
    background-color: {BORDER_LINE};
    border: none;
    max-height: {BORDER_HAIRLINE}px;
}}
"""


def bar_rules() -> str:
    """The strip along the top of a window, and the readout strip at the bottom."""
    return f"""
*[surface="{AS_APP_BAR}"] {{
    background-color: {SURFACE_CARD};
    border-bottom: {BORDER_HAIRLINE}px solid {BORDER_LINE};
}}
*[surface="{AS_STRIP}"] {{
    background-color: {SURFACE_SUNKEN};
    border-top: {BORDER_HAIRLINE}px solid {BORDER_LINE};
}}
*[surface="{AS_MAP}"] {{
    background-color: {SURFACE_SUNKEN};
}}
"""


def tab_rules() -> str:
    return f"""
QTabWidget::pane {{
    background-color: {SURFACE_CARD};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    border-radius: {RADIUS_LG}px;
    top: -{BORDER_HAIRLINE}px;
}}
QTabBar {{
    qproperty-drawBase: 0;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: {TAB_UNDERLINE}px solid transparent;
    padding: {SPACE_SM}px {SPACE_LG}px;
    margin-right: {SPACE_XS}px;
    font-weight: {FONT_WEIGHT_SEMIBOLD};
}}
QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom-color: {ACCENT};
}}
QTabBar QToolButton {{
    background-color: {SURFACE_RAISED};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    border-radius: {RADIUS_SM}px;
    margin: {SPACE_XS}px;
}}
QTabBar QToolButton:hover {{
    background-color: {ACCENT};
}}
"""


def well_rules() -> str:
    """Sunken surfaces: lists, logs, tables and video. Content goes into them,
    so they sit below the card rather than on it."""
    mono_family = first_installed_family(FONT_MONO_FAMILY)
    return f"""
QListWidget, QListView, QTreeView, QTableView, QTextEdit, QPlainTextEdit {{
    background-color: {SURFACE_SUNKEN};
    color: {TEXT_SECONDARY};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_SM}px;
    selection-background-color: {SURFACE_RAISED};
    selection-color: {TEXT_PRIMARY};
}}
QListWidget::item, QTreeView::item {{
    padding: {SPACE_XS}px {SPACE_SM}px;
    border-radius: {RADIUS_SM}px;
}}
QListWidget::item:hover, QTreeView::item:hover {{
    background-color: {SURFACE_CARD};
}}
QListWidget::item:selected, QTreeView::item:selected {{
    background-color: {SURFACE_RAISED};
    color: {TEXT_PRIMARY};
}}
QHeaderView::section {{
    background-color: {SURFACE_CARD};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    padding: {SPACE_SM}px;
    font-size: {FONT_SIZE_LABEL}px;
    font-weight: {FONT_WEIGHT_SEMIBOLD};
}}

TerminalView {{
    font-family: {mono_family};
}}

CameraView {{
    background-color: {SURFACE_SUNKEN};
    color: {TEXT_MUTED};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    border-radius: {RADIUS_MD}px;
}}
"""
