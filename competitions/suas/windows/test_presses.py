"""Every press the TEST tab makes, and what came back about it.

Split out of ``test_tab.py`` because it is one subject and one file was not
enough to read both in. It is a mixin for the same reason the rest of the window
is: the methods keep their own names, and the signals connected in
``test_tab.py`` point straight at them.

**Nothing here reaches the aircraft.** A press is published on the broker on the
ground services machine; ``computer/relay`` is the only thing joined to both
that broker and the aircraft's Rocket link, and it carries the press over and
the acknowledgement back. So a press crosses four things, and that is what makes
the answers worth being careful about:

    a press taken, or refused with a reason   the aircraft did that, and the
                                              acknowledgement is the proof
    no answer at all                          the broker, the ground services,
                                              the Rocket link or the aircraft.
                                              We do not know which, and a
                                              message that says "the aircraft"
                                              sends somebody to the wrong box.

So every press starts a clock, and a press nobody answered is said out loud
rather than left sitting there looking like it worked — without guessing where
the silence came from.

Two of these presses are not this tab's at all. HOLD and RELEASE on the drop
page are the mission's own delivery commands, sent through the mission
controller and answered on the mission's own acknowledgement — which is the
point: proving a bay opens here proves the bay opens on the day.
"""

import logging

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from competitions.suas.config import (
    ACK_REJECTED,
    CAMERA_TEST_ACTIONS,
    DETECTOR_ACTIONS,
    GIMBAL_ACTIONS,
    REFRESH_INTERVAL_MS,
    ROUTE_ACTIONS,
    TEST_COMMAND_ACK_TIMEOUT_MS,
    TEST_TRANSFER_TEXT,
    WATCH_ACTIONS,
    competition_path,
)
from competitions.suas.windows.test_tab import (
    PAGE_CAMERA, PAGE_DETECTION, PAGE_DROP, PAGE_MAPPING, PAGE_WAYPOINTS,
)

logger = logging.getLogger(__name__)

# What a silence actually tells us. Written once because it goes in the page's
# own log and in the application's, and because the list of places to look is
# the whole value of the line.
NO_ANSWER_NOTE = ("No answer came back. It crosses the broker, the ground "
                  "services, the Rocket link and the aircraft, so the gap may "
                  "be at any of the four.")


