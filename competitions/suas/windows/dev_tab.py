"""The window's tabs, the DEV tab among them, and the link test it starts.

The operations window is the MISSION tab, and the CALIBRATION tab sits beside
it: the calibrations are run on the bench and before takeoff, never in flight.
Developer mode adds the bench tools on TEST and DEV tabs after them. The map is
hidden while any other tab shows, which is accepted then and never happens in
front of a judge: in flight the operator stays on MISSION.

The link test's probes cross the broker, so the window sends them through the
controller and this is where the result comes back; DIAGNOSE reads that
result and the tab's last ping test together.

A mixin on SuasMainWindow, so these keep using self.controller and
self.developer_mode.
"""

import time

from PyQt6.QtWidgets import QTabWidget, QWidget

from competitions.suas.config import (
    DEVELOPER_NETWORK,
    DEVELOPER_TEXT,
    SAFETY_MAVLINK_ENDPOINT,
    SAFETY_SIMULATION_ENDPOINT,
    TABS_TEXT,
    TEST_TAB_TITLE,
)
from competitions.suas.dev import LinkProbe, LinkTestResult, ProbeResult, diagnose
from competitions.suas.widgets.dev_panel import DevPanel
from competitions.suas.widgets.link_test_dialog import LinkTestDialog
from theme import fade_in

MILLISECONDS_PER_SECOND = 1000


class DevTabMixin:
    """MISSION, CALIBRATION, TEST and DEV side by side, and the link test."""

    def wrap_in_tabs(self, mission_page: QWidget, calibration_page: QWidget) -> QWidget:
        """The mission and calibration pages as tabs, with the bench tabs after them."""
        self.dev_panel = None
        self.link_test_dialog = None
        self.link_probe = None
        self.last_link_result = None
        tabs = QTabWidget(self)
        tabs.addTab(mission_page, TABS_TEXT["mission_title"])
        tabs.addTab(calibration_page, TABS_TEXT["calibration_title"])
        tabs.currentChanged.connect(lambda index: fade_in(tabs.widget(index)))
        # Asked for even on a scored run, where it builds nothing and returns
        # nothing: the mission handlers check whether the bench pages are there
        # before they draw on them, and they can only check what exists.
        test_page = self.build_test_page()
        if not self.developer_mode:
            return tabs

        self.dev_panel = DevPanel(self)
        self.dev_panel.link_test_requested.connect(self.start_link_test)
        self.dev_panel.diagnose_requested.connect(self.diagnose_links)
        self.dev_panel.simulation_changed.connect(self.point_safety_link)
        self.point_safety_link(self.dev_panel.simulation_checkbox.isChecked())
        self.link_test_dialog = LinkTestDialog(self)
        self.link_test_dialog.retest_requested.connect(self.start_link_test)
        self.link_test_dialog.diagnose_requested.connect(self.diagnose_links)

        # TEST is the bench pages onto the mission's own machinery; DEV is the
        # machine the machinery runs on. Both are bench equipment rather than
        # flight controls, so both go after the operations pages.
        if test_page is not None:
            tabs.addTab(test_page, TEST_TAB_TITLE)
        tabs.addTab(self.dev_panel, DEVELOPER_TEXT["tab_title"])
        return tabs

    def point_safety_link(self, simulating: bool) -> None:
        """Which MAVLink endpoint the safety link dials.

        There is no RFD900x on a bench, so holding its serial port open in
        simulation only produces an error every two seconds. The tab is built
        before the link is started, so this also decides where it opens.
        """
        if simulating:
            self.safety_link.use_endpoint(SAFETY_SIMULATION_ENDPOINT)
            return
        self.safety_link.use_endpoint(SAFETY_MAVLINK_ENDPOINT)

    # The link test

    def start_link_test(self) -> None:
        if self.link_probe is not None:
            return  # one at a time
        self.link_test_dialog.show_running()
        self.link_probe = LinkProbe(self.controller, self)
        self.link_probe.finished.connect(self.link_probe_finished)
        self.link_probe.start()
        self.dev_panel.append_output(DEVELOPER_TEXT["link_test_started"].format(
            count=DEVELOPER_NETWORK["probe_count"]
        ))

    def link_probe_finished(self, probes: ProbeResult) -> None:
        self.link_probe.deleteLater()
        self.link_probe = None
        self.last_link_result = self.link_test_result(probes)
        self.link_test_dialog.show_result(self.last_link_result)

    def link_test_result(self, probes: ProbeResult) -> LinkTestResult:
        """The probes, and how every other link looks right now."""
        controller = self.controller
        return LinkTestResult(
            probes,
            seconds_or_none(controller.vehicle.telemetry_age_milliseconds()),
            seconds_or_none(controller.links.safety.age_milliseconds()),
            controller.mqtt_client.is_connected,
            age_since(controller.camera.frame_received_monotonic),
            controller.links.mission_is_up(),
            controller.links.safety_is_up(),
        )

    def diagnose_links(self) -> None:
        """Read the last ping test and link test and say what they mean."""
        reasons = diagnose(self.dev_panel.last_report, self.last_link_result)
        self.dev_panel.show_diagnosis(reasons)
        self.link_test_dialog.show_diagnosis(reasons)

    def refresh_flying_state(self) -> None:
        """The link test loads the mission link, so it is refused while the aircraft is armed."""
        if self.dev_panel is None:
            return
        flying = bool(self.controller.vehicle.armed)
        self.dev_panel.set_mission_active(flying)
        self.link_test_dialog.set_mission_active(flying)

    def stop_developer_sessions(self) -> None:
        """Kill every process the DEV tab started, before the window goes away."""
        if self.link_probe is not None:
            self.link_probe.stop()
        if self.dev_panel is not None:
            self.dev_panel.stop_sessions()


def seconds_or_none(milliseconds: float | None) -> float | None:
    if milliseconds is None:
        return None
    return milliseconds / MILLISECONDS_PER_SECOND


def age_since(monotonic_time: float | None) -> float | None:
    if monotonic_time is None:
        return None
    return time.monotonic() - monotonic_time
