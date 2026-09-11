"""The TEST tab's half of the bus: the bench reports, and the state they build.

The TEST tab is not a separate system. Every press it makes reaches the code the
scored mission runs — the same recorder, the same camera, the same detector, the
same route planner, the same servos — and these topics are the finer-grained
reporting that a bench needs and a mission does not: where the gimbal is
actually looking, what is on the camera's card, where each servo was last
driven, which waypoint armed the scan, what the model scored on a frame it went
on to throw away.

So this is a second set of topics, never a second set of behaviour. If a bench
press ever needs something the mission code cannot do, the mission code is what
changes.

**This application never talks to the aircraft, and neither does the TEST tab.**
It connects to the broker on the ground services machine, and ``computer/relay``
is the only thing joined to both that broker and the aircraft's Rocket link. So
a press reaches the aircraft when the ground services carry it, and a report
arrives when they carried it back — which is why nothing here treats a silence
as the aircraft's fault. It could be any of the four.

It lives beside ``suas_controller.py`` rather than in it because that file was
already full, and it shares the broker connection rather than opening a second
one: one client, one set of subscriptions, and the controller hands a message
down here when the topic is one of these.

The one thing this does that no other part of the bus does is put a file on
disk. A 4K still is several megabytes, so it arrives in pieces, and something
has to hold the pieces and write the file when the last one lands. That is
transport work rather than something a widget should know about, so it happens
here and the panel is only told where the file went.

Callbacks fire on the MQTT network thread. The window bridges them onto the Qt
thread; nothing here touches a widget.
"""

import logging
from pathlib import Path

from competitions.suas.config import (
    KEY_SIGHTING_IMAGE,
    TEST_TRANSFER_TEXT,
    TOPIC_CAMERA_MEDIA_CHUNK,
    TOPIC_CAMERA_MEDIA_LIST,
    TOPIC_CAMERA_TRANSFER,
    TOPIC_DETECTOR_SIGHTING,
    TOPIC_DETECTOR_STATE,
    TOPIC_GIMBAL_STATE,
    TOPIC_MAPPING_PROGRESS,
    TOPIC_PAYLOAD_SERVO,
    TOPIC_WAYPOINT_WATCH,
    competition_path,
)
from competitions.suas.controller.test_commands import TestCommandsMixin
from competitions.suas.controller.wire_values import decode_image
from competitions.suas.models import (
    DetectorState, GimbalState, MappingCaptureState, MediaLibraryState,
    ServoState, Sighting, WaypointWatchState,
)

logger = logging.getLogger(__name__)

# The topics this half of the bus owns. The controller subscribes to them with
# the rest and hands anything on this list straight down.
#
# The route the aircraft plans is not here, and neither is the payload state or
# the stitch. Those arrive on the mission's own topics and the bench pages read
# the same ones -- a second copy would be a second answer to the same question.
TEST_TOPICS = (
    TOPIC_GIMBAL_STATE,
    TOPIC_CAMERA_MEDIA_LIST,
    TOPIC_CAMERA_MEDIA_CHUNK,
    TOPIC_CAMERA_TRANSFER,
    TOPIC_PAYLOAD_SERVO,
    TOPIC_WAYPOINT_WATCH,
    TOPIC_MAPPING_PROGRESS,
    TOPIC_DETECTOR_STATE,
    TOPIC_DETECTOR_SIGHTING,
)