class TestPressesMixin:
    """The TEST tab's outgoing presses and the answers to them."""

    # The camera page

    def send_camera_test_command(self, action: str) -> None:
        """One press of either column, or one of the send-to-GCS toggles."""
        self.controller.test.send_camera_test_command(action)
        self.begin_test_command(PAGE_CAMERA, self.sender(), f"camera '{action}'")

    def send_camera_photo_timer(self, action: str, rate_hz: float) -> None:
        self.controller.test.send_camera_test_command(action, rate_hz=rate_hz)
        self.begin_test_command(PAGE_CAMERA, self.sender(),
                                f"camera '{action}' at {rate_hz} Hz")

    def fetch_camera_files(self, file_names: list) -> None:
        """Copy files off the camera's card, or everything not here yet.

        An empty list is not an empty request: it means the aircraft chooses,
        which is what somebody wants after a burst of stills they did not pick
        through.
        """
        self.controller.test.send_camera_test_command(
            CAMERA_TEST_ACTIONS["card_fetch_files"], file_names=file_names
        )
        self.begin_test_command(PAGE_CAMERA, self.sender(),
                                f"fetch {len(file_names) or 'every new'} file(s)")

    def point_gimbal(self, yaw_degrees: float, pitch_degrees: float) -> None:
        self.controller.test.send_gimbal_command(
            GIMBAL_ACTIONS["point"], yaw_degrees=yaw_degrees,
            pitch_degrees=pitch_degrees,
        )
        self.begin_gimbal_command(f"point to yaw {yaw_degrees}, "
                                  f"pitch {pitch_degrees}")

    def zoom_gimbal(self, zoom: float) -> None:
        self.controller.test.send_gimbal_command(GIMBAL_ACTIONS["zoom_to"],
                                                 zoom=zoom)
        self.begin_gimbal_command(f"zoom to {zoom}")

    def centre_gimbal(self) -> None:
        self.controller.test.send_gimbal_command(GIMBAL_ACTIONS["centre"])
        self.begin_gimbal_command("centre")

    def stop_gimbal(self) -> None:
        self.controller.test.send_gimbal_command(GIMBAL_ACTIONS["stop"])
        self.begin_gimbal_command("stop")

    def begin_gimbal_command(self, description: str) -> None:
        """The gimbal answers on its own line, under its own controls."""
        self.begin_test_command(PAGE_CAMERA,
                                self.camera_test_panel.gimbal_bar,
                                f"gimbal {description}")

    def open_download_folder(self) -> None:
        """Show the operator where the files off the camera's card landed."""
        folder = competition_path(TEST_TRANSFER_TEXT["download_folder"])
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    # The drop page

    def plan_route_to_place(self, latitude: float, longitude: float,
                            altitude_metres: float, station: str,
                            radius_metres: float) -> None:
        """Ask for a route to a place the operator typed. Nothing moves yet."""
        self.send_place_command(ROUTE_ACTIONS["plan"], "plan a route",
                                latitude, longitude, altitude_metres, station,
                                radius_metres)

    def drop_on_a_place(self, latitude: float, longitude: float,
                        altitude_metres: float, station: str,
                        radius_metres: float) -> None:
        """Go there and drop, with nobody asked in between.

        The same plan and the same flight as the two presses beside it, minus
        the pause where somebody looks at the route -- which is worth a line of
        its own in the test's log, because it is the difference between a
        delivery that was checked and one that was not.
        """
        self.send_place_command(ROUTE_ACTIONS["plan_and_drop"],
                                "go and drop, unreviewed", latitude, longitude,
                                altitude_metres, station, radius_metres)

    def send_place_command(self, action: str, description: str, latitude: float,
                           longitude: float, altitude_metres: float,
                           station: str, radius_metres: float) -> None:
        """One press of either button under the place, and the clock on it."""
        self.controller.test.send_route_command(
            action, latitude=latitude, longitude=longitude,
            altitude_metres=altitude_metres, radius_metres=radius_metres,
            station=station,
        )
        self.begin_test_command(
            PAGE_DROP, self.servo_test_panel,
            f"{description}: {latitude:.7f}, {longitude:.7f} at "
            f"{altitude_metres} m for '{station}', arrived within "
            f"{radius_metres} m"
        )

    def approve_route(self, route_id: str) -> None:
        """Fly the route on offer and release on arrival."""
        self.controller.test.send_route_command(ROUTE_ACTIONS["approve"],
                                                route_id=route_id)
        self.begin_test_command(PAGE_DROP, self.servo_test_panel,
                                f"approve route {route_id}")

    def reject_route(self, route_id: str) -> None:
        self.controller.test.send_route_command(ROUTE_ACTIONS["reject"],
                                                route_id=route_id)
        self.begin_test_command(PAGE_DROP, self.servo_test_panel,
                                f"reject route {route_id}")

    def note_delivery_sent(self, command_id: str) -> None:
        """A HOLD or RELEASE went out on the mission's own command."""
        if self.test_pages is None:
            return
        self.servo_test_panel.show_command_sent()
        self.note_test(PAGE_DROP, f"delivery step {command_id} sent")

    def note_delivery_answer(self, status: str, reason: str) -> None:
        if self.test_pages is None:
            return
        if status == ACK_REJECTED:
            self.servo_test_panel.show_command_rejected(reason)
            self.note_test_problem(PAGE_DROP, f"refused by the aircraft: {reason}")
            return
        self.servo_test_panel.show_command_accepted()
        self.note_test(PAGE_DROP, f"the aircraft took it: {status}")

    def note_delivery_timeout(self) -> None:
        if self.test_pages is None:
            return
        self.servo_test_panel.show_command_timeout()
        self.note_test_problem(PAGE_DROP, NO_ANSWER_NOTE)

    # The mapping page

    def toggle_mapping_capture(self, action: str) -> None:
        """Start or stop the capture the survey would have started itself."""
        self.controller.test.send_mapping_command(action)
        self.begin_test_command(PAGE_MAPPING, self.mapping_test_panel,
                                f"mapping capture '{action}'")

    def open_mapping_folder(self) -> None:
        """Open the folder the ground services wrote the map into."""
        mosaic_path = self.controller.stitch.mosaic_path
        if not mosaic_path:
            return
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(competition_path(mosaic_path).parent))
        )

    # The waypoint monitor

    def set_scan_start_waypoint(self, waypoint_index: int) -> None:
        self.send_waypoint_watch(WATCH_ACTIONS["set_start"], waypoint_index)

    def set_scan_finish_waypoint(self, waypoint_index: int) -> None:
        self.send_waypoint_watch(WATCH_ACTIONS["set_finish"], waypoint_index)

    def clear_scan_waypoints(self) -> None:
        self.controller.test.send_waypoint_watch(WATCH_ACTIONS["clear"])
        self.begin_test_command(PAGE_WAYPOINTS, self.waypoint_monitor_panel,
                                "clear both scan waypoints")

    def send_waypoint_watch(self, action: str, waypoint_index: int) -> None:
        """Arm the scan on a mission item the operator picked.

        This is not a second way of starting the survey. It changes the item
        number the aircraft's own lap watch already compares against, so the
        scan still starts where it always did.
        """
        self.controller.test.send_waypoint_watch(action, waypoint_index)
        self.begin_test_command(PAGE_WAYPOINTS, self.waypoint_monitor_panel,
                                f"{action} on item {waypoint_index}")

    # The detection page

    def start_detector(self) -> None:
        self.send_detector_command(DETECTOR_ACTIONS["start"], "start detecting")

    def stop_detector(self) -> None:
        self.send_detector_command(DETECTOR_ACTIONS["stop"], "stop detecting")

    def choose_detector(self, backend: str) -> None:
        self.controller.test.send_detector_command(
            DETECTOR_ACTIONS["set_backend"], backend=backend
        )
        self.begin_test_command(PAGE_DETECTION, self.detection_test_panel,
                                f"use the {backend} detector")

    def set_detector_confidence(self, minimum_confidence: float) -> None:
        """Retune the detector the aircraft searches with, not a bench copy."""
        self.controller.test.send_detector_command(
            DETECTOR_ACTIONS["set_minimum_confidence"],
            minimum_confidence=minimum_confidence,
        )
        self.begin_test_command(PAGE_DETECTION, self.detection_test_panel,
                                f"score at least {minimum_confidence}")

    def send_detector_command(self, action: str, description: str) -> None:
        self.controller.test.send_detector_command(action)
        self.begin_test_command(PAGE_DETECTION, self.detection_test_panel,
                                description)

    def add_truth_point(self, target_class: str, latitude: float,
                        longitude: float) -> None:
        """Where an object really is. It never leaves this laptop."""
        point = self.truth_points.add(target_class, latitude, longitude)
        self.detection_test_panel.truth_table.show_errors(self.truth_points)
        self.sighting_log.note_truth_point(point)
        self.note_test(PAGE_DETECTION,
                       f"truth point {point.point_id}: {target_class} at "
                       f"{latitude:.7f}, {longitude:.7f}")

    def remove_truth_point(self, point_id: str) -> None:
        self.truth_points.remove(point_id)
        self.detection_test_panel.truth_table.show_errors(self.truth_points)
        self.sighting_log.note_truth_point_removed(point_id)
        self.note_test(PAGE_DETECTION, f"truth point {point_id} removed")

    # Waiting for the answer

    def begin_test_command(self, page_key: str, panel, description: str) -> None:
        """Start the clock on one press, and say on the page that it went."""
        self.pending_test_commands[page_key] = [0, panel]
        if panel is not None:
            panel.show_command_sent()
        self.note_test(page_key, f"sent: {description}")

    def answer_test_command(self, page_key: str, status: str,
                            reason: str) -> None:
        """Say what came back, refusal included."""
        pending = self.pending_test_commands.pop(page_key, None)
        panel = pending[1] if pending else None

        if status == ACK_REJECTED:
            if panel is not None:
                panel.show_command_rejected(reason)
            self.note_test_problem(page_key, f"refused: {reason}")
            return

        if panel is not None:
            panel.show_command_accepted()
        self.note_test(page_key, f"the aircraft took it: {status}")

    def handle_camera_test_answer(self, status: str, reason: str) -> None:
        self.answer_test_command(PAGE_CAMERA, status, reason)

    def handle_gimbal_answer(self, status: str, reason: str) -> None:
        self.answer_test_command(PAGE_CAMERA, status, reason)

    def handle_watch_answer(self, status: str, reason: str) -> None:
        self.answer_test_command(PAGE_WAYPOINTS, status, reason)

    def handle_mapping_test_answer(self, status: str, reason: str) -> None:
        self.answer_test_command(PAGE_MAPPING, status, reason)

    def handle_detector_answer(self, status: str, reason: str) -> None:
        self.answer_test_command(PAGE_DETECTION, status, reason)

    def handle_route_answer(self, status: str, reason: str) -> None:
        self.answer_test_command(PAGE_DROP, status, reason)

    def refresh_test_commands(self) -> None:
        """A press nobody answered stops looking like one that worked."""
        for page_key, pending in list(self.pending_test_commands.items()):
            pending[0] += REFRESH_INTERVAL_MS
            if pending[0] < TEST_COMMAND_ACK_TIMEOUT_MS:
                continue

            self.pending_test_commands.pop(page_key)
            panel = pending[1]
            if panel is not None:
                panel.show_command_timeout()
            self.note_test_problem(page_key, NO_ANSWER_NOTE)
            logger.warning(f"Nothing came back for the {page_key} test's last "
                           f"press. {NO_ANSWER_NOTE}")
