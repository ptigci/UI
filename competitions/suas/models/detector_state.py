"""What the detector says it is doing, and one thing it says it saw.

Two facts arrive together and are kept apart on purpose: the detector that was
asked for and the detector that actually loaded. A Hailo that will not open
falls back to the CPU and carries on detecting, so a page that only showed the
choice the operator made would spend the afternoon measuring the wrong model.
`fell_back` is the question that catches it.

Nothing here is inferred from a press. `running` stays unknown until the
aircraft says, the same way the camera's recording does, because the command is
a toggle and guessing wrong makes the button do the opposite of its label.
"""

from competitions.suas.config import (
    KEY_DETECTOR_BACKEND,
    KEY_DETECTOR_FRAMES_PER_SECOND,
    KEY_DETECTOR_FRAMES_SEEN,
    KEY_DETECTOR_MINIMUM_CONFIDENCE,
    KEY_DETECTOR_REASON,
    KEY_DETECTOR_REQUESTED_BACKEND,
    KEY_DETECTOR_RUNNING,
    KEY_DETECTOR_SIGHTINGS,
    KEY_SIGHTING_BACKEND,
    KEY_SIGHTING_CLASS,
    KEY_SIGHTING_CONFIDENCE,
    KEY_SIGHTING_FRAME_TIMESTAMP,
    KEY_SIGHTING_ID,
    KEY_SIGHTING_IMAGE,
    KEY_SIGHTING_LATITUDE,
    KEY_SIGHTING_LONGITUDE,
    KEY_SIGHTING_POSITION_ERROR,
    KEY_SIGHTING_PROJECTION_INPUTS,
)


class DetectorState:
    """The detector's own account of itself, as it last reported."""

    def __init__(self) -> None:
        self.running: bool | None = None
        self.backend: str = ""
        self.requested_backend: str = ""
        self.minimum_confidence: float = 0.0
        self.frames_per_second: float = 0.0
        self.frames_seen: int = 0
        self.sightings: int = 0
        self.reason: str = ""

    def update_from(self, payload: dict) -> None:
        """Take the aircraft's word on the detector."""
        self.running = bool(payload.get(KEY_DETECTOR_RUNNING))
        self.backend = payload.get(KEY_DETECTOR_BACKEND) or ""
        self.requested_backend = payload.get(KEY_DETECTOR_REQUESTED_BACKEND) or ""
        self.minimum_confidence = number_or_zero(
            payload.get(KEY_DETECTOR_MINIMUM_CONFIDENCE)
        )
        self.frames_per_second = number_or_zero(
            payload.get(KEY_DETECTOR_FRAMES_PER_SECOND)
        )
        self.frames_seen = count_or_zero(payload.get(KEY_DETECTOR_FRAMES_SEEN))
        self.sightings = count_or_zero(payload.get(KEY_DETECTOR_SIGHTINGS))
        self.reason = payload.get(KEY_DETECTOR_REASON) or ""

    def fell_back(self) -> bool:
        """Whether the detector that loaded is not the one that was asked for.

        Both names have to be there before the two can disagree: an aircraft
        that has not said which detector it was asked for has not fallen back,
        it has simply not told us yet.
        """
        if not self.backend or not self.requested_backend:
            return False
        return self.backend != self.requested_backend


class Sighting:
    """One thing the model saw in one frame.

    The place may be missing, and that is an answer rather than a fault: a
    sighting taken while the attitude was unknown has a score and nowhere to
    put it. What the projection was given comes along as one table, kept as
    it arrived: the page never reads it, the sighting log writes it down.
    """

    def __init__(self, payload: dict) -> None:
        self.sighting_id = payload.get(KEY_SIGHTING_ID)
        self.target_class = str(payload.get(KEY_SIGHTING_CLASS) or "")
        self.confidence = number_or_zero(payload.get(KEY_SIGHTING_CONFIDENCE))
        self.latitude = number_or_none(payload.get(KEY_SIGHTING_LATITUDE))
        self.longitude = number_or_none(payload.get(KEY_SIGHTING_LONGITUDE))
        self.position_error_m = number_or_none(payload.get(KEY_SIGHTING_POSITION_ERROR))
        self.projection_inputs = table_or_empty(payload.get(KEY_SIGHTING_PROJECTION_INPUTS))
        self.image_base64 = payload.get(KEY_SIGHTING_IMAGE) or ""
        self.frame_timestamp = number_or_none(payload.get(KEY_SIGHTING_FRAME_TIMESTAMP))
        self.backend = payload.get(KEY_SIGHTING_BACKEND) or ""

    def position(self) -> tuple[float, float] | None:
        """Where the projection put it, or None when it could not put it anywhere."""
        if self.latitude is None or self.longitude is None:
            return None
        return self.latitude, self.longitude


def number_or_none(value) -> float | None:
    """A number from the wire, or None when the field is missing or not one."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def number_or_zero(value) -> float:
    number = number_or_none(value)
    if number is None:
        return 0.0
    return number


def count_or_zero(value) -> int:
    return int(number_or_zero(value))


def table_or_empty(value) -> dict:
    """A nested table from the wire, or nothing when the field was not one."""
    if isinstance(value, dict):
        return value
    return {}
