"""One detection waiting for the operator's verdict.

The aircraft sends an image and whatever it knows about what it found. The
panel only reads the keys named in config/interface.toml; everything else in
the message is carried along untouched so the verdict can be matched back to
the detection that produced it.
"""

from dataclasses import dataclass

from PyQt6.QtGui import QPixmap

from config import (
    DETECTION_KEY_ALTITUDE,
    DETECTION_KEY_CONFIDENCE,
    DETECTION_KEY_ID,
    DETECTION_KEY_IMAGE,
    DETECTION_KEY_LABEL,
    DETECTION_KEY_LATITUDE,
    DETECTION_KEY_LONGITUDE,
    DETECTION_KEY_TIMESTAMP,
    DETECTION_REVIEW_ALTITUDE_DECIMALS,
    DETECTION_REVIEW_CONFIDENCE_DECIMALS,
    DETECTION_REVIEW_COORDINATE_DECIMALS,
    DETECTION_REVIEW_DETAILS_FORMAT,
    DETECTION_REVIEW_MISSING_VALUE_TEXT,
)


@dataclass(frozen=True)
class Detection:
    """An incoming detection: the picture plus the message it arrived in."""

    image: QPixmap
    payload: dict

    def detection_id(self):
        return self.payload.get(DETECTION_KEY_ID)

    def label(self) -> str:
        return self.text_value(DETECTION_KEY_LABEL)

    def latitude(self) -> float | None:
        return self.number_value(DETECTION_KEY_LATITUDE)

    def longitude(self) -> float | None:
        return self.number_value(DETECTION_KEY_LONGITUDE)

    def altitude(self) -> float | None:
        return self.number_value(DETECTION_KEY_ALTITUDE)

    def confidence(self) -> float | None:
        return self.number_value(DETECTION_KEY_CONFIDENCE)

    def has_location(self) -> bool:
        return self.latitude() is not None and self.longitude() is not None

    def text_value(self, key: str) -> str:
        value = self.payload.get(key)
        if value is None:
            return DETECTION_REVIEW_MISSING_VALUE_TEXT
        return str(value)

    def number_value(self, key: str) -> float | None:
        value = self.payload.get(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def formatted(self, value: float | None, decimals: int) -> str:
        if value is None:
            return DETECTION_REVIEW_MISSING_VALUE_TEXT
        return f"{value:.{decimals}f}"

    def details_text(self) -> str:
        """The metadata line shown under the image."""
        return DETECTION_REVIEW_DETAILS_FORMAT.format(
            label=self.label(),
            confidence=self.formatted(self.confidence(), DETECTION_REVIEW_CONFIDENCE_DECIMALS),
            latitude=self.formatted(self.latitude(), DETECTION_REVIEW_COORDINATE_DECIMALS),
            longitude=self.formatted(self.longitude(), DETECTION_REVIEW_COORDINATE_DECIMALS),
            altitude=self.formatted(self.altitude(), DETECTION_REVIEW_ALTITUDE_DECIMALS),
            timestamp=self.text_value(DETECTION_KEY_TIMESTAMP),
        )

    def verdict_payload(self) -> dict:
        """What goes back out with the verdict: everything but the image.

        The picture has already been looked at, and sending it back would put a
        base64 blob on the link for no reason.
        """
        return {
            key: value for key, value in self.payload.items() if key != DETECTION_KEY_IMAGE
        }
