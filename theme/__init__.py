"""The design system: one palette, one type scale, one set of components.

Every screen in every competition is drawn from the tokens in
config/theme.toml. Start the theme once, on the QApplication, and every window
and dialog opened afterwards inherits it:

    apply_theme(application)

A widget asks for a look by name — an object name for what it is (`card`,
`readout`, `pill`) and a property for how it is doing (`state`, `variant`).
It never writes a colour.
"""

from theme.animation import fade_in
from theme.application import apply_theme
from theme.elevation import apply_shadow
from theme.fonts import mono_font, ui_font
from theme.layout import flush_layout, space_layout
from theme.state import (
    repolish,
    set_role,
    set_scale,
    set_state,
    set_surface,
    set_variant,
)

__all__ = [
    "apply_theme",
    "apply_shadow",
    "fade_in",
    "flush_layout",
    "mono_font",
    "space_layout",
    "repolish",
    "set_role",
    "set_scale",
    "set_state",
    "set_surface",
    "set_variant",
    "ui_font",
]
