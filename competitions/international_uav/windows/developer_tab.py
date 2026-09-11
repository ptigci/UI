"""The window's tabs, the DEV tab among them, and the link test it starts.

The operations window is the MISSION tab and the CALIBRATION tab sits beside
it. Developer mode adds the bench tools on a DEV tab after them. The link test
goes over every link the mission uses, so the ground station runs it and this
is where the request leaves and the result comes back; DIAGNOSE reads that
result and the tab's last ping test together.

A mixin on InternationalMainWindow, so these keep using self.controller,
self.vehicles and self.log_panel.
"""

from PyQt6.QtWidgets import QTabWidget, QWidget

from competitions.international_uav.config import (
    DEVELOPER_TEXT,
    KEY_RESULT_FILE,
    KEY_RESULT_MESH_ROWS,
    LINK_TEST,
    LINK_TEST_DURATION_S,
    MISSION_ACTIVE_STATES,
    TABS_TEXT,
)
from competitions.international_uav.dev import agent_vehicle, diagnose, pasifik_vehicle
from competitions.international_uav.widgets.dev_panel import DevPanel
from competitions.international_uav.widgets.link_test_dialog import LinkTestDialog
from theme import fade_in


class DeveloperTabMixin:
    """MISSION, CALIBRATION and DEV side by side, and the link test between them."""

    def wrap_in_tabs(self, mission_page: QWidget, calibration_page: QWidget) -> QWidget:
        """The mission and calibration pages as tabs, with DEV after them in developer mode."""
        self.dev_panel = None
        self.link_test_dialog = None
        self.last_link_result = None

        tabs = QTabWidget(self)
        tabs.addTab(mission_page, TABS_TEXT["mission_title"])
        tabs.addTab(calibration_page, TABS_TEXT["calibration_title"])
        tabs.currentChanged.connect(lambda index: fade_in(tabs.widget(index)))
        if not self.developer_mode:
            return tabs

        self.agent_vehicles = [
            agent_vehicle(int(vehicle.vehicle_id)) for vehicle in self.vehicles if not vehicle.is_pasifik
        ]
        self.dev_panel = DevPanel(pasifik_vehicle(), self.agent_vehicles, self)
        self.dev_panel.link_test_requested.connect(self.start_link_test)
        self.link_test_dialog = LinkTestDialog(self.node_name, self.agent_vehicles, self)
        self.link_test_dialog.retest_requested.connect(self.retest_link)
        self.link_test_dialog.diagnose_requested.connect(self.diagnose_links)
        self.dev_panel.network_report_ready.connect(self.link_test_dialog.show_network_report)

        # Bench equipment rather than a flight control, so it goes last.
        tabs.addTab(self.dev_panel, DEVELOPER_TEXT["tab_title"])
        return tabs

    # The link test

    def start_link_test(self, agent_ids: list) -> None:
        self.link_test_dialog.show_running(LINK_TEST_DURATION_S)
        self.controller.link_test(agent_ids)
        self.log_panel.append(
            f"Link test started for {LINK_TEST_DURATION_S:.0f} s with agents {agent_ids}."
        )

    def retest_link(self) -> None:
        """The window's RETEST button: the same test again, with the agents ticked now."""
        self.start_link_test(self.dev_panel.ticked_agent_ids())

    def handle_link_test(self, payload: dict) -> None:
        if self.link_test_dialog is None:
            return
        self.last_link_result = payload
        self.link_test_dialog.show_result(payload)
        self.log_panel.append(
            f"Link test done | {len(payload.get(KEY_RESULT_MESH_ROWS, []))} mesh rows | "
            f"{payload.get(KEY_RESULT_FILE)}"
        )

    def diagnose_links(self) -> None:
        """Read the last ping test and link test and say what they mean."""
        reasons = diagnose(self.dev_panel.last_report, self.last_link_result, self.agent_vehicles)
        self.link_test_dialog.show_diagnosis(reasons)
        self.dev_panel.show_diagnosis(reasons)

    def node_name(self, node_id: int) -> str:
        """A mesh node as the table names it: an agent by its name, the ground station as GCS."""
        for agent in self.agent_vehicles:
            if agent.agent_id == node_id:
                return agent.name
        return LINK_TEST["gcs_name"]

    def refresh_flying_state(self) -> None:
        """The link test loads every link, so it is refused while anything flies."""
        if self.dev_panel is None:
            return
        flying = self.controller.mission_state in MISSION_ACTIVE_STATES or any(
            vehicle.armed for vehicle in self.vehicles
        )
        self.dev_panel.set_mission_active(flying)
        self.link_test_dialog.set_mission_active(flying)

    def stop_developer_sessions(self) -> None:
        """Kill every ssh the DEV tab started, before the window goes away."""
        if self.dev_panel is not None:
            self.dev_panel.stop_sessions()
