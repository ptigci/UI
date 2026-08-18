"""Headings, readouts, chips, and the colours that carry state.

Two things get their own type treatment. A heading is small, quiet and wide —
it labels a card without competing with what is in it. A readout is monospaced,
because a number the operator is watching should not shuffle sideways every
time a digit changes.

The state colours are generated from STATE_COLORS, so a label, a chip and a
card rail can never disagree about what "critical" looks like. They are written
last: a plain state rule and a role rule carry the same weight in Qt, so the
state has to come after the role to win.
"""

from theme.fonts import first_installed_family
from theme.tokens import (
    ACCENT,
    BORDER_HAIRLINE,
    BORDER_LINE,
    FONT_MONO_FAMILY,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_DISPLAY,
    FONT_SIZE_MICRO,
    FONT_SIZE_TITLE,
    FONT_WEIGHT_BOLD,
    FONT_WEIGHT_MEDIUM,
    FONT_WEIGHT_SEMIBOLD,
    RADIUS_PILL,
    ROLE_HEADING,
    ROLE_HINT,
    ROLE_PAGE_TITLE,
    ROLE_PILL,
    ROLE_READOUT,
    ROLE_READOUT_LABEL,
    ROLE_SUBHEADING,
    SCALE_BODY,
    SCALE_DISPLAY,
    SCALE_TITLE,
    SPACE_MD,
    STATE_COLORS,
    SURFACE_RAISED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    soft_fill,
    soft_line,
)

PILL_VERTICAL_PADDING = 2


def text_sheet() -> str:
    return "\n".join([heading_rules(), readout_rules(), pill_rules(), state_rules()])


def heading_rules() -> str:
    return f"""
QLabel {{
    color: {TEXT_SECONDARY};
    background: transparent;
}}

*[role="{ROLE_PAGE_TITLE}"] {{
    color: {TEXT_PRIMARY};
    font-size: {FONT_SIZE_TITLE}px;
    font-weight: {FONT_WEIGHT_SEMIBOLD};
}}
*[role="{ROLE_HEADING}"] {{
    color: {TEXT_MUTED};
    font-size: {FONT_SIZE_CAPTION}px;
    font-weight: {FONT_WEIGHT_BOLD};
}}
*[role="{ROLE_SUBHEADING}"] {{
    color: {TEXT_MUTED};
    font-size: {FONT_SIZE_CAPTION}px;
}}
*[role="{ROLE_HINT}"] {{
    color: {TEXT_MUTED};
    font-size: {FONT_SIZE_CAPTION}px;
}}
"""


def readout_rules() -> str:
    mono_family = first_installed_family(FONT_MONO_FAMILY)
    return f"""
*[role="{ROLE_READOUT}"] {{
    font-family: {mono_family};
    font-size: {FONT_SIZE_BODY}px;
    font-weight: {FONT_WEIGHT_MEDIUM};
    color: {TEXT_PRIMARY};
}}
*[role="{ROLE_READOUT}"][scale="{SCALE_DISPLAY}"] {{
    font-size: {FONT_SIZE_DISPLAY}px;
    font-weight: {FONT_WEIGHT_BOLD};
}}
*[role="{ROLE_READOUT}"][scale="{SCALE_TITLE}"] {{
    font-size: {FONT_SIZE_TITLE}px;
    font-weight: {FONT_WEIGHT_BOLD};
}}
*[role="{ROLE_READOUT}"][scale="{SCALE_BODY}"] {{
    font-size: {FONT_SIZE_BODY}px;
}}
/* The caption is the accent and the number is white. Two colours, and the
   operator's eye lands on the value rather than on what it is called. */
*[role="{ROLE_READOUT_LABEL}"] {{
    color: {ACCENT};
    font-size: {FONT_SIZE_MICRO}px;
    font-weight: {FONT_WEIGHT_SEMIBOLD};
}}
"""


def pill_rules() -> str:
    """A small filled chip. The one component that states a status in words."""
    tinted = "\n".join(
        f"""*[role="{ROLE_PILL}"][state="{state}"] {{
    color: {color};
    background-color: {soft_fill(color)};
    border-color: {soft_line(color)};
}}"""
        for state, color in STATE_COLORS.items()
    )
    return f"""
*[role="{ROLE_PILL}"] {{
    color: {TEXT_SECONDARY};
    background-color: {SURFACE_RAISED};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    border-radius: {RADIUS_PILL}px;
    padding: {PILL_VERTICAL_PADDING}px {SPACE_MD}px;
    font-size: {FONT_SIZE_CAPTION}px;
    font-weight: {FONT_WEIGHT_BOLD};
}}
{tinted}
"""


def state_rules() -> str:
    """Any label can carry a state, and it will always mean the same colour."""
    return "\n".join(
        f'QLabel[state="{state}"] {{ color: {color}; }}'
        for state, color in STATE_COLORS.items()
    )
