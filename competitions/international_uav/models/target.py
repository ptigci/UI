"""A place on the ground the swarm is meant to reach.

A target starts as a detection the operator approved, gets confirmed by the
ground station, is assigned to an agent, and ends delivered, failed or vetoed.
"""

from dataclasses import dataclass

from competitions.international_uav.config import (
    KEY_TARGET_AGENT,
    KEY_TARGET_CONFIDENCE,
    KEY_TARGET_ID,
    KEY_TARGET_LABEL,
    KEY_TARGET_LATITUDE,
    KEY_TARGET_LONGITUDE,
    KEY_TARGET_PRIORITY,
    KEY_TARGET_STATE,
    TARGET_STATE_CANDIDATE,
    TARGET_STATE_CONFIRMED,
    TARGET_STATE_VETOED,
)
from competitions.international_uav.models.vehicle_state import number_from, text_from


@dataclass
class Target:
    target_id: str
    label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    confidence: float | None = None
    priority: float | None = None
    state: str = TARGET_STATE_CANDIDATE
    agent_id: str | None = None

    def update_from(self, payload: dict) -> None:
        self.label = text_from(payload, KEY_TARGET_LABEL, self.label)
        self.latitude = number_from(payload, KEY_TARGET_LATITUDE, self.latitude)
        self.longitude = number_from(payload, KEY_TARGET_LONGITUDE, self.longitude)
        self.confidence = number_from(payload, KEY_TARGET_CONFIDENCE, self.confidence)
        self.priority = number_from(payload, KEY_TARGET_PRIORITY, self.priority)
        self.state = text_from(payload, KEY_TARGET_STATE, self.state)
        self.agent_id = text_from(payload, KEY_TARGET_AGENT, self.agent_id)

    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def is_open(self) -> bool:
        """Still waiting for an agent, so the operator can still drop it."""
        return self.state in (TARGET_STATE_CANDIDATE, TARGET_STATE_CONFIRMED)

    def is_vetoed(self) -> bool:
        return self.state == TARGET_STATE_VETOED


def target_from_payload(payload: dict) -> Target | None:
    """Build a target from a ground-station message, or None without an id."""
    target_id = payload.get(KEY_TARGET_ID)
    if target_id is None:
        return None
    target = Target(str(target_id))
    target.update_from(payload)
    return target
