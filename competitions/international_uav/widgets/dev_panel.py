"""DEV tab: the vehicle software as it runs on the companion Pis.

The agents each run their software on a Pi 4 reached over wifi, the Pasifik
on a Pi 5 reached over the Rocket pair, and a bench session is mostly spent
starting those nodes, reading their logs and pulling the branch under test
onto all of them. This tab does that over SSH so nobody has to keep four
terminals open beside the interface, and beside it runs the ground station on
this laptop and asks both ends of the Rocket link what they can see. With
SIMULATION ticked the vehicles run on this laptop too, against SITL.

The commands live in competitions/international_uav/dev/ and the buttons in
widgets/dev_commands.py and widgets/dev_local.py — this file lays the tab
out, polls the units and runs the ping test.
"""

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from competitions.international_uav.config import DEVELOPER_STATUS_POLL_MS, DEVELOPER_TEXT
from competitions.international_uav.dev import (
    LocalProcess,
    NetworkProbe,
    NetworkReport,
    SshSession,
    Vehicle,
    ground_start,
    node_status,
)
from competitions.international_uav.widgets.dev_commands import DevCommandsMixin
from competitions.international_uav.widgets.dev_local import DevLocalMixin
from competitions.international_uav.widgets.monitor_grid import MonitorGrid
from competitions.international_uav.widgets.network_table import NetworkTable
from theme import flush_layout, set_role, set_variant, space_layout
from theme.tokens import (
    ROLE_HINT,
    ROLE_READOUT_LABEL,
    SPACE_XL,
    STATE_CRITICAL,
    STATE_IDLE,
    STATE_OK,
    STATE_STALE,
    VARIANT_DANGER,
    VARIANT_PRIMARY,
)
from widgets.card import Card
from widgets.status_pill import StatusPill
from widgets.terminal_view import TerminalView, timestamped

SUCCESS_EXIT_CODE = 0
# What systemctl is-active prints, and the pill each answer becomes.
ACTIVE_TEXT = "active"
FAILED_TEXT = "failed"
NODES_STRETCH = 2
REPOSITORY_STRETCH = 1
MONITORS_STRETCH = 2
NETWORK_STRETCH = 1
# How the middle row and the command output share the height left under the
# control row. The monitors take the larger share because four of them stack
# two deep, and a command that answers in a paragraph was still unreadable
# through the few lines the output used to get.
MIDDLE_ROW_STRETCH = 4
OUTPUT_STRETCH = 2


