"""How much further before the payload goes, and why it has not gone yet.

The aircraft decides this — both release solvers run on the Raspberry Pi and
neither needs us — so nothing here computes anything. It holds the last
countdown that arrived and answers the two questions the panel asks of it: what
number to show, and whether the mode being flown is one the operator can press
buttons at.

A countdown that stops arriving goes stale rather than staying on the screen as
a live figure. An aircraft that is no longer setting up a delivery is not one
metre from releasing, and a frozen number is the sort of thing an operator acts
on.
"""

import time

from competitions.suas.config import (
    KEY_COUNTDOWN_ALLOWED,
    KEY_COUNTDOWN_DISTANCE,
    KEY_COUNTDOWN_HEADING_ERROR,
    KEY_COUNTDOWN_METRES,
    KEY_COUNTDOWN_MODE,
    KEY_COUNTDOWN_REASON,
    KEY_COUNTDOWN_TARGET_CLASS,
    KEY_COUNTDOWN_THROW,
    KEY_COUNTDOWN_TRACK_ID,
    MODE_BALLISTIC,
)

# The aircraft publishes twice a second while a delivery is being set up, so
# nothing for this long means it has stopped setting one up.
COUNTDOWN_STALE_SECONDS = 3.0


class ReleaseState:
    """The last countdown the aircraft sent, and how old it is."""

    def __init__(self) -> None:
        self.mode: str | None = None
        self.track_id = None
        self.target_class: str | None = None
        self.metres_to_release: float | None = None
        self.distance_to_target_metres: float | None = None
        self.throw_metres: float | None = None
        self.heading_error_degrees: float | None = None
        self.release_allowed = False
        self.reason: str = ""
        self.received_monotonic: float | None = None

    def update_from(self, payload: dict) -> None:
        """Take one countdown message.

        Only the mode is guaranteed to be there. A refusal that never got as far
        as measuring anything carries a reason and no numbers, and that is worth
        showing: it is the answer to why the pass is doing nothing.
        """
        self.mode = payload.get(KEY_COUNTDOWN_MODE)
        self.track_id = payload.get(KEY_COUNTDOWN_TRACK_ID)
        self.target_class = payload.get(KEY_COUNTDOWN_TARGET_CLASS)
        self.metres_to_release = float_or_none(payload.get(KEY_COUNTDOWN_METRES))
        self.distance_to_target_metres = float_or_none(
            payload.get(KEY_COUNTDOWN_DISTANCE)
        )
        self.throw_metres = float_or_none(payload.get(KEY_COUNTDOWN_THROW))
        self.heading_error_degrees = float_or_none(
            payload.get(KEY_COUNTDOWN_HEADING_ERROR)
        )
        self.release_allowed = bool(payload.get(KEY_COUNTDOWN_ALLOWED))
        self.reason = payload.get(KEY_COUNTDOWN_REASON) or ""
        self.received_monotonic = time.monotonic()

    def is_live(self) -> bool:
        """Whether a delivery is being set up right now."""
        if self.received_monotonic is None:
            return False
        return time.monotonic() - self.received_monotonic <= COUNTDOWN_STALE_SECONDS

    def is_watch_only(self) -> bool:
        """Whether the aircraft is flying a release nobody can press a button at.

        The winged release is never commanded: it watches the mission the
        operator loaded in Mission Planner and lets go on the pass. Pressing GO
        TO DROP ZONE during one would be refused in the air, so the panel does
        not offer it.
        """
        return self.mode == MODE_BALLISTIC


def float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
