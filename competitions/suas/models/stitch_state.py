"""Where the map stands, as the ground services last said.

The stitch runs on the ground services machine and this holds nothing but their
last word on it: running, complete, failed or on the stick, the counts, the
clock, and where the full mosaic was written. The preview picture is not kept
here — it goes straight to the panel as bytes, the way a video frame does,
because a picture is a Qt matter and this is not a Qt object.

The clock keeps moving between messages: the ground services say how long the
stitch has been running as of their message, and the panel adds the time since
that message arrived.
"""

import time

from competitions.suas.config import (
    KEY_STITCH_ELAPSED,
    KEY_STITCH_EXPORT_PATH,
    KEY_STITCH_FOLDER,
    KEY_STITCH_FRAMES_FOUND,
    KEY_STITCH_FRAMES_PLACED,
    KEY_STITCH_FRAMES_RECEIVED,
    KEY_STITCH_FRAMES_SKIPPED,
    KEY_STITCH_FRAMES_TO_PLACE,
    KEY_STITCH_FRAMES_USED,
    KEY_STITCH_MOSAIC_PATH,
    KEY_STITCH_REASON,
    KEY_STITCH_STATE,
    STITCH_STATE_COMPLETE,
    STITCH_STATE_EXPORTED,
    STITCH_STATE_FAILED,
    STITCH_STATE_RUNNING,
)


class StitchState:
    """The last stitch_state message, one field per fact."""

    def __init__(self) -> None:
        self.state: str | None = None
        self.reason: str = ""
        self.source: str = ""
        self.frames_found: int = 0
        self.frames_skipped: int = 0
        self.frames_placed: int = 0
        self.frames_to_place: int = 0
        self.frames_used: int = 0
        self.frames_received: int = 0
        self.mosaic_path: str = ""
        self.export_path: str = ""
        self.elapsed_seconds: float = 0.0
        self.received_monotonic: float | None = None

    def update_from(self, payload: dict) -> None:
        """Take the ground services' word on the stitch."""
        self.state = payload.get(KEY_STITCH_STATE)
        self.reason = payload.get(KEY_STITCH_REASON) or ""
        self.source = payload.get(KEY_STITCH_FOLDER) or ""
        self.frames_found = count_or_zero(payload.get(KEY_STITCH_FRAMES_FOUND))
        self.frames_skipped = count_or_zero(payload.get(KEY_STITCH_FRAMES_SKIPPED))
        self.frames_placed = count_or_zero(payload.get(KEY_STITCH_FRAMES_PLACED))
        self.frames_to_place = count_or_zero(payload.get(KEY_STITCH_FRAMES_TO_PLACE))
        self.frames_used = count_or_zero(payload.get(KEY_STITCH_FRAMES_USED))
        self.frames_received = count_or_zero(payload.get(KEY_STITCH_FRAMES_RECEIVED))
        self.mosaic_path = payload.get(KEY_STITCH_MOSAIC_PATH) or ""
        self.export_path = payload.get(KEY_STITCH_EXPORT_PATH) or ""
        self.elapsed_seconds = number_or_zero(payload.get(KEY_STITCH_ELAPSED))
        self.received_monotonic = time.monotonic()

    def is_running(self) -> bool:
        return self.state == STITCH_STATE_RUNNING

    def is_complete(self) -> bool:
        return self.state == STITCH_STATE_COMPLETE

    def is_failed(self) -> bool:
        return self.state == STITCH_STATE_FAILED

    def is_exported(self) -> bool:
        return self.state == STITCH_STATE_EXPORTED

    def has_map(self) -> bool:
        return bool(self.mosaic_path)

    def is_counting_frames(self) -> bool:
        """Whether the ground services have said how far through they are.

        They only say it once the first frame is down, and the feature-based
        backend never says it at all -- so this is what tells a bar that can
        fill from one that can only spin.
        """
        return self.frames_to_place > 0

    def elapsed_now(self) -> float:
        """Seconds the stitch has been going, ticking on between messages."""
        if self.received_monotonic is None:
            return 0.0
        if not self.is_running():
            return self.elapsed_seconds
        return self.elapsed_seconds + (time.monotonic() - self.received_monotonic)


def count_or_zero(value) -> int:
    """A count from the wire, or zero when the field is missing or not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def number_or_zero(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
