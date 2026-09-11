"""Everything the operator clicks or types into.

Buttons come in one shape and four intents. The intent is a `variant` property
rather than an object name, so any competition can ask for a caution button
without a new rule being written for it:

    button.setProperty("variant", VARIANT_DANGER)
"""

from theme.spin_arrows import POINTING_DOWN, POINTING_UP, arrow_path
from theme.tokens import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_PRESSED,
    BORDER_FOCUS,
    BORDER_HAIRLINE,
    BORDER_LINE,
    BORDER_LINE_STRONG,
    CONTROL_HEIGHT,
    CONTROL_HEIGHT_LARGE,
    FOCUS_RING,
    FONT_SIZE_HEADING,
    FONT_WEIGHT_SEMIBOLD,
    ON_ACCENT,
    ON_STATUS,
    RADIUS_MD,
    RADIUS_PILL,
    RADIUS_SM,
    SCALE_ICON,
    SCALE_LARGE,
    SCALE_TILE,
    SPIN_ARROW_SIZE,
    SPIN_BUTTON_WIDTH,
    SPACE_LG,
    SPACE_SM,
    SPACE_XS,
    STATUS_CAUTION,
    STATUS_CRITICAL,
    SURFACE_BASE,
    SURFACE_CARD,
    SURFACE_OVERLAY,
    SURFACE_RAISED,
    SURFACE_SUNKEN,
    TEXT_DISABLED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TILE_HEIGHT,
    TILE_WIDTH,
    VARIANT_CAUTION,
    VARIANT_DANGER,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
    soft_fill,
    soft_line,
)

# Sizes that only exist to make Qt's own parts line up with the rest.
INDICATOR_SIZE = 16
SLIDER_GROOVE_HEIGHT = 4
SLIDER_HANDLE_SIZE = 14
PROGRESS_HEIGHT = 6


def controls_sheet() -> str:
    return "\n".join(
        [
            button_rules(),
            status_button_rules(VARIANT_CAUTION, STATUS_CAUTION),
            status_button_rules(VARIANT_DANGER, STATUS_CRITICAL),
            input_rules(),
            spin_and_combo_rules(),
            choice_rules(),
            slider_and_progress_rules(),
        ]
    )


def button_rules() -> str:
    return f"""
QPushButton {{
    background-color: {SURFACE_RAISED};
    color: {TEXT_PRIMARY};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    border-radius: {RADIUS_MD}px;
    padding: 0px {SPACE_LG}px;
    min-height: {CONTROL_HEIGHT}px;
    font-weight: {FONT_WEIGHT_SEMIBOLD};
}}
QPushButton:hover {{
    background-color: {SURFACE_OVERLAY};
    border-color: {BORDER_LINE_STRONG};
}}
QPushButton:pressed {{
    background-color: {SURFACE_CARD};
}}
/* Dimmed rather than solid accent: a focused button must not be mistaken for
   a selected one, and on this screen both can be true at once. */
QPushButton:focus {{
    border: {BORDER_FOCUS}px solid {FOCUS_RING};
}}
QPushButton:disabled {{
    background-color: {SURFACE_CARD};
    color: {TEXT_DISABLED};
    border-color: {BORDER_LINE};
}}

/* A toggle that is on says so the same way a primary button does. */
QPushButton[variant="{VARIANT_PRIMARY}"], QPushButton:checked {{
    background-color: {ACCENT};
    color: {ON_ACCENT};
    border-color: {ACCENT};
}}
QPushButton[variant="{VARIANT_PRIMARY}"]:hover, QPushButton:checked:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton[variant="{VARIANT_PRIMARY}"]:pressed, QPushButton:checked:pressed {{
    background-color: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}
/* Disabled looks the same whatever the button is for. A dimmed accent still
   reads as a button waiting to be pressed, which is the wrong answer. */
QPushButton[variant="{VARIANT_PRIMARY}"]:disabled, QPushButton:checked:disabled {{
    background-color: {SURFACE_CARD};
    color: {TEXT_DISABLED};
    border-color: {BORDER_LINE};
}}

QPushButton[variant="{VARIANT_GHOST}"] {{
    background-color: transparent;
    border-color: transparent;
    color: {TEXT_SECONDARY};
}}
QPushButton[variant="{VARIANT_GHOST}"]:hover {{
    background-color: {SURFACE_RAISED};
    color: {TEXT_PRIMARY};
}}
QPushButton[variant="{VARIANT_GHOST}"]:disabled {{
    background-color: transparent;
    color: {TEXT_DISABLED};
}}

/* A stylesheet min-height beats setMinimumHeight, so a taller button is asked
   for by scale rather than by the widget setting its own size. */
QPushButton[scale="{SCALE_LARGE}"] {{
    min-height: {CONTROL_HEIGHT_LARGE}px;
    font-size: {FONT_SIZE_HEADING}px;
}}
QPushButton[scale="{SCALE_TILE}"] {{
    min-width: {TILE_WIDTH}px;
    min-height: {TILE_HEIGHT}px;
    font-size: {FONT_SIZE_HEADING}px;
}}
/* One glyph wide: a stepper arrow, a close, an add. The usual button padding
   would swallow the glyph at this size. */
QPushButton[scale="{SCALE_ICON}"] {{
    min-width: {CONTROL_HEIGHT}px;
    max-width: {CONTROL_HEIGHT}px;
    padding: 0px;
}}
"""


