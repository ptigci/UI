"""What the camera says about itself, and how old that answer is.

Every angle in here is one the gimbal reported, never one it was asked for.
That distinction is the reason the camera page exists: a gimbal that echoes the
command straight back is a gimbal that is not moving, and the only way to catch
it is to keep the two numbers apart all the way from the wire to the screen. So
nothing in this file is ever filled in from a press.

The aircraft sends several of these a second while the page is open. A gap
longer than the stale limit means the readings on screen are history rather
than a camera holding still, and the page says so instead of showing them.
"""

import time

from competitions.suas.config import (
    KEY_GIMBAL_CARD_FREE,
    KEY_GIMBAL_CARD_STATE,
    KEY_GIMBAL_PITCH,
    KEY_GIMBAL_REACHABLE,
    KEY_GIMBAL_REASON,
    KEY_GIMBAL_RECORDING,
    KEY_GIMBAL_ROLL,
    KEY_GIMBAL_STREAM_UP,
    KEY_GIMBAL_YAW,
    KEY_GIMBAL_ZOOM,
    TEST_GIMBAL_STALE_SECONDS,
)


class GimbalState:
    """The last gimbal_state message, one field per fact the camera reported."""

    def __init__(self) -> None:
        self.reachable = False
        self.yaw_degrees: float | None = None
        self.pitch_degrees: float | None = None
        self.roll_degrees: float | None = None
        self.zoom: float | None = None
        self.recording = False
        self.card_state: str = ""
        self.card_free_megabytes: float | None = None
        self.stream_up = False
        self.reason: str = ""
        self.message_received_monotonic: float | None = None

    def mark_message(self) -> None:
        """One gimbal message arrived."""
        self.message_received_monotonic = time.monotonic()

    def update_from(self, payload: dict) -> None:
        """Take the camera's word on itself.

        An unreachable gimbal still sends one of these, with the reason and
        nothing else, which is why every reading is allowed to be missing.
        """
        self.reachable = bool(payload.get(KEY_GIMBAL_REACHABLE))
        self.yaw_degrees = number_or_none(payload.get(KEY_GIMBAL_YAW))
        self.pitch_degrees = number_or_none(payload.get(KEY_GIMBAL_PITCH))
        self.roll_degrees = number_or_none(payload.get(KEY_GIMBAL_ROLL))
        self.zoom = number_or_none(payload.get(KEY_GIMBAL_ZOOM))
        self.recording = bool(payload.get(KEY_GIMBAL_RECORDING))
        self.card_state = payload.get(KEY_GIMBAL_CARD_STATE) or ""
        self.card_free_megabytes = number_or_none(payload.get(KEY_GIMBAL_CARD_FREE))
        self.stream_up = bool(payload.get(KEY_GIMBAL_STREAM_UP))
        self.reason = payload.get(KEY_GIMBAL_REASON) or ""
        self.mark_message()

    def is_live(self) -> bool:
        """Whether the readings are current rather than the last ones to arrive."""
        if self.message_received_monotonic is None:
            return False
        age_seconds = time.monotonic() - self.message_received_monotonic
        return age_seconds <= TEST_GIMBAL_STALE_SECONDS


def number_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
