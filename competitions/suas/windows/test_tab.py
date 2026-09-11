"""The TEST tab: five bench pages onto the same machinery the mission flies.

Nothing on these pages is a bench copy of anything. A HOLD press here is the
same press the delivery makes, a mapping toggle starts the capture the survey
starts, a detector threshold set here is the threshold the aircraft searches
with, and a route to a place you typed is planned by the planner a found target
would have used. That is the whole point of the tab: a thing proved on it is
proved for the flight, because it is the same code underneath. Anything that
cannot be tested that way is a gap in the mission code, not a reason to write a
second version beside it.

The pages open one at a time and can be dragged into whatever order a
particular test wants. Each one writes its own log file, opened the first time
the page is shown — see ``test_log.py`` for why.

It covers the map, so it exists only in developer mode, the same rule the DEV
tab lives by and for the same reason: §3.0.6 makes an uncovered map a condition
of taking off, and a judge never sees this page.

A mixin on SuasMainWindow, so these keep using self.controller and the
signals the window already hops onto the Qt thread. The presses and the answers
to them live next door in ``test_presses.py``.
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QScrollArea, QTabWidget

from competitions.suas.config import TEST_PAGE_TITLES, TEST_TAB_ENABLED
from competitions.suas.models import TruthPointStore
from competitions.suas.sighting_log import SightingLog
from competitions.suas.widgets.test import (
    CameraTestPanel, DetectionTestPanel, MappingTestPanel, ServoTestPanel,
    WaypointMonitorPanel,
)
from competitions.suas.windows.test_log import TestPageLog
from theme import fade_in

logger = logging.getLogger(__name__)

# The pages, in the order they open in. The operator can drag them; this is
# only where they start.
PAGE_CAMERA = "camera"
PAGE_DROP = "drop"
PAGE_MAPPING = "mapping"
PAGE_WAYPOINTS = "waypoints"
PAGE_DETECTION = "detection"

PAGE_ORDER = (PAGE_CAMERA, PAGE_DROP, PAGE_MAPPING, PAGE_WAYPOINTS,
              PAGE_DETECTION)


class TestTabMixin:
    """Builds the TEST tab's pages and wires them to the mission's own bus."""

    def build_test_page(self):
        """The TEST tab, or nothing when this is not a bench run.

        Returns:
            QTabWidget or None: The page to put beside MISSION, or ``None``
            when the tab is switched off or the interface was not started in
            developer mode.
        """
        self.test_pages = None
        self.test_logs = {}
        self.truth_points = TruthPointStore()
        self.sighting_log = SightingLog()
        self.pending_test_commands = {}
        if not self.developer_mode or not TEST_TAB_ENABLED:
            return None

        self.camera_test_panel = CameraTestPanel(self)
        self.servo_test_panel = ServoTestPanel(self)
        self.mapping_test_panel = MappingTestPanel(self)
        self.waypoint_monitor_panel = WaypointMonitorPanel(self)
        self.detection_test_panel = DetectionTestPanel(self)

        self.test_panels = {
            PAGE_CAMERA: self.camera_test_panel,
            PAGE_DROP: self.servo_test_panel,
            PAGE_MAPPING: self.mapping_test_panel,
            PAGE_WAYPOINTS: self.waypoint_monitor_panel,
            PAGE_DETECTION: self.detection_test_panel,
        }

        self.test_pages = QTabWidget(self)
        # Draggable, because which test matters changes from one bench day to
        # the next and the order they sit in should follow that.
        self.test_pages.setMovable(True)
        for page_key in PAGE_ORDER:
            self.test_pages.addTab(scrolling(self.test_panels[page_key], self),
                                   TEST_PAGE_TITLES[page_key])
        self.test_pages.currentChanged.connect(self.show_test_page)

        self.connect_test_pages()
        self.open_test_log(PAGE_ORDER[0])
        return self.test_pages

    # The per-test logs

    def show_test_page(self, index: int) -> None:
        """Fade the page in, and start its log the first time it is opened.

        The fade goes on the panel and never on the scroll area around it. A
        graphics effect on a scrolling widget draws the whole thing empty --
        which looked exactly like a page whose buttons had not been built.
        """
        panel = self.test_pages.widget(index).widget()
        fade_in(panel)
        self.open_test_log(self.page_key_of(panel))

    def page_key_of(self, panel) -> str:
        for page_key, page_panel in self.test_panels.items():
            if page_panel is panel:
                return page_key
        return ""

    def open_test_log(self, page_key: str) -> None:
        """One log file per test, opened once and kept for the session."""
        if not page_key or page_key in self.test_logs:
            return
        self.test_logs[page_key] = TestPageLog(page_key)

    def note_test(self, page_key: str, text: str) -> None:
        page_log = self.test_logs.get(page_key)
        if page_log is not None:
            page_log.note(text)

    def note_test_problem(self, page_key: str, text: str) -> None:
        page_log = self.test_logs.get(page_key)
        if page_log is not None:
            page_log.note_problem(text)

    def close_test_logs(self) -> None:
        for page_log in self.test_logs.values():
            page_log.close()
        self.test_logs = {}
        self.sighting_log.close()

    # Wiring

    def connect_test_pages(self) -> None:
        """Point every press at the code the mission already runs."""
        self.connect_camera_test()
        self.connect_drop_test()
        self.connect_mapping_test()
        self.connect_waypoint_test()
        self.connect_detection_test()
        self.connect_test_reports()

    def connect_camera_test(self) -> None:
        camera = self.camera_test_panel
        for column in (camera.stream_column, camera.card_column):
            column.command_requested.connect(self.send_camera_test_command)
            column.photo_timer_requested.connect(self.send_camera_photo_timer)
        camera.card_column.fetch_requested.connect(self.fetch_camera_files)

        camera.gimbal_bar.point_requested.connect(self.point_gimbal)
        camera.gimbal_bar.zoom_requested.connect(self.zoom_gimbal)
        camera.gimbal_bar.centre_requested.connect(self.centre_gimbal)
        camera.gimbal_bar.stop_requested.connect(self.stop_gimbal)

        camera.transfer_bar.send_toggled.connect(self.send_camera_test_command)
        camera.transfer_bar.open_folder_requested.connect(self.open_download_folder)

    def connect_drop_test(self) -> None:
        # HOLD and RELEASE are the mission's own presses, not bench ones: the
        # same command, the same servo, the same acknowledgement.
        self.servo_test_panel.hold_requested.connect(self.hold_payload)
        self.servo_test_panel.release_requested.connect(self.release_payload)
        self.servo_test_panel.plan_requested.connect(self.plan_route_to_place)
        self.servo_test_panel.plan_and_drop_requested.connect(self.drop_on_a_place)
        self.servo_test_panel.approve_requested.connect(self.approve_route)
        self.servo_test_panel.reject_requested.connect(self.reject_route)

    def connect_mapping_test(self) -> None:
        self.mapping_test_panel.capture_toggled.connect(self.toggle_mapping_capture)
        # The stitch is the ground services' work and goes out on the topic the
        # mapping panel already uses. An empty path means the session they have
        # just been filling from the air.
        self.mapping_test_panel.stitch_requested.connect(
            self.controller.send_stitch_request)
        self.mapping_test_panel.export_requested.connect(
            self.controller.send_export_request)
        self.mapping_test_panel.open_folder_requested.connect(
            self.open_mapping_folder)

    def connect_waypoint_test(self) -> None:
        panel = self.waypoint_monitor_panel
        panel.set_start_requested.connect(self.set_scan_start_waypoint)
        panel.set_finish_requested.connect(self.set_scan_finish_waypoint)
        panel.clear_requested.connect(self.clear_scan_waypoints)

    def connect_detection_test(self) -> None:
        panel = self.detection_test_panel
        panel.start_requested.connect(self.start_detector)
        panel.stop_requested.connect(self.stop_detector)
        panel.backend_requested.connect(self.choose_detector)
        panel.confidence_requested.connect(self.set_detector_confidence)
        panel.truth_table.truth_point_added.connect(self.add_truth_point)
        panel.truth_table.truth_point_removed.connect(self.remove_truth_point)

    def connect_test_reports(self) -> None:
        """Everything the aircraft says about the bench, onto the Qt thread."""
        test_bus = self.controller.test
        test_bus.on_gimbal_changed = self.gimbal_changed.emit
        test_bus.on_media_list_changed = self.media_list_changed.emit
        test_bus.on_transfer_changed = self.transfer_changed.emit
        test_bus.on_media_file_saved = self.media_file_saved.emit
        test_bus.on_servos_changed = self.servos_changed.emit
        test_bus.on_waypoint_watch_changed = self.waypoint_watch_changed.emit
        test_bus.on_mapping_progress = self.mapping_progress_received.emit
        test_bus.on_detector_changed = self.detector_changed.emit
        test_bus.on_sighting = self.sighting_received.emit

        test_bus.on_camera_test_answered = self.camera_test_answered.emit
        test_bus.on_gimbal_answered = self.gimbal_answered.emit
        test_bus.on_watch_answered = self.watch_answered.emit
        test_bus.on_mapping_answered = self.mapping_test_answered.emit
        test_bus.on_detector_answered = self.detector_answered.emit
        test_bus.on_route_answered = self.route_answered.emit

        self.gimbal_changed.connect(self.handle_gimbal_changed)
        self.media_list_changed.connect(self.handle_media_list_changed)
        self.transfer_changed.connect(self.handle_transfer_changed)
        self.media_file_saved.connect(self.handle_media_file_saved)
        self.servos_changed.connect(self.handle_servos_changed)
        self.waypoint_watch_changed.connect(self.handle_waypoint_watch_changed)
        self.mapping_progress_received.connect(self.handle_mapping_progress)
        self.detector_changed.connect(self.handle_detector_changed)
        self.sighting_received.connect(self.handle_sighting)

        self.camera_test_answered.connect(self.handle_camera_test_answer)
        self.gimbal_answered.connect(self.handle_gimbal_answer)
        self.watch_answered.connect(self.handle_watch_answer)
        self.mapping_test_answered.connect(self.handle_mapping_test_answer)
        self.detector_answered.connect(self.handle_detector_answer)
        self.route_answered.connect(self.handle_route_answer)

    # What the aircraft reports, already on the Qt thread

    def handle_gimbal_changed(self) -> None:
        if self.test_pages is None:
            return
        self.camera_test_panel.gimbal_bar.show_gimbal(self.controller.test.gimbal)

    def handle_media_list_changed(self) -> None:
        if self.test_pages is None:
            return
        media = self.controller.test.media
        self.camera_test_panel.card_column.show_media_list(media)
        self.note_test(PAGE_CAMERA,
                       f"The camera's card holds {len(media.files)} files.")

    def handle_transfer_changed(self) -> None:
        if self.test_pages is None:
            return
        media = self.controller.test.media
        self.camera_test_panel.transfer_bar.show_transfer(media)
        self.camera_test_panel.transfer_bar.show_sending(media.sending_photos,
                                                         media.sending_videos)
        self.camera_test_panel.card_column.show_watching(media.watching)

    def handle_media_file_saved(self, file_name: str, path) -> None:
        self.note_test(PAGE_CAMERA, f"Saved {file_name} to {path}.")

    def handle_servos_changed(self) -> None:
        if self.test_pages is None:
            return
        self.servo_test_panel.show_servos(self.controller.test.servos)

    def handle_waypoint_watch_changed(self) -> None:
        if self.test_pages is None:
            return
        watch = self.controller.test.waypoint_watch
        self.waypoint_monitor_panel.show_watch(watch)
        if watch.has_triggered():
            self.note_test(PAGE_WAYPOINTS,
                           f"The scan was triggered '{watch.triggered}' on "
                           f"item {watch.triggered_index}.")

    def handle_mapping_progress(self) -> None:
        if self.test_pages is None:
            return
        self.mapping_test_panel.show_capture(self.controller.test.mapping_capture)

    def handle_detector_changed(self) -> None:
        if self.test_pages is None:
            return
        detector = self.controller.test.detector
        self.detection_test_panel.show_detector(detector)
        self.detection_test_panel.show_fallback(detector)
        if detector.fell_back():
            self.note_test_problem(
                PAGE_DETECTION,
                f"Asked for {detector.requested_backend}, "
                f"running {detector.backend}."
            )

    def handle_sighting(self, image_bytes: bytes, sighting) -> None:
        """One thing the model saw: onto the list, into the error sums, and
        onto the disk with how far out it was."""
        if self.test_pages is None:
            return
        self.detection_test_panel.sighting_column.add_sighting(
            self.crop_pixmap(image_bytes), sighting
        )
        self.truth_points.note_sighting(sighting)
        self.detection_test_panel.truth_table.show_errors(self.truth_points)
        error_metres, point_id = self.truth_points.error_of(sighting)
        self.sighting_log.note_sighting(sighting, image_bytes, error_metres,
                                        point_id)

    # The mission's own reports, repeated onto the bench pages

    def show_test_video_frame(self, picture) -> None:
        if self.test_pages is None:
            return
        self.camera_test_panel.show_frame(picture)

    def show_test_no_picture(self, has_had_one: bool) -> None:
        if self.test_pages is None:
            return
        self.camera_test_panel.show_no_picture(has_had_one)

    def show_test_stations(self) -> None:
        if self.test_pages is None:
            return
        self.servo_test_panel.show_stations(self.controller.payload)

    def show_test_route(self) -> None:
        if self.test_pages is None:
            return
        self.servo_test_panel.show_route(self.controller.route)

    def show_test_waypoint_progress(self) -> None:
        if self.test_pages is None:
            return
        self.waypoint_monitor_panel.show_progress(
            self.controller.waypoint_index,
            self.controller.waypoint_total,
            self.controller.waypoint_distance_metres,
        )

    def show_test_stitch(self, preview) -> None:
        if self.test_pages is None:
            return
        self.mapping_test_panel.show_stitch(self.controller.stitch, preview)

    def refresh_test_pages(self) -> None:
        """The clocks and staleness that keep moving with no new message."""
        if self.test_pages is None:
            return
        if not self.controller.test.gimbal.is_live():
            self.camera_test_panel.gimbal_bar.show_stale()
        self.mapping_test_panel.refresh_clock(self.controller.stitch)
        self.refresh_test_commands()


def scrolling(panel, parent) -> QScrollArea:
    """One page, in something that scrolls rather than squeezing it.

    A bench page carries more controls than a mission screen and the window is
    whatever size the laptop is. Without this Qt shrinks the controls below the
    size they can draw in and they end up on top of each other -- the same
    failure the mission window's side column already has a scroll area for.

    It scrolls both ways. A page narrower than its own controls is worth a
    horizontal bar: the alternative is a row of buttons drawn over itself.
    """
    area = QScrollArea(parent)
    area.setWidget(panel)
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    return area
