"""SUAS 2026 interface: one VTOL, a 45-minute clock, and a judge watching.

The requirements live in UI/docs/SUAS_UI.md. The detection approve / deny browser
this competition needs is already shared: widgets/detection_review/.
"""

import logging

from competitions.suas.windows import SuasMainWindow

logger = logging.getLogger(__name__)


def start_suas(selection):
    """Open the SUAS operations window."""
    if selection.vtol_count > 1:
        # 1.4: teams may enter one aircraft, and the topics carry no vehicle id.
        logger.warning(
            f"{selection.vtol_count} VTOLs were selected, but SUAS flies one aircraft. "
            f"The extra ones are ignored."
        )
    return SuasMainWindow(selection)
