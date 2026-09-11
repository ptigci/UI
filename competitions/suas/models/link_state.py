"""The two radios, tracked separately.

They are different bands doing different jobs and they do not fail together —
which is the whole point of having both. The 900 MHz RFD900x carries the safety
MAVLink path that Appendix B requires the ground station to have; the 2.4 GHz
Rocket link carries the mission bus. When one dies the operator has to know which, so
they never share an indicator.

The safety link's state comes from our own MAVLink connection rather than from a
message, because a link that reports on itself through the thing that is broken
tells you nothing.
"""

import time

from competitions.suas.config import (
    KEY_MISSION_LINK_LOSS,
    MISSION_LINK_STALE_MS,
    SAFETY_HEARTBEAT_TIMEOUT_MS,
)

MILLISECONDS_PER_SECOND = 1000


class LinkState:
    """Up or down, and how stale, for one radio."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.last_seen_monotonic: float | None = None
        self.loss_percent: float | None = None

    def mark_seen(self) -> None:
        self.last_seen_monotonic = time.monotonic()

    def mark_lost(self) -> None:
        self.last_seen_monotonic = None

    def age_milliseconds(self) -> float | None:
        if self.last_seen_monotonic is None:
            return None
        return (time.monotonic() - self.last_seen_monotonic) * MILLISECONDS_PER_SECOND

    def is_up(self, timeout_milliseconds: float) -> bool:
        age = self.age_milliseconds()
        if age is None:
            return False
        return age <= timeout_milliseconds


class LinkPair:
    """The mission link and the safety link, and nothing about either mixed up."""

    def __init__(self, mission_name: str, safety_name: str) -> None:
        self.mission = LinkState(mission_name)
        self.safety = LinkState(safety_name)

    def update_mission_from(self, payload: dict) -> None:
        self.mission.mark_seen()
        if KEY_MISSION_LINK_LOSS in payload:
            self.mission.loss_percent = float_or_none(payload[KEY_MISSION_LINK_LOSS])

    def safety_is_up(self) -> bool:
        return self.safety.is_up(SAFETY_HEARTBEAT_TIMEOUT_MS)

    def mission_is_up(self) -> bool:
        """Whether the aircraft has been heard from recently enough to call the link up."""
        return self.mission.is_up(MISSION_LINK_STALE_MS)


def float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
