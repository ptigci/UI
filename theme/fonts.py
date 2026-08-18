"""Fonts built from the type tokens.

Most type is set by the stylesheet. This module exists for the one thing a Qt
stylesheet cannot do: letter spacing. Qt parses no `letter-spacing` property,
so the wide tracking on card headings and on the big readouts is applied to the
QFont instead — see apply_tracking.
"""

from PyQt6.QtGui import QFont, QFontDatabase

from theme.tokens import (
    FONT_FAMILY,
    FONT_MONO_FAMILY,
    FONT_SIZE_BODY,
    FONT_WEIGHT_REGULAR,
)

NO_TRACKING = 0.0


def family_list(families: str) -> list[str]:
    """The stylesheet writes families as a CSS list; QFont wants them apart."""
    return [name.strip().strip("'\"") for name in families.split(",")]


def first_installed_family(families: str) -> str:
    """Pick the best family actually present on this machine.

    A Qt stylesheet takes one family name and no fallback list, so the fallback
    has to be resolved before the sheet is built. Needs a running QApplication,
    which is why the stylesheet is composed in apply_theme rather than at import.
    """
    installed = set(QFontDatabase.families())
    candidates = family_list(families)
    for family in candidates:
        if family in installed:
            return family
    # The last entry is the generic name (sans-serif, monospace); Qt maps it.
    return candidates[-1]


def ui_font(
    size: int = FONT_SIZE_BODY,
    weight: int = FONT_WEIGHT_REGULAR,
    tracking: float = NO_TRACKING,
) -> QFont:
    return build_font(family_list(FONT_FAMILY), size, weight, tracking)


def mono_font(
    size: int = FONT_SIZE_BODY,
    weight: int = FONT_WEIGHT_REGULAR,
    tracking: float = NO_TRACKING,
) -> QFont:
    return build_font(family_list(FONT_MONO_FAMILY), size, weight, tracking)


def build_font(families: list[str], size: int, weight: int, tracking: float) -> QFont:
    font = QFont()
    font.setFamilies(families)
    font.setPixelSize(size)
    font.setWeight(QFont.Weight(weight))
    if tracking != NO_TRACKING:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, tracking)
    return font
