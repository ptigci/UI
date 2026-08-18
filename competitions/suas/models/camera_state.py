"""The live picture's freshness, and whether the camera is recording.

Two facts that look like one on the screen and are not. The picture comes from
the ground services several times a second; the recording state comes from the
aircraft and changes only when somebody presses something. Either can be true
while the other is not — a camera recording perfectly to its own card while the
2.4 GHz link is down shows no picture at all, and that is not a fault.

Neither is inferred from a button. `recording` is what the aircraft last said,
and it stays unknown until it says something, because the command is a toggle:
guessing wrong makes the button do the opposite of its label.
"""

import time

from competitions.suas.config import (
    CAMERA_STALE_SECONDS,
    KEY_CAMERA_REASON,
    KEY_CAMERA_RECORDING,
)


class CameraState:
    """How old the newest frame is, and what the camera says it is doing."""

    def __init__(self) -> None:
        self.recording: bool | None = None
        self.reason: str = ""
        self.frame_received_monotonic: float | None = None

    def mark_frame(self) -> None:
        """One preview frame arrived."""
        self.frame_received_monotonic = time.monotonic()

    def update_from(self, payload: dict) -> None:
        """Take the aircraft's word on the recording."""
        self.recording = bool(payload.get(KEY_CAMERA_RECORDING))
        self.reason = payload.get(KEY_CAMERA_REASON) or ""

    def picture_is_live(self) -> bool:
        """Whether what is on the screen is current rather than the last frame."""
        if self.frame_received_monotonic is None:
            return False
        return time.monotonic() - self.frame_received_monotonic <= CAMERA_STALE_SECONDS

    def has_had_a_picture(self) -> bool:
        """Whether a frame has ever arrived.

        Never having had one and having lost one are different things to say to
        an operator: the first is usually an aircraft that is not powered up,
        the second is a link that just went.
        """
        return self.frame_received_monotonic is not None
