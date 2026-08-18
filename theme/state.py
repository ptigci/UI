"""How a widget asks the design system for a look.

Five properties, and nothing else. A widget says what it is (`role`), what it
sits on (`surface`), how it is doing (`state`), what it is for (`variant`) and
how big it needs to be (`scale`). The stylesheet in theme/sheets/ answers.

Properties rather than object names on purpose: object names have to be unique
within a form, so a screen with two hints on it would need two rules. These
work the same from Python and from a .ui file:

    <property name="role"><string>hint</string></property>

Qt resolves stylesheet rules when a widget is polished, so changing one of
these has no effect until the widget is polished again. That is done here, once,
instead of in every widget that changes state.
"""

from PyQt6.QtCore import Qt

ROLE_PROPERTY = "role"
SURFACE_PROPERTY = "surface"
STATE_PROPERTY = "state"
VARIANT_PROPERTY = "variant"
SCALE_PROPERTY = "scale"


def repolish(widget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def set_style_property(widget, name: str, value) -> None:
    """No-op when nothing changed, so a 10 Hz refresh costs nothing."""
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    repolish(widget)


def set_role(widget, role: str) -> None:
    set_style_property(widget, ROLE_PROPERTY, role)


def set_surface(widget, surface: str) -> None:
    """Make the widget a card, a bar or a strip.

    A plain QWidget subclass does not paint a stylesheet background unless it is
    told to, which is the usual reason a panel comes out invisible. Asking for a
    surface is exactly the moment to set that, so no caller has to remember.
    """
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    set_style_property(widget, SURFACE_PROPERTY, surface)


def set_state(widget, state: str) -> None:
    set_style_property(widget, STATE_PROPERTY, state)


def set_variant(widget, variant: str) -> None:
    set_style_property(widget, VARIANT_PROPERTY, variant)


def set_scale(widget, scale: str) -> None:
    set_style_property(widget, SCALE_PROPERTY, scale)
