"""The detection review column: the browser plus what a verdict actually does.

Approving a target here is what sends the aircraft to fly to it and spend a
payload on it, so the two things that would make that impossible are refused
before the operator can click: a detection with no coordinate has nowhere to
fly to, and a detection of a class the aircraft could not name has no payload
station bound to it. Both would promise a delivery that can never happen.

Denying is not the opposite of approving. It rejects the target *and*
blacklists the place, so the aircraft does not raise the same false positive
again ten seconds later. The hint says so, because that is not obvious from a
button labelled DENY.
"""

from widgets.detection_review import DetectionReviewPanel
from competitions.suas.config import (
    DETECTION_HINT_TEXT,
    DETECTION_MISSING_LOCATION_TEXT,
    DETECTION_UNKNOWN_CLASS_NAME,
    DETECTION_UNKNOWN_CLASS_TEXT,
)


class DetectionColumn(DetectionReviewPanel):
    """The shared detection browser, with this mission's wording and its rules."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.set_hint(DETECTION_HINT_TEXT)
        self.approve_guard = self.refuse_what_cannot_be_delivered

    @staticmethod
    def refuse_what_cannot_be_delivered(detection) -> str | None:
        """Why this detection may not be approved, or ``None`` when it may.

        Returns:
            str or None: The reason to show the operator.
        """
        if not detection.has_location():
            return DETECTION_MISSING_LOCATION_TEXT
        if detection.label() == DETECTION_UNKNOWN_CLASS_NAME:
            return DETECTION_UNKNOWN_CLASS_TEXT
        return None
