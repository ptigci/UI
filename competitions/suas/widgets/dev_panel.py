"""DEV tab: the aircraft software as it runs on the VTOL's Pi.

A bench session is mostly spent starting the vtol node, reading its log and
pulling the branch under test onto the Pi. This tab does that over SSH so
nobody has to keep a terminal open beside the interface, and beside it runs
the ground services on this laptop and asks both ends of the Rocket link what
they can see. With SIMULATION ticked the vtol node runs on this laptop too,
against SITL.

The commands live in competitions/suas/dev/ and the buttons in
widgets/dev_commands.py and widgets/dev_local.py — this file lays the tab
out, polls the unit, follows the journal and runs the ping test. The link
test crosses the broker, so the window runs that one and this tab only asks
for it.
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

from competitions.suas.config import (
    DEVELOPER_MONITOR_MIN_HEIGHT,
    DEVELOPER_STATUS_POLL_S,
    DEVELOPER_TEXT,
)
from competitions.suas.dev import (
    LocalProcess,
    NetworkProbe,
    NetworkReport,
    SshSession,
    decode_log_line,
    ground_services_start,
    read_simulation_mode,
    vtol_monitor,
    vtol_status,
)
from competitions.suas.widgets.dev_commands import DevCommandsMixin
from competitions.suas.widgets.dev_local import DevLocalMixin
from competitions.suas.widgets.network_table import NetworkTable
from theme import flush_layout, set_role, set_variant, space_layout
from theme.tokens import (
    ROLE_HINT,
    ROLE_READOUT_LABEL,
    STATE_COLORS,
    STATE_CRITICAL,
    STATE_IDLE,
    STATE_OK,
    STATE_STALE,
    VARIANT_DANGER,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
)
from widgets.card import Card
from widgets.status_pill import StatusPill
from widgets.terminal_view import TerminalView, timestamped

SUCCESS_EXIT_CODE = 0
MILLISECONDS_PER_SECOND = 1000
# What systemctl is-active prints, and the pill each answer becomes.
ACTIVE_TEXT = "active"
FAILED_TEXT = "failed"
NODES_STRETCH = 2
REPOSITORY_STRETCH = 1
MONITOR_STRETCH = 2
NETWORK_STRETCH = 1
# How the middle row and the command output share the height left under the
# control row. A command that answers in a paragraph was unreadable
# through the few lines the output used to get.
MIDDLE_ROW_STRETCH = 3
OUTPUT_STRETCH = 2


class DevPanel(DevCommandsMixin, DevLocalMixin, QWidget):
    """Start, stop, update and watch the vtol node."""

    # The link test goes over the broker, so the window runs it.
    link_test_requested = pyqtSignal()
    # DIAGNOSE reads the last link test as well, which the window holds.
    diagnose_requested = pyqtSignal()
    # SIMULATION means more than where the node runs: with no aircraft there is
    # no RFD900x either, so the window points the safety link somewhere else.
    simulation_changed = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # Commands that have gone out and not reported back yet, the status
        # question not answered yet, the journal being followed, and the vtol
        # node when it runs here in simulation.
        self.command_sessions: list[SshSession | LocalProcess] = []
        self.status_session: SshSession | None = None
        self.monitor_session: SshSession | None = None
        self.local_vtol: LocalProcess | None = None
        self.test_mission: LocalProcess | None = None
        self.ground = ground_services_start(self)
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
        middle_layout.addWidget(self.build_monitor_card(), MONITOR_STRETCH)
        middle_layout.addWidget(self.build_network_card(), NETWORK_STRETCH)
        panel_layout.addLayout(middle_layout, MIDDLE_ROW_STRETCH)
        panel_layout.addWidget(self.build_output_card(), OUTPUT_STRETCH)

        self.status_timer = QTimer(self)
        self.status_timer.setInterval(int(DEVELOPER_STATUS_POLL_S * MILLISECONDS_PER_SECOND))
        self.status_timer.timeout.connect(self.poll_status)
        self.status_timer.start()
        self.poll_status()

    # Construction

    def build_nodes_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["nodes_title"])
        unit_layout = QHBoxLayout()
        flush_layout(unit_layout)
        unit_label = QLabel(DEVELOPER_TEXT["unit_label"], self)
        set_role(unit_label, ROLE_READOUT_LABEL)
        unit_layout.addWidget(unit_label)
        self.unit_pill = StatusPill(self, DEVELOPER_TEXT["status_unknown"], STATE_IDLE)
        unit_layout.addWidget(self.unit_pill)
        unit_layout.addStretch()
        card.add_layout(unit_layout)

        # Two rows of three, so the card fits beside the repository card at
        # the window's smallest size: the node itself, then the tests.
        node_layout = QHBoxLayout()
        flush_layout(node_layout)
        start_button = QPushButton(DEVELOPER_TEXT["start_text"], self)
        set_variant(start_button, VARIANT_PRIMARY)
        start_button.clicked.connect(self.start_vtol)
        node_layout.addWidget(start_button)
        stop_button = QPushButton(DEVELOPER_TEXT["stop_text"], self)
        stop_button.clicked.connect(self.stop_vtol)
        node_layout.addWidget(stop_button)
        self.monitor_button = QPushButton(DEVELOPER_TEXT["monitor_text"], self)
        self.monitor_button.clicked.connect(self.toggle_monitor)
        node_layout.addWidget(self.monitor_button)
        card.add_layout(node_layout)

        test_layout = QHBoxLayout()
        flush_layout(test_layout)
        self.ping_test_button = QPushButton(DEVELOPER_TEXT["ping_test_text"], self)
        self.ping_test_button.clicked.connect(self.run_ping_test)
        test_layout.addWidget(self.ping_test_button)
        self.link_test_button = QPushButton(DEVELOPER_TEXT["link_test_text"], self)
        self.link_test_button.clicked.connect(self.link_test_requested)
        test_layout.addWidget(self.link_test_button)
        reboot_button = QPushButton(DEVELOPER_TEXT["reboot_text"], self)
        set_variant(reboot_button, VARIANT_DANGER)
        reboot_button.clicked.connect(self.reboot_pi)
        test_layout.addWidget(reboot_button)
        card.add_layout(test_layout)

        ground_layout = QHBoxLayout()
        flush_layout(ground_layout)
        self.ground_button = QPushButton(DEVELOPER_TEXT["ground_start_text"], self)
        self.ground_button.clicked.connect(self.toggle_ground)
        ground_layout.addWidget(self.ground_button)
        self.ground_pill = StatusPill(self, DEVELOPER_TEXT["status_stopped"], STATE_IDLE)
        ground_layout.addWidget(self.ground_pill)
        ground_layout.addStretch()
        self.simulation_checkbox = QCheckBox(DEVELOPER_TEXT["simulation_text"], self)
        # Where the last session left it, so a bench day does not start by
        # writing the wrong mode into the aircraft's config.
        self.simulation_checkbox.setChecked(read_simulation_mode())
        self.simulation_checkbox.toggled.connect(self.simulation_toggled)
        ground_layout.addWidget(self.simulation_checkbox)
        card.add_layout(ground_layout)

        mission_layout = QHBoxLayout()
        flush_layout(mission_layout)
        self.test_mission_button = QPushButton(DEVELOPER_TEXT["test_mission_text"], self)
        self.test_mission_button.clicked.connect(self.run_test_mission)
        mission_layout.addWidget(self.test_mission_button)
        mission_layout.addStretch()
        card.add_layout(mission_layout)
        card.add_widget(self.build_hint(DEVELOPER_TEXT["test_mission_hint"]))
        self.refresh_test_mission_button()

        card.add_stretch()
        return card

    def simulation_toggled(self, simulating: bool) -> None:
        """The box changed: the safety link and TEST MISSION both follow it."""
        self.refresh_test_mission_button()
        self.simulation_changed.emit(simulating)

    def refresh_test_mission_button(self) -> None:
        """TEST MISSION arms an aircraft, so it exists only for a simulated one."""
        self.test_mission_button.setEnabled(
            self.simulation_checkbox.isChecked() and self.test_mission is None
        )

    def build_repository_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["repository_title"])
        branch_layout = QHBoxLayout()
        flush_layout(branch_layout)
        branch_label = QLabel(DEVELOPER_TEXT["branch_label"], self)
        set_role(branch_label, ROLE_READOUT_LABEL)
        branch_layout.addWidget(branch_label)
        self.branch_input = QLineEdit(self)
        self.branch_input.setPlaceholderText(DEVELOPER_TEXT["branch_placeholder"])
        self.branch_input.returnPressed.connect(self.checkout_branch)
        branch_layout.addWidget(self.branch_input)
        card.add_layout(branch_layout)

        button_layout = QHBoxLayout()
        flush_layout(button_layout)
        checkout_button = QPushButton(DEVELOPER_TEXT["checkout_text"], self)
        checkout_button.clicked.connect(self.checkout_branch)
        button_layout.addWidget(checkout_button)
        pull_button = QPushButton(DEVELOPER_TEXT["pull_text"], self)
        pull_button.clicked.connect(self.pull_repository)
        button_layout.addWidget(pull_button)
        push_button = QPushButton(DEVELOPER_TEXT["push_text"], self)
        push_button.clicked.connect(self.push_repository)
        button_layout.addWidget(push_button)
        restore_button = QPushButton(DEVELOPER_TEXT["restore_text"], self)
        set_variant(restore_button, VARIANT_DANGER)
        restore_button.clicked.connect(self.restore_repository)
        button_layout.addWidget(restore_button)
        card.add_layout(button_layout)
        card.add_widget(self.build_hint(DEVELOPER_TEXT["repository_hint"]))
        card.add_stretch()
        return card

    def build_monitor_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["monitor_title"])
        self.monitor_terminal = TerminalView(card)
        self.monitor_terminal.setMinimumHeight(DEVELOPER_MONITOR_MIN_HEIGHT)
        self.monitor_terminal.setPlaceholderText(DEVELOPER_TEXT["monitor_empty_text"])
        card.add_widget(self.monitor_terminal, stretch=1)
        # A long log is easier to read from empty again.
        clear_button = QPushButton(DEVELOPER_TEXT["clear_text"], card)
        set_variant(clear_button, VARIANT_GHOST)
        clear_button.clicked.connect(self.monitor_terminal.clear)
        card.add_header_widget(clear_button)
        return card

    def build_network_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["network_title"])
        self.network_status_label = self.build_hint(DEVELOPER_TEXT["network_empty_text"])
        card.add_header_widget(self.network_status_label)
        card.add_widget(self.build_hint(DEVELOPER_TEXT["network_hint"]))
        self.network_table = NetworkTable(self)
        card.add_widget(self.network_table, stretch=1)
        diagnosis_layout = QHBoxLayout()
        flush_layout(diagnosis_layout)
        diagnosis_label = QLabel(DEVELOPER_TEXT["diagnosis_title"], self)
        set_role(diagnosis_label, ROLE_READOUT_LABEL)
        diagnosis_layout.addWidget(diagnosis_label)
        diagnosis_layout.addStretch()
        diagnose_button = QPushButton(DEVELOPER_TEXT["diagnose_text"], self)
        diagnose_button.clicked.connect(self.diagnose_requested)
        diagnosis_layout.addWidget(diagnose_button)
        card.add_layout(diagnosis_layout)
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

    # The status pill

    def poll_status(self) -> None:
        """Ask whether the unit runs, unless the last answer is still out.

        While the node runs here in simulation the Pi is not asked: the pill
        says so already.
        """
        if self.status_session is not None or self.local_vtol is not None:
            return
        self.status_session = vtol_status(self)
        self.status_session.finished.connect(self.status_answered)
        self.status_session.start()

    def status_answered(self, exit_code: int) -> None:
        session = self.status_session
        self.status_session = None
        session.deleteLater()
        answer = ""
        if session.lines:
            answer = session.lines[-1].strip()
        if answer == ACTIVE_TEXT:
            self.unit_pill.show_status(DEVELOPER_TEXT["status_running"], STATE_OK)
        elif answer == FAILED_TEXT:
            self.unit_pill.show_status(DEVELOPER_TEXT["status_failed"], STATE_CRITICAL)
        elif exit_code == SUCCESS_EXIT_CODE or answer:
            # systemctl exits non-zero for an inactive unit, but it did answer.
            self.unit_pill.show_status(DEVELOPER_TEXT["status_stopped"], STATE_IDLE)
        else:
            self.unit_pill.show_status(DEVELOPER_TEXT["status_unreachable"], STATE_STALE)

    # The monitor

    def toggle_monitor(self) -> None:
        """One button: it opens the journal, and once it is open it closes it."""
        if self.monitor_session is None:
            self.open_monitor()
        else:
            self.close_monitor()
            self.append_output(DEVELOPER_TEXT["monitor_closed"].format(vehicle=DEVELOPER_TEXT["vtol_name"]))
        self.refresh_monitor_button()

    def open_monitor(self) -> None:
        self.monitor_session = vtol_monitor(self)
        self.monitor_session.line_received.connect(self.show_monitor_line)
        self.monitor_session.finished.connect(self.monitor_ended)
        self.append_output(DEVELOPER_TEXT["monitor_open"].format(vehicle=DEVELOPER_TEXT["vtol_name"]))
        self.monitor_session.start()

    def show_monitor_line(self, line: str) -> None:
        """The node logs in colour, and the escape codes it uses cannot be
        printed, so the line is shown plain, in the colour of its level."""
        text, log_state = decode_log_line(line)
        self.monitor_terminal.append_line(text, STATE_COLORS.get(log_state))

    def monitor_ended(self, exit_code: int) -> None:
        """The journal stopped on its own: a dead link, or ssh refused."""
        if self.monitor_session is None:
            return  # closed from the button, which reports it itself
        self.append_output(DEVELOPER_TEXT["monitor_ended"].format(
            vehicle=DEVELOPER_TEXT["vtol_name"], exit_code=exit_code
        ))
        self.close_monitor()
        self.refresh_monitor_button()

    def close_monitor(self) -> None:
        session = self.monitor_session
        self.monitor_session = None
        session.stop()
        session.deleteLater()

    def refresh_monitor_button(self) -> None:
        if self.monitor_session is None:
            self.monitor_button.setText(DEVELOPER_TEXT["monitor_text"])
        else:
            self.monitor_button.setText(DEVELOPER_TEXT["monitor_stop_text"])

    # The tests

    def set_mission_active(self, mission_flying: bool) -> None:
        """The link test loads the mission link, so it is refused while the aircraft flies."""
        self.link_test_button.setEnabled(not mission_flying)

    def run_ping_test(self) -> None:
        if self.network_probe is not None:
            return  # one at a time; the button says so by staying pressed
        self.ping_test_button.setEnabled(False)
        self.network_status_label.setText(DEVELOPER_TEXT["network_running_text"])
        self.network_table.show_pending()
        self.network_probe = NetworkProbe(self)
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

    def show_diagnosis(self, reasons: list[str]) -> None:
        self.diagnosis_text.setText("\n".join(reasons))

    def stop_sessions(self) -> None:
        """Kill every process this tab started, before the tab goes away."""
        self.status_timer.stop()
        if self.monitor_session is not None:
            self.close_monitor()
        if self.network_probe is not None:
            self.network_probe.stop()
        self.ground.stop()
        self.stop_local_vtol()
        self.stop_test_mission()
        if self.status_session is not None:
            self.status_session.stop()
        # A stopped command reports back from inside stop(), and reporting
        # back is what takes it off this list.
        for session in list(self.command_sessions):
            session.stop()

    # Output

    def append_output(self, message: str) -> None:
        self.output_terminal.append_line(timestamped(message))
