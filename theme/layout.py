"""Layout spacing, taken from the same tokens as everything else.

A .ui file can only hold literal numbers, so margins and spacing are set from
here after the form is loaded. That keeps the whitespace in the interface as
consistent as the colours, and changing the rhythm one place changes it
everywhere.
"""

from theme.tokens import SPACE_LG, SPACE_MD

NO_MARGIN = 0
# Bars that run edge to edge have no gap between them and what they border.
NO_SPACING = 0


def space_layout(layout, margin: int = SPACE_LG, spacing: int = SPACE_MD) -> None:
    layout.setContentsMargins(margin, margin, margin, margin)
    layout.setSpacing(spacing)


def flush_layout(layout, spacing: int = SPACE_MD) -> None:
    """No margin of its own — for a layout nested inside something already padded."""
    layout.setContentsMargins(NO_MARGIN, NO_MARGIN, NO_MARGIN, NO_MARGIN)
    layout.setSpacing(spacing)
