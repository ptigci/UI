"""Composes the one stylesheet the whole application runs on.

Order matters: later rules win ties, so the sheet goes from the most general to
the most specific. Nothing else in the codebase calls setStyleSheet — a screen
that needs to look different asks for it with a property, and the rule for that
property lives in theme/sheets/.
"""

from theme.sheets import base_sheet, controls_sheet, surfaces_sheet, text_sheet


def build_stylesheet() -> str:
    return "\n".join([base_sheet(), controls_sheet(), surfaces_sheet(), text_sheet()])