class DevPanel(DevCommandsMixin, DevLocalMixin, QWidget):
    """Start, stop, update and watch the nodes of the ticked vehicles."""

    # The link test goes over every link, so the main window runs it; it
    # carries the ticked agents' ids. Disabled while anything flies.
    link_test_requested = pyqtSignal(list)
    # A finished ping test, for the link test window's own copy of the table.
    network_report_ready = pyqtSignal(object)

    def __init__(self, pasifik: Vehicle, agents: list[Vehicle], parent=None) -> None:
        super().__init__(parent)
        self.pasifik = pasifik
        self.agents = agents
        self.vehicles = [*agents, pasifik]
        self.checkboxes: dict[str, QCheckBox] = {}
        self.pills: dict[str, StatusPill] = {}
        # Commands that have gone out and not reported back yet, and the
        # status question each vehicle has not answered yet.
        self.command_sessions: list[SshSession | LocalProcess] = []
        self.status_sessions: dict[str, SshSession] = {}
        self.ground = ground_start(self)
        self.ground.line_received.connect(self.show_ground_line)
        self.ground.finished.connect(self.ground_finished)
        self.network_probe: NetworkProbe | None = None
        self.last_report: NetworkReport | None = None

        panel_layout = QVBoxLayout(self)
        space_layout(panel_layout)
        control_layout = QHBoxLayout()
        flush_layout(control_layout)
        control_layout.addWidget(self.build_nodes_card(), NODES_STRETCH)
        control_layout.addWidget(self.build_repository_card(), REPOSITORY_STRETCH)
        panel_layout.addLayout(control_layout)

        middle_layout = QHBoxLayout()
        flush_layout(middle_layout)
        self.monitors = MonitorGrid(self)
        self.monitors.output.connect(self.append_output)
        self.monitors.local_ended.connect(self.local_node_ended)
        middle_layout.addWidget(self.monitors, MONITORS_STRETCH)
        middle_layout.addWidget(self.build_network_card(), NETWORK_STRETCH)
        panel_layout.addLayout(middle_layout, MIDDLE_ROW_STRETCH)
        panel_layout.addWidget(self.build_output_card(), OUTPUT_STRETCH)

        self.status_timer = QTimer(self)
        self.status_timer.setInterval(DEVELOPER_STATUS_POLL_MS)
        self.status_timer.timeout.connect(self.poll_status)
        self.status_timer.start()
        self.poll_status()

    # Construction

    def build_nodes_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["nodes_title"])
        # The agents and the Pasifik share one row: the four monitors under
        # this card need every row the card does not take for itself.
        vehicle_layout = QHBoxLayout()
        flush_layout(vehicle_layout)
        self.add_vehicle_group(vehicle_layout, DEVELOPER_TEXT["agents_label"], self.agents)
        vehicle_layout.addSpacing(SPACE_XL)
        self.add_vehicle_group(vehicle_layout, DEVELOPER_TEXT["pasifik_label"], [self.pasifik])
        vehicle_layout.addStretch()
        card.add_layout(vehicle_layout)

        button_layout = QHBoxLayout()
        flush_layout(button_layout)
        start_button = QPushButton(DEVELOPER_TEXT["start_text"], self)
        set_variant(start_button, VARIANT_PRIMARY)
        start_button.clicked.connect(self.start_nodes)
        button_layout.addWidget(start_button)
        stop_button = QPushButton(DEVELOPER_TEXT["stop_text"], self)
        stop_button.clicked.connect(self.stop_nodes)
        button_layout.addWidget(stop_button)
        self.monitor_button = QPushButton(DEVELOPER_TEXT["monitor_text"], self)
        self.monitor_button.clicked.connect(self.toggle_monitors)
        button_layout.addWidget(self.monitor_button)
        self.link_test_button = QPushButton(DEVELOPER_TEXT["link_test_text"], self)
        self.link_test_button.clicked.connect(self.request_link_test)
        button_layout.addWidget(self.link_test_button)
        self.ping_test_button = QPushButton(DEVELOPER_TEXT["ping_test_text"], self)
        self.ping_test_button.clicked.connect(self.run_ping_test)
        button_layout.addWidget(self.ping_test_button)
        reboot_button = QPushButton(DEVELOPER_TEXT["reboot_text"], self)
        set_variant(reboot_button, VARIANT_DANGER)
        reboot_button.clicked.connect(self.reboot_boards)
        button_layout.addWidget(reboot_button)
        card.add_layout(button_layout)

        ground_layout = QHBoxLayout()
        flush_layout(ground_layout)
        self.ground_button = QPushButton(DEVELOPER_TEXT["ground_start_text"], self)
        self.ground_button.clicked.connect(self.toggle_ground)
        ground_layout.addWidget(self.ground_button)
        self.ground_pill = StatusPill(self, DEVELOPER_TEXT["status_stopped"], STATE_IDLE)
        ground_layout.addWidget(self.ground_pill)
        ground_layout.addStretch()
        self.simulation_checkbox = QCheckBox(DEVELOPER_TEXT["simulation_text"], self)
        ground_layout.addWidget(self.simulation_checkbox)
        card.add_layout(ground_layout)

        card.add_stretch()
        return card

    def add_vehicle_group(self, row_layout: QHBoxLayout, label_text: str, vehicles: list[Vehicle]) -> None:
        """Onto the row: a label, then a checkbox and a status pill per vehicle."""
        row_label = QLabel(label_text, self)
        set_role(row_label, ROLE_READOUT_LABEL)
        row_layout.addWidget(row_label)
        for vehicle in vehicles:
            checkbox = QCheckBox(vehicle.name.upper(), self)
            checkbox.setChecked(True)
            row_layout.addWidget(checkbox)
            self.checkboxes[vehicle.name] = checkbox
            pill = StatusPill(self, DEVELOPER_TEXT["status_unknown"], STATE_IDLE)
            row_layout.addWidget(pill)
            self.pills[vehicle.name] = pill

    def build_repository_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["repository_title"])
        branch_layout = QHBoxLayout()
        flush_layout(branch_layout)
        branch_label = QLabel(DEVELOPER_TEXT["branch_label"], self)
        set_role(branch_label, ROLE_READOUT_LABEL)
        branch_layout.addWidget(branch_label)
        self.branch_input = QLineEdit(self)
        self.branch_input.setPlaceholderText(DEVELOPER_TEXT["branch_placeholder"])
        self.branch_input.returnPressed.connect(self.checkout_branches)
        branch_layout.addWidget(self.branch_input)
        card.add_layout(branch_layout)

        button_layout = QHBoxLayout()
        flush_layout(button_layout)
        checkout_button = QPushButton(DEVELOPER_TEXT["checkout_text"], self)
        checkout_button.clicked.connect(self.checkout_branches)
        button_layout.addWidget(checkout_button)
        pull_button = QPushButton(DEVELOPER_TEXT["pull_text"], self)
        pull_button.clicked.connect(self.pull_repositories)
        button_layout.addWidget(pull_button)
        push_button = QPushButton(DEVELOPER_TEXT["push_text"], self)
        push_button.clicked.connect(self.push_repositories)
        button_layout.addWidget(push_button)
        restore_button = QPushButton(DEVELOPER_TEXT["restore_text"], self)
        set_variant(restore_button, VARIANT_DANGER)
        restore_button.clicked.connect(self.restore_repositories)
        button_layout.addWidget(restore_button)
        card.add_layout(button_layout)
        card.add_widget(self.build_hint(DEVELOPER_TEXT["repository_hint"]))
        card.add_stretch()
        return card

    def build_network_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["network_title"])
        self.network_status_label = self.build_hint(DEVELOPER_TEXT["network_empty_text"])
        card.add_header_widget(self.network_status_label)
        card.add_widget(self.build_hint(DEVELOPER_TEXT["network_hint"]))
        self.network_table = NetworkTable(self.agents, self)
        card.add_widget(self.network_table, stretch=1)
        diagnosis_label = QLabel(DEVELOPER_TEXT["diagnosis_title"], self)
        set_role(diagnosis_label, ROLE_READOUT_LABEL)
        card.add_widget(diagnosis_label)
        self.diagnosis_text = self.build_hint("")
        card.add_widget(self.diagnosis_text)
        return card

    def build_output_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["output_title"])
        self.output_terminal = TerminalView(self)
        card.add_widget(self.output_terminal, stretch=1)
        return card

    def build_hint(self, text: str) -> QLabel:
        hint_label = QLabel(text, self)
        hint_label.setWordWrap(True)
        set_role(hint_label, ROLE_HINT)
        return hint_label

    # Status pills

    def poll_status(self) -> None:
        """Ask every vehicle whose last answer is in whether its unit runs.

        A vehicle running here in simulation is not asked: its pill says so.
        """
        for vehicle in self.vehicles:
            if vehicle.name in self.status_sessions or self.monitors.is_local(vehicle.name):
                continue
            session = node_status(vehicle, self)
            self.status_sessions[vehicle.name] = session
            session.finished.connect(lambda exit_code, name=vehicle.name: self.status_answered(name, exit_code))
            session.start()

    def status_answered(self, vehicle_name: str, exit_code: int) -> None:
        session = self.status_sessions.pop(vehicle_name)
        session.deleteLater()
        answer = ""
        if session.lines:
            answer = session.lines[-1].strip()
        if answer == ACTIVE_TEXT:
            self.pills[vehicle_name].show_status(DEVELOPER_TEXT["status_running"], STATE_OK)
        elif answer == FAILED_TEXT:
            self.pills[vehicle_name].show_status(DEVELOPER_TEXT["status_failed"], STATE_CRITICAL)
        elif exit_code == SUCCESS_EXIT_CODE or answer:
            # systemctl exits non-zero for an inactive unit, but it did answer.
            self.pills[vehicle_name].show_status(DEVELOPER_TEXT["status_stopped"], STATE_IDLE)
        else:
            self.pills[vehicle_name].show_status(DEVELOPER_TEXT["status_unreachable"], STATE_STALE)

    # Monitors and the tests

    def toggle_monitors(self) -> None:
        """One button: it opens the journals, and once they are open it closes them."""
        if self.monitors.is_open():
            self.monitors.close_journals()
        else:
            for vehicle in self.selected_vehicles():
                self.monitors.open(vehicle)
        self.refresh_monitor_button()

    def refresh_monitor_button(self) -> None:
        if self.monitors.is_open():
            self.monitor_button.setText(DEVELOPER_TEXT["monitor_stop_text"])
        else:
            self.monitor_button.setText(DEVELOPER_TEXT["monitor_text"])

    def request_link_test(self) -> None:
        self.link_test_requested.emit(self.ticked_agent_ids())

    def set_mission_active(self, mission_flying: bool) -> None:
        """The link test loads every link, so it is refused while anything flies."""
        self.link_test_button.setEnabled(not mission_flying)

    def run_ping_test(self) -> None:
        if self.network_probe is not None:
            return  # one at a time; the button says so by staying pressed
        self.ping_test_button.setEnabled(False)
        self.network_status_label.setText(DEVELOPER_TEXT["network_running_text"])
        self.network_table.show_pending()
        self.network_probe = NetworkProbe(self.pasifik, self.agents, self)
        self.network_probe.updated.connect(self.network_table.show_report)
        self.network_probe.finished.connect(self.ping_test_finished)
        self.network_probe.start()

    def ping_test_finished(self, report: NetworkReport) -> None:
        self.network_probe.deleteLater()
        self.network_probe = None
        self.last_report = report
        self.ping_test_button.setEnabled(True)
        self.network_status_label.setText(DEVELOPER_TEXT["network_done_text"])
        self.append_output(DEVELOPER_TEXT["network_done_text"])
        self.network_report_ready.emit(report)

    def show_diagnosis(self, reasons: list[str]) -> None:
        self.diagnosis_text.setText("\n".join(reasons))

    def stop_sessions(self) -> None:
        """Kill every process this tab started, before the tab goes away."""
        self.status_timer.stop()
        self.monitors.close_all()
        if self.network_probe is not None:
            self.network_probe.stop()
        self.ground.stop()
        for session in list(self.status_sessions.values()):
            session.stop()
        # A stopped command reports back from inside stop(), and reporting
        # back is what takes it off this list.
        for session in list(self.command_sessions):
            session.stop()

    # Output

    def append_output(self, message: str) -> None:
        self.output_terminal.append_line(timestamped(message))
