"""The two payload stations, as the aircraft last reported them."""

from competitions.suas.config import (
    KEY_PAYLOAD_STATIONS,
    KEY_STATION_CLASS,
    KEY_STATION_RELEASED_TRACK,
    KEY_STATION_STATE,
)


class Station:
    """One station: what it carries, what it drops on, whether it still has it."""

    def __init__(self, name: str, target_class: str, state: str,
                 released_track_id) -> None:
        self.name = name
        self.target_class = target_class
        self.state = state
        self.released_track_id = released_track_id


class PayloadState:
    """Every station the aircraft has."""

    def __init__(self) -> None:
        self.stations: list[Station] = []

    def update_from(self, payload: dict) -> None:
        stations = payload.get(KEY_PAYLOAD_STATIONS)
        if not isinstance(stations, dict):
            return
        self.stations = [
            Station(
                name,
                str(details.get(KEY_STATION_CLASS, "")),
                str(details.get(KEY_STATION_STATE, "")),
                details.get(KEY_STATION_RELEASED_TRACK),
            )
            for name, details in stations.items()
            if isinstance(details, dict)
        ]
