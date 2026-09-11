"""How the mapping capture is going while the aircraft is flying it.

Three counts and nothing clever: what the aircraft has taken, what has made it
down the link, and what is still queued on board. They are separate on purpose.
A capture taking frames while `frames_sent` sits still is a link problem, and
being able to see that before the flight ends is the whole reason the numbers
are on the page.

Whether a capture is running is not in the message -- the aircraft only reports
progress while there is progress to report. It comes from the command the
aircraft acknowledged, through mark_capture, and the staleness check catches the
case where that answer is no longer true because the reports have stopped.
"""

import time

from competitions.suas.config import (
    KEY_MAPPING_FRAMES_CAPTURED,
    KEY_MAPPING_FRAMES_QUEUED,
    KEY_MAPPING_FRAMES_SENT,
    KEY_MAPPING_SESSION_ID,
    TEST_MAPPING_TEXT,
)

CAPTURE_STALE_SECONDS: float = TEST_MAPPING_TEXT["capture_stale_seconds"]


class MappingCaptureState:
    """The last mapping_progress message, and whether a capture is running."""

    def __init__(self) -> None:
        self.frames_captured: int = 0
        self.frames_queued: int = 0
        self.frames_sent: int = 0
        self.session_id: str = ""
        self.capturing: bool = False
        self.received_monotonic: float | None = None

    def update_from(self, payload: dict) -> None:
        self.frames_captured = count_or_zero(payload.get(KEY_MAPPING_FRAMES_CAPTURED))
        self.frames_queued = count_or_zero(payload.get(KEY_MAPPING_FRAMES_QUEUED))
        self.frames_sent = count_or_zero(payload.get(KEY_MAPPING_FRAMES_SENT))
        self.session_id = payload.get(KEY_MAPPING_SESSION_ID) or ""
        self.received_monotonic = time.monotonic()

    def mark_capture(self, running: bool) -> None:
        """Take the acknowledged command's word for it.

        Starting also counts as a report, so the page does not call a capture
        stale in the gap before the first progress message arrives.
        """
        self.capturing = running
        if running:
            self.received_monotonic = time.monotonic()

    def is_live(self) -> bool:
        """Running, and still saying so."""
        if not self.capturing or self.received_monotonic is None:
            return False
        return time.monotonic() - self.received_monotonic <= CAPTURE_STALE_SECONDS


def count_or_zero(value) -> int:
    """A count from the wire, or zero when the field is missing or not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
