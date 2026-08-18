"""The detection review column: the browser plus what a verdict actually does.

This is where the mission turns a picture into a place the swarm flies to, so
the consequence of each button is written on screen, and a detection without a
ground coordinate cannot be approved at all — there would be nothing to send.
"""

from widgets.detection_review import DetectionReviewPanel
from competitions.international_uav.config import (
    DETECTION_HINT_TEXT,
    DETECTION_MISSING_LOCATION_TEXT,
)


class DetectionColumn(DetectionReviewPanel):
    """The shared detection browser, with this mission's wording and its rule."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.set_hint(DETECTION_HINT_TEXT)
        self.approve_guard = self.refuse_without_location

    @staticmethod
    def refuse_without_location(detection) -> str | None:
        """An approval carries a coordinate; without one there is nothing to send."""
        if detection.has_location():
            return None
        return DETECTION_MISSING_LOCATION_TEXT
