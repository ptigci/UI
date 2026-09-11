"""Every sighting the detection page received, kept on this laptop.

The page shows the last forty sightings and one error number per truth point,
and when the application closes both are gone. The question after a bench day
is never answered by those: it is "why was the mannequin 6 m out on the third
pass and 2 m out on the fourth", and that needs every sighting, what the
aircraft was given to place it, and how far off each one was -- kept, so it can
be gone through afterwards.

So each session's sightings go in a folder of their own: one line of JSON per
sighting, and the crop it came with as a picture beside it. The line carries
what the model said, where the aircraft put it, everything the projection was
given to put it there, and the metres to the nearest truth point of its class
at the moment it arrived. The truth points themselves are written into the
same file as they are added, so the file is enough on its own.

The aircraft keeps its own copy of the same numbers on its card. This one is
the copy that does not need the aircraft back on the bench to read.
"""

import json
import logging
import time

from competitions.suas.config import TEST_LOGGING, TEST_SIGHTING_LOG, competition_path

logger = logging.getLogger(__name__)

SIGHTING_RECORD = "sighting"
TRUTH_POINT_RECORD = "truth_point"
TRUTH_POINT_REMOVED_RECORD = "truth_point_removed"


class SightingLog:
    """One session's sightings, on disk."""

    def __init__(self) -> None:
        self.folder = None
        self.log_file = None
        self.kept = 0

    def open(self) -> bool:
        """Create the folder the first time there is something to keep.

        Returns:
            bool: Whether there is a file to write to. A folder that cannot be
            made costs the record and nothing else; the page carries on and
            the failure is said once rather than once per sighting.
        """
        if self.folder is not None:
            return self.log_file is not None

        stamp = time.strftime(TEST_LOGGING["stamp_format"])
        self.folder = competition_path(TEST_LOGGING["folder"]) / (
            TEST_SIGHTING_LOG["folder_format"].format(stamp=stamp)
        )
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            self.log_file = (self.folder / TEST_SIGHTING_LOG["log_name"]).open(
                "a", encoding="utf-8"
            )
        except OSError as error:
            logger.warning(f"Sightings will not be kept: {error}")
            return False

        logger.info(f"Sightings are being kept in {self.folder}.")
        return True

    def note_sighting(self, sighting, image_bytes: bytes, error_metres,
                      point_id) -> None:
        """Write one sighting down, crop and all.

        Parameters:
            sighting (Sighting): What arrived.
            image_bytes (bytes): Its crop, already decoded; empty when the
                picture would not decode, in which case only the line is kept.
            error_metres (float or None): Metres to the nearest truth point of
                its class, or None when there is no place or no point.
            point_id (str or None): Which truth point that was measured to.
        """
        if not self.open():
            return

        crop_name = None
        if image_bytes:
            crop_name = self.write_crop(sighting, image_bytes)

        self.write({
            "record": SIGHTING_RECORD,
            "sighting_id": sighting.sighting_id,
            "target_class": sighting.target_class,
            "confidence": sighting.confidence,
            "backend": sighting.backend,
            "frame_timestamp": sighting.frame_timestamp,
            "latitude": sighting.latitude,
            "longitude": sighting.longitude,
            "position_error_m": sighting.position_error_m,
            "projection_inputs": sighting.projection_inputs,
            "error_metres": error_metres,
            "truth_point_id": point_id,
            "crop": crop_name,
        })
        self.kept += 1

    def note_truth_point(self, point) -> None:
        """Write a truth point down, so the errors in the file can be re-done."""
        self.write({
            "record": TRUTH_POINT_RECORD,
            "point_id": point.point_id,
            "target_class": point.target_class,
            "latitude": point.latitude,
            "longitude": point.longitude,
        })

    def note_truth_point_removed(self, point_id: str) -> None:
        self.write({"record": TRUTH_POINT_REMOVED_RECORD, "point_id": point_id})

    def write_crop(self, sighting, image_bytes: bytes):
        """Put the crop beside the log. Returns its name, or None if it failed."""
        decimals = TEST_SIGHTING_LOG["confidence_decimals"]
        confidence = f"{sighting.confidence:.{decimals}f}".replace(
            ".", TEST_SIGHTING_LOG["decimal_separator"]
        )
        crop_name = TEST_SIGHTING_LOG["crop_name_format"].format(
            sighting_id=sighting.sighting_id,
            target_class=sighting.target_class,
            confidence=confidence,
        )
        try:
            (self.folder / crop_name).write_bytes(image_bytes)
        except OSError as error:
            logger.warning(f"The crop of sighting {sighting.sighting_id} was not "
                           f"kept: {error}")
            return None
        return crop_name

    def write(self, record: dict) -> None:
        """One line of JSON, flushed at once so a crash keeps what came before."""
        if not self.open():
            return
        try:
            self.log_file.write(json.dumps({"received": time.time(), **record}) + "\n")
            self.log_file.flush()
        except (OSError, TypeError, ValueError) as error:
            logger.warning(f"A sighting record was not written: {error}")

    def close(self) -> None:
        if self.log_file is None:
            return
        self.log_file.close()
        self.log_file = None
        logger.info(f"{self.kept} sightings kept in {self.folder}.")