def status_button_rules(variant: str, color: str) -> str:
    """A button that carries a warning: tinted at rest, solid under the pointer.

    Filling it only on hover keeps a row of controls calm until the operator
    reaches for the one that matters.
    """
    return f"""
QPushButton[variant="{variant}"] {{
    background-color: {soft_fill(color)};
    color: {color};
    border-color: {soft_line(color)};
}}
QPushButton[variant="{variant}"]:hover {{
    background-color: {color};
    color: {ON_STATUS};
    border-color: {color};
}}
QPushButton[variant="{variant}"]:pressed {{
    background-color: {color};
    color: {ON_STATUS};
}}
QPushButton[variant="{variant}"]:disabled {{
    background-color: {SURFACE_CARD};
    color: {TEXT_DISABLED};
    border-color: {BORDER_LINE};
}}
"""


def input_rules() -> str:
    return f"""
QLineEdit, QAbstractSpinBox, QComboBox {{
    background-color: {SURFACE_SUNKEN};
    color: {TEXT_PRIMARY};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE};
    border-radius: {RADIUS_MD}px;
    padding: 0px {SPACE_SM}px;
    min-height: {CONTROL_HEIGHT}px;
    selection-background-color: {ACCENT};
    selection-color: {ON_ACCENT};
}}
QLineEdit:hover, QAbstractSpinBox:hover, QComboBox:hover {{
    border-color: {BORDER_LINE_STRONG};
}}
QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus {{
    border: {BORDER_FOCUS}px solid {ACCENT};
    background-color: {SURFACE_BASE};
}}
QLineEdit:disabled, QAbstractSpinBox:disabled, QComboBox:disabled {{
    background-color: {SURFACE_CARD};
    color: {TEXT_DISABLED};
}}
"""


def spin_and_combo_rules() -> str:
    """The frame, the step buttons, and the popup.

    Each step button carries the frame's corner radius on its outer edge, so the
    pair fills the right-hand end of the field without squaring off the rounded
    frame behind it. Shaping them costs the arrows Fusion used to draw, so the
    glyphs come from theme/spin_arrows.py — see the note there.
    """
    up_arrow = arrow_path(POINTING_UP)
    down_arrow = arrow_path(POINTING_DOWN)
    return f"""
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    subcontrol-origin: padding;
    width: {SPIN_BUTTON_WIDTH}px;
    background-color: {SURFACE_RAISED};
    border: none;
}}
QAbstractSpinBox::up-button {{
    subcontrol-position: top right;
    border-top-right-radius: {RADIUS_MD}px;
}}
QAbstractSpinBox::down-button {{
    subcontrol-position: bottom right;
    border-bottom-right-radius: {RADIUS_MD}px;
}}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
    background-color: {SURFACE_OVERLAY};
}}
QAbstractSpinBox::up-button:pressed, QAbstractSpinBox::down-button:pressed {{
    background-color: {ACCENT};
}}
QAbstractSpinBox::up-button:disabled, QAbstractSpinBox::down-button:disabled {{
    background-color: {SURFACE_CARD};
}}

QAbstractSpinBox::up-arrow {{
    image: url("{up_arrow}");
    width: {SPIN_ARROW_SIZE}px;
    height: {SPIN_ARROW_SIZE}px;
}}
QAbstractSpinBox::down-arrow {{
    image: url("{down_arrow}");
    width: {SPIN_ARROW_SIZE}px;
    height: {SPIN_ARROW_SIZE}px;
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE_OVERLAY};
    color: {TEXT_PRIMARY};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE_STRONG};
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_XS}px;
    outline: none;
    selection-background-color: {SURFACE_RAISED};
}}
"""


def choice_rules() -> str:
    return f"""
QCheckBox, QRadioButton {{
    color: {TEXT_SECONDARY};
    spacing: {SPACE_SM}px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: {INDICATOR_SIZE}px;
    height: {INDICATOR_SIZE}px;
    background-color: {SURFACE_SUNKEN};
    border: {BORDER_HAIRLINE}px solid {BORDER_LINE_STRONG};
}}
QCheckBox::indicator {{
    border-radius: {RADIUS_SM}px;
}}
QRadioButton::indicator {{
    border-radius: {INDICATOR_SIZE // 2}px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox:disabled, QRadioButton:disabled {{
    color: {TEXT_DISABLED};
}}
"""


def slider_and_progress_rules() -> str:
    return f"""
QSlider::groove:horizontal {{
    height: {SLIDER_GROOVE_HEIGHT}px;
    background-color: {BORDER_LINE};
    border-radius: {SLIDER_GROOVE_HEIGHT // 2}px;
}}
QSlider::sub-page:horizontal {{
    background-color: {ACCENT};
    border-radius: {SLIDER_GROOVE_HEIGHT // 2}px;
}}
QSlider::handle:horizontal {{
    width: {SLIDER_HANDLE_SIZE}px;
    height: {SLIDER_HANDLE_SIZE}px;
    margin: -{(SLIDER_HANDLE_SIZE - SLIDER_GROOVE_HEIGHT) // 2}px 0px;
    border-radius: {SLIDER_HANDLE_SIZE // 2}px;
    background-color: {TEXT_PRIMARY};
}}

QProgressBar {{
    background-color: {SURFACE_SUNKEN};
    border: none;
    border-radius: {RADIUS_PILL}px;
    max-height: {PROGRESS_HEIGHT}px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: {RADIUS_PILL}px;
}}
"""