class TestBus(TestCommandsMixin):
    """The bench topics: what the aircraft reports, and what the TEST tab sends."""

    def __init__(self, mqtt_client, next_command_id) -> None:
        """Wire the bench half to the broker connection the mission bus opened.

        Parameters:
            mqtt_client (MqttClient): The shared connection.
            next_command_id (callable): The controller's id maker, so a press
                from this tab is numbered in the same sequence as every other
                press and its acknowledgement is told apart the same way.
        """
        self.mqtt_client = mqtt_client
        self.next_command_id = next_command_id

        self.gimbal = GimbalState()
        self.media = MediaLibraryState()
        self.servos = ServoState()
        self.waypoint_watch = WaypointWatchState()
        self.mapping_capture = MappingCaptureState()
        self.detector = DetectorState()

        # The press each page is waiting to hear about, kept per page so an
        # answer to a camera press does not land in the waypoint monitor.
        self.pending_camera_command_id: str | None = None
        self.pending_gimbal_command_id: str | None = None
        self.pending_watch_command_id: str | None = None
        self.pending_mapping_command_id: str | None = None
        self.pending_detector_command_id: str | None = None
        self.pending_route_command_id: str | None = None

        self.on_gimbal_changed = None       # callable()
        self.on_media_list_changed = None   # callable()
        self.on_transfer_changed = None     # callable()
        self.on_media_file_saved = None     # callable(file_name, path)
        self.on_servos_changed = None       # callable()
        self.on_waypoint_watch_changed = None  # callable()
        self.on_mapping_progress = None     # callable()
        self.on_detector_changed = None     # callable()
        # The crop crosses as bytes for the same reason a detection card's
        # does: building a picture is a Qt operation and this is the network
        # thread.
        self.on_sighting = None             # callable(image_bytes, sighting)

        self.on_camera_test_answered = None   # callable(status, reason)
        self.on_gimbal_answered = None        # callable(status, reason)
        self.on_watch_answered = None         # callable(status, reason)
        self.on_mapping_answered = None       # callable(status, reason)
        self.on_detector_answered = None      # callable(status, reason)
        self.on_route_answered = None         # callable(status, reason)

    # Incoming

    def handles(self, topic: str) -> bool:
        return topic in TEST_TOPICS

    def route(self, topic: str, payload: dict) -> None:
        """Take one message off the bench half of the bus."""
        if topic == TOPIC_GIMBAL_STATE:
            self.handle_gimbal_state(payload)
        elif topic == TOPIC_CAMERA_MEDIA_LIST:
            self.handle_media_list(payload)
        elif topic == TOPIC_CAMERA_MEDIA_CHUNK:
            self.handle_media_chunk(payload)
        elif topic == TOPIC_CAMERA_TRANSFER:
            self.handle_transfer(payload)
        elif topic == TOPIC_PAYLOAD_SERVO:
            self.handle_servos(payload)
        elif topic == TOPIC_WAYPOINT_WATCH:
            self.handle_waypoint_watch(payload)
        elif topic == TOPIC_MAPPING_PROGRESS:
            self.handle_mapping_progress(payload)
        elif topic == TOPIC_DETECTOR_STATE:
            self.handle_detector_state(payload)
        elif topic == TOPIC_DETECTOR_SIGHTING:
            self.handle_sighting(payload)

    def handle_gimbal_state(self, payload: dict) -> None:
        self.gimbal.update_from(payload)
        if self.on_gimbal_changed:
            self.on_gimbal_changed()

    def handle_media_list(self, payload: dict) -> None:
        self.media.update_list_from(payload)
        if self.on_media_list_changed:
            self.on_media_list_changed()

    def handle_media_chunk(self, payload: dict) -> None:
        """Collect one piece of a file, and write the file when the last lands.

        Nothing is reported between pieces. The bar is drawn from the transfer
        message the aircraft sends alongside these, which knows the whole copy
        rather than one file of it.
        """
        finished = self.media.add_chunk(payload)
        if finished is None:
            return

        file_name, file_bytes = finished
        saved_path = self.save_media_file(file_name, file_bytes)
        if saved_path is None:
            return
        if self.on_media_file_saved:
            self.on_media_file_saved(file_name, saved_path)

    def save_media_file(self, file_name: str, file_bytes: bytes) -> Path | None:
        """Put one file off the camera's card on this laptop's disk.

        A file that cannot be written is logged and dropped rather than raised:
        this is the network thread, and a full disk should cost the copy rather
        than the rest of the bus.
        """
        folder = competition_path(TEST_TRANSFER_TEXT["download_folder"])
        try:
            folder.mkdir(parents=True, exist_ok=True)
            saved_path = folder / Path(file_name).name
            saved_path.write_bytes(file_bytes)
        except OSError as error:
            logger.error(f"Could not save '{file_name}' off the camera's card: {error}")
            return None

        logger.info(f"Saved '{file_name}' from the camera's card to {saved_path}.")
        return saved_path

    def handle_transfer(self, payload: dict) -> None:
        self.media.update_transfer_from(payload)
        if self.on_transfer_changed:
            self.on_transfer_changed()

    def handle_servos(self, payload: dict) -> None:
        self.servos.update_from(payload)
        if self.on_servos_changed:
            self.on_servos_changed()

    def handle_waypoint_watch(self, payload: dict) -> None:
        self.waypoint_watch.update_from(payload)
        if self.on_waypoint_watch_changed:
            self.on_waypoint_watch_changed()

    def handle_mapping_progress(self, payload: dict) -> None:
        self.mapping_capture.update_from(payload)
        if self.on_mapping_progress:
            self.on_mapping_progress()

    def handle_detector_state(self, payload: dict) -> None:
        self.detector.update_from(payload)
        if self.on_detector_changed:
            self.on_detector_changed()

    def handle_sighting(self, payload: dict) -> None:
        """One thing the model saw, whatever the aircraft went on to make of it."""
        sighting = Sighting(payload)
        if self.on_sighting:
            self.on_sighting(decode_image(payload.get(KEY_SIGHTING_IMAGE)), sighting)

    def handle_acknowledgement(self, command_id: str, status: str, reason: str) -> bool:
        """Answer whichever page was waiting for this press.

        Returns:
            bool: True when the id belonged to one of these pages, so the
            mission bus knows it has been dealt with.
        """
        answers = (
            ("pending_camera_command_id", self.on_camera_test_answered),
            ("pending_gimbal_command_id", self.on_gimbal_answered),
            ("pending_watch_command_id", self.on_watch_answered),
            ("pending_mapping_command_id", self.on_mapping_answered),
            ("pending_detector_command_id", self.on_detector_answered),
            ("pending_route_command_id", self.on_route_answered),
        )

        for pending_name, answered in answers:
            if command_id != getattr(self, pending_name):
                continue
            setattr(self, pending_name, None)
            if answered:
                answered(status, reason)
            return True

        return False
