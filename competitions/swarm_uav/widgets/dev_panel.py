"""DEV tab: the drone nodes as they run on the companion Pis, and on this
laptop for a simulation.

Every drone runs its software on its own Pi, and a bench session is mostly
spent starting those nodes, reading their logs and getting the branch under
test onto all three. This tab does that over SSH so nobody has to keep three
terminals open beside the interface. Beside it runs the computer node on this
laptop, and with SIMULATION ticked the drone nodes run here too, against SITL.

The commands live in competitions/swarm_uav/dev/ and the buttons in
widgets/dev_commands.py and widgets/dev_local.py — this file lays the tab out
and keeps the monitors.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from competitions.swarm_uav.config import (
    DEVELOPER_MONITOR_COLUMNS,
    DEVELOPER_MONITOR_MIN_HEIGHT,
    DEVELOPER_MONITOR_SHARE,
    DEVELOPER_OUTPUT_MIN_HEIGHT,
    DEVELOPER_OUTPUT_SHARE,
    DEVELOPER_TEXT,
    LINK_TEST_BUTTON_TEXT,
)
from competitions.swarm_uav.dev import (
    LocalProcess,
    SshSession,
    computer_start,
    decode_log_line,
    node_monitor,
)
from competitions.swarm_uav.widgets.dev_commands import DevCommandsMixin
from competitions.swarm_uav.widgets.dev_local import DevLocalMixin
from theme import flush_layout, set_role, set_variant, space_layout
from theme.tokens import (
    ROLE_HINT,
    ROLE_READOUT_LABEL,
    STATE_COLORS,
    STATE_IDLE,
    VARIANT_DANGER,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
)
from widgets.card import Card
from widgets.status_pill import StatusPill
from widgets.terminal_view import TerminalView, timestamped


class DevPanel(DevCommandsMixin, DevLocalMixin, QWidget):
    """Start, stop, update and watch the nodes of the ticked drones."""

    # The link test goes over the mesh, so the main window runs it; it carries
    # the ticked drones' ids, and none ticked means only the air is looked at.
    # Disabled while a mission flies.
    link_test_requested = pyqtSignal(list)

    def __init__(self, drones: list[tuple[int, str]], parent=None) -> None:
        """drones is a list of (vehicle_id, display_name) tuples."""
        super().__init__(parent)
        self.drone_names = dict(drones)
        self.drone_checkboxes: dict[int, QCheckBox] = {}
        # A monitor is a card on the grid fed by the ssh reading a journal or,
        # in simulation, by the drone node running here.
        self.monitor_cards: dict[int, Card] = {}
        self.monitor_sessions: dict[int, SshSession] = {}
        self.local_nodes: dict[int, LocalProcess] = {}
        # Commands that have gone out and not reported back yet.
        self.command_sessions: list[SshSession | LocalProcess] = []
        self.computer = computer_start(self)
        self.computer.line_received.connect(self.show_computer_line)
        self.computer.finished.connect(self.computer_finished)

        panel_layout = QVBoxLayout(self)
        space_layout(panel_layout)

        control_layout = QHBoxLayout()
        flush_layout(control_layout)
        control_layout.addWidget(self.build_nodes_card(), 2)
        control_layout.addWidget(self.build_repository_card(), 1)
        panel_layout.addLayout(control_layout)

        panel_layout.addWidget(self.build_monitors_card(), DEVELOPER_MONITOR_SHARE)
        panel_layout.addWidget(self.build_output_card(), DEVELOPER_OUTPUT_SHARE)
        self.refresh_monitor_button()

    # Construction

    def build_nodes_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["nodes_title"])

        selection_layout = QHBoxLayout()
        flush_layout(selection_layout)
        for vehicle_id, vehicle_name in self.drone_names.items():
            drone_checkbox = QCheckBox(vehicle_name.upper(), self)
            drone_checkbox.setChecked(True)
            selection_layout.addWidget(drone_checkbox)
            self.drone_checkboxes[vehicle_id] = drone_checkbox
        selection_layout.addStretch()
        self.simulation_checkbox = QCheckBox(DEVELOPER_TEXT["simulation_text"], self)
        selection_layout.addWidget(self.simulation_checkbox)
        card.add_layout(selection_layout)

        button_layout = QHBoxLayout()
        flush_layout(button_layout)
        start_button = QPushButton(DEVELOPER_TEXT["start_text"], self)
        set_variant(start_button, VARIANT_PRIMARY)
        start_button.clicked.connect(self.start_nodes)
        button_layout.addWidget(start_button)

        stop_button = QPushButton(DEVELOPER_TEXT["stop_text"], self)
        stop_button.clicked.connect(self.stop_nodes)
        button_layout.addWidget(stop_button)

        self.monitor_button = QPushButton(self)
        self.monitor_button.clicked.connect(self.toggle_monitors)
        button_layout.addWidget(self.monitor_button)

        pps_button = QPushButton(DEVELOPER_TEXT["pps_check_text"], self)
        pps_button.clicked.connect(self.check_pps)
        button_layout.addWidget(pps_button)

        logs_button = QPushButton(DEVELOPER_TEXT["logs_text"], self)
        logs_button.clicked.connect(self.fetch_logs)
        button_layout.addWidget(logs_button)

        self.link_test_button = QPushButton(LINK_TEST_BUTTON_TEXT, self)
        self.link_test_button.clicked.connect(self.request_link_test)
        button_layout.addWidget(self.link_test_button)

        reboot_button = QPushButton(DEVELOPER_TEXT["reboot_text"], self)
        set_variant(reboot_button, VARIANT_DANGER)
        reboot_button.clicked.connect(self.reboot_boards)
        button_layout.addWidget(reboot_button)
        card.add_layout(button_layout)

        computer_layout = QHBoxLayout()
        flush_layout(computer_layout)
        self.computer_button = QPushButton(DEVELOPER_TEXT["computer_start_text"], self)
        self.computer_button.clicked.connect(self.toggle_computer)
        computer_layout.addWidget(self.computer_button)
        self.computer_pill = StatusPill(self, DEVELOPER_TEXT["status_stopped"], STATE_IDLE)
        computer_layout.addWidget(self.computer_pill)
        computer_layout.addStretch()
        card.add_layout(computer_layout)

        card.add_stretch()
        return card

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

    def build_monitors_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["monitors_title"])
        self.monitors_empty_label = self.build_hint(DEVELOPER_TEXT["monitors_empty_text"])
        # The grid below is what grows; a hint left free to grow with it ends
        # up floating in the middle of an empty card.
        self.monitors_empty_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        card.add_widget(self.monitors_empty_label)

        self.monitors_layout = QGridLayout()
        flush_layout(self.monitors_layout)
        card.add_layout(self.monitors_layout, stretch=1)
        return card

    def build_output_card(self) -> Card:
        card = Card(self, DEVELOPER_TEXT["output_title"])
        self.output_terminal = TerminalView(self)
        self.output_terminal.setMinimumHeight(DEVELOPER_OUTPUT_MIN_HEIGHT)
        card.add_widget(self.output_terminal, stretch=1)
        return card

    def build_hint(self, text: str) -> QLabel:
        hint_label = QLabel(text, self)
        hint_label.setWordWrap(True)
        set_role(hint_label, ROLE_HINT)
        return hint_label

    def request_link_test(self) -> None:
        self.link_test_requested.emit(self.ticked_drone_ids())

    def set_mission_active(self, mission_flying: bool) -> None:
        """The link test loads the mesh, so it is refused while a mission flies."""
        self.link_test_button.setEnabled(not mission_flying)

    # Monitors

    def toggle_monitors(self) -> None:
        """One button: it opens the journals, and once they are open it closes them.

        A drone running here in simulation keeps its card: that card is its log.
        """
        if self.monitor_sessions:
            for vehicle_id in list(self.monitor_sessions):
                self.close_monitor(vehicle_id)
                self.append_output(
                    DEVELOPER_TEXT["monitor_closed"].format(vehicle=self.drone_names[vehicle_id])
                )
            self.layout_monitors()
            return

        for vehicle_id, vehicle_name in self.selected_drones():
            if vehicle_id in self.local_nodes:
                continue
            session = node_monitor(vehicle_id, self)
            self.monitor_sessions[vehicle_id] = session
            self.open_monitor(vehicle_id, vehicle_name, session)
            self.append_output(DEVELOPER_TEXT["monitor_open"].format(vehicle=vehicle_name))
            session.start()
        self.layout_monitors()

    def open_monitor(self, vehicle_id: int, vehicle_name: str, session) -> None:
        """A card on the grid showing every line the session prints.

        The session is an ssh reading a journal or a local drone node; the
        caller keeps it in its own dict and starts it once the card listens.
        """
        monitor_card = Card(self, vehicle_name.upper())
        monitor_terminal = TerminalView(monitor_card)
        monitor_terminal.setMinimumHeight(DEVELOPER_MONITOR_MIN_HEIGHT)
        monitor_card.add_widget(monitor_terminal, stretch=1)
        self.monitor_cards[vehicle_id] = monitor_card

        # Beside the drone name: a long log is easier to read from empty again.
        clear_button = QPushButton(DEVELOPER_TEXT["clear_text"], monitor_card)
        set_variant(clear_button, VARIANT_GHOST)
        clear_button.clicked.connect(monitor_terminal.clear)
        monitor_card.add_header_widget(clear_button)

        session.line_received.connect(
            lambda line, terminal=monitor_terminal: self.show_monitor_line(terminal, line)
        )
        session.finished.connect(
            lambda exit_code, watched_id=vehicle_id: self.monitor_ended(watched_id, exit_code)
        )

    def show_monitor_line(self, monitor_terminal: TerminalView, line: str) -> None:
        """A node logs in colour, and the escape codes it uses cannot be
        printed — so the line is shown plain, in the colour of its level."""
        text, log_state = decode_log_line(line)
        monitor_terminal.append_line(text, STATE_COLORS.get(log_state))

    def monitor_ended(self, vehicle_id: int, exit_code: int) -> None:
        """The journal or the local node stopped on its own."""
        if vehicle_id in self.local_nodes:
            ended_text = DEVELOPER_TEXT["local_node_ended"]
        elif vehicle_id in self.monitor_sessions:
            ended_text = DEVELOPER_TEXT["monitor_ended"]
        else:
            return  # closed from a button, which reports it itself
        self.append_output(
            ended_text.format(vehicle=self.drone_names[vehicle_id], exit_code=exit_code)
        )
        self.close_monitor(vehicle_id)
        self.layout_monitors()

    def close_monitor(self, vehicle_id: int) -> None:
        """Stop what feeds one card and take the card off the grid."""
        if vehicle_id in self.local_nodes:
            session = self.local_nodes.pop(vehicle_id)
        else:
            session = self.monitor_sessions.pop(vehicle_id)
        session.stop()
        session.deleteLater()
        monitor_card = self.monitor_cards.pop(vehicle_id)
        self.monitors_layout.removeWidget(monitor_card)
        monitor_card.deleteLater()

    def layout_monitors(self) -> None:
        """Repack the open monitors, so a closed one leaves no hole behind."""
        while self.monitors_layout.count():
            self.monitors_layout.takeAt(0)
        for slot_index, monitor_card in enumerate(self.monitor_cards.values()):
            grid_row = slot_index // DEVELOPER_MONITOR_COLUMNS
            grid_column = slot_index % DEVELOPER_MONITOR_COLUMNS
            self.monitors_layout.addWidget(monitor_card, grid_row, grid_column)

        self.monitors_empty_label.setVisible(not self.monitor_cards)
        self.refresh_monitor_button()

    def refresh_monitor_button(self) -> None:
        if self.monitor_sessions:
            self.monitor_button.setText(DEVELOPER_TEXT["monitor_stop_text"])
        else:
            self.monitor_button.setText(DEVELOPER_TEXT["monitor_text"])

    def stop_sessions(self) -> None:
        """Kill every process this tab started, before the tab goes away."""
        for vehicle_id in list(self.monitor_cards):
            self.close_monitor(vehicle_id)
        self.computer.stop()
        # A stopped command reports back from inside stop(), and reporting
        # back is what takes it off this list.
        for session in list(self.command_sessions):
            session.stop()

    # Output

    def append_output(self, message: str) -> None:
        self.output_terminal.append_line(timestamped(message))
