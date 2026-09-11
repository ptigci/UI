"""What the map draws about the targets: every track, and the ground denied.

The aircraft publishes each fused track as it changes and every blacklist zone
whenever one is added or cleared. This keeps the latest of both so the map can
draw where the aircraft believes the mannequin and the tent are, what the
operator said about each, and where a denial has closed the ground.
"""

import threading

from competitions.suas.config import (
    KEY_BLACKLIST_ZONES,
    KEY_TRACK_CLASS,
    KEY_TRACK_DECISION,
    KEY_TRACK_ID,
    KEY_TRACK_LATITUDE,
    KEY_TRACK_LONGITUDE,
    KEY_TRACK_SCORE,
    KEY_ZONE_CLASS,
    KEY_ZONE_ID,
    KEY_ZONE_LATITUDE,
    KEY_ZONE_LONGITUDE,
    KEY_ZONE_RADIUS,
)


class MapTrack:
    """One target as the aircraft last reported it."""

    def __init__(self, track_id, target_class: str, latitude: float,
                 longitude: float, decision: str, score: float) -> None:
        self.track_id = track_id
        self.target_class = target_class
        self.latitude = latitude
        self.longitude = longitude
        self.decision = decision
        self.score = score


class BlacklistZone:
    """Ground a denial closed off."""

    def __init__(self, zone_id, target_class: str, latitude: float,
                 longitude: float, radius_metres: float) -> None:
        self.zone_id = zone_id
        self.target_class = target_class
        self.latitude = latitude
        self.longitude = longitude
        self.radius_metres = radius_metres


class TargetMapState:
    """The tracks and zones the map draws, safe to read from the Qt thread."""

    def __init__(self) -> None:
        self.tracks: dict = {}
        self.zones: list[BlacklistZone] = []
        self.lock = threading.Lock()

    def update_track_from(self, payload: dict) -> None:
        try:
            track = MapTrack(
                payload[KEY_TRACK_ID],
                str(payload.get(KEY_TRACK_CLASS, "")),
                float(payload[KEY_TRACK_LATITUDE]),
                float(payload[KEY_TRACK_LONGITUDE]),
                str(payload.get(KEY_TRACK_DECISION, "")),
                float(payload.get(KEY_TRACK_SCORE) or 0.0),
            )
        except (KeyError, TypeError, ValueError):
            return
        with self.lock:
            self.tracks[track.track_id] = track

    def update_zones_from(self, payload: dict) -> None:
        zones = []
        for zone in payload.get(KEY_BLACKLIST_ZONES) or []:
            try:
                zones.append(BlacklistZone(
                    zone[KEY_ZONE_ID], str(zone.get(KEY_ZONE_CLASS, "")),
                    float(zone[KEY_ZONE_LATITUDE]), float(zone[KEY_ZONE_LONGITUDE]),
                    float(zone[KEY_ZONE_RADIUS]),
                ))
            except (KeyError, TypeError, ValueError):
                continue
        with self.lock:
            self.zones = zones

    def snapshot(self) -> tuple[list, list]:
        """Copies of the tracks and zones, for the painter."""
        with self.lock:
            return list(self.tracks.values()), list(self.zones)
