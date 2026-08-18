"""One hop of the radio network, and the antenna tracker that keeps it pointed.

The ground station measures these; the interface only shows them. A link that
is quietly getting worse is the earliest warning the operator gets.
"""

from dataclasses import dataclass

from competitions.international_uav.config import (
    KEY_LINK_LAST_SEEN_MS,
    KEY_LINK_LATENCY_MS,
    KEY_LINK_LOSS_PERCENT,
    KEY_LINK_NAME,
    KEY_LINK_SIGNAL,
    KEY_TRACKER_ERROR_DEGREES,
    KEY_TRACKER_LOCKED,
    LINK_LATENCY_WARNING_MS,
    LINK_LOSS_WARNING_PERCENT,
)
from competitions.international_uav.models.vehicle_state import number_from, text_from


@dataclass
class LinkState:
    name: str
    latency_ms: float | None = None
    loss_percent: float | None = None
    last_seen_ms: float | None = None
    signal_strength: float | None = None

    def is_degraded(self) -> bool:
        if self.latency_ms is not None and self.latency_ms > LINK_LATENCY_WARNING_MS:
            return True
        if self.loss_percent is not None and self.loss_percent > LINK_LOSS_WARNING_PERCENT:
            return True
        return False


@dataclass
class TrackerState:
    locked: bool | None = None
    error_degrees: float | None = None


def link_from_payload(payload: dict) -> LinkState | None:
    """One entry of the links list, or None when it carries no name."""
    name = text_from(payload, KEY_LINK_NAME, None)
    if name is None:
        return None
    link = LinkState(name)
    link.latency_ms = number_from(payload, KEY_LINK_LATENCY_MS, None)
    link.loss_percent = number_from(payload, KEY_LINK_LOSS_PERCENT, None)
    link.last_seen_ms = number_from(payload, KEY_LINK_LAST_SEEN_MS, None)
    link.signal_strength = number_from(payload, KEY_LINK_SIGNAL, None)
    return link


def tracker_from_payload(payload: dict) -> TrackerState:
    tracker = TrackerState()
    if KEY_TRACKER_LOCKED in payload:
        tracker.locked = bool(payload[KEY_TRACKER_LOCKED])
    tracker.error_degrees = number_from(payload, KEY_TRACKER_ERROR_DEGREES, None)
    return tracker
