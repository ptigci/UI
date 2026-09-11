"""The MONITORS card: a grid of live logs, one per vehicle being watched.

Each monitor is a card with the vehicle's name, a CLEAR button and a terminal
the log streams into, laid out in a grid that is repacked whenever one closes
so a closed one leaves no hole behind. The log is the journal read over ssh
or, in simulation, the vehicle's node running on this laptop — then the card
is the node's log and lives as long as the node.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QLabel, QPushButton, QSizePolicy

from competitions.international_uav.config import (
    DEVELOPER_MONITOR_COLUMNS,
    DEVELOPER_MONITOR_MIN_HEIGHT,
    DEVELOPER_TEXT,
)
from competitions.international_uav.dev import (
    LocalProcess,
    SshSession,
    Vehicle,
    decode_log_line,
    node_monitor,
)
from theme import flush_layout, set_role, set_variant
from theme.tokens import ROLE_HINT, STATE_COLORS, VARIANT_GHOST
from widgets.card import Card
from widgets.terminal_view import TerminalView


class MonitorGrid(Card):
    """The open monitors, and the journals and local nodes feeding them."""

    # A line for the command output: a monitor opened, closed or died.
    output = pyqtSignal(str)
    # A vehicle running here ended by itself: its name and exit code.
    local_ended = pyqtSignal(str, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, DEVELOPER_TEXT["monitors_title"])
        self.cards: dict[str, Card] = {}
        self.sessions: dict[str, SshSession] = {}
        self.local_nodes: dict[str, LocalProcess] = {}

        self.empty_label = QLabel(DEVELOPER_TEXT["monitors_empty_text"], self)
        self.empty_label.setWordWrap(True)
        set_role(self.empty_label, ROLE_HINT)
        # The grid below is what grows; a hint left free to grow with it ends
        # up floating in the middle of an empty card.
        self.empty_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.add_widget(self.empty_label)

        self.grid = QGridLayout()
        flush_layout(self.grid)
        self.add_layout(self.grid, stretch=1)

    def is_open(self) -> bool:
        """Whether any journal is being followed; the MONITOR button reads it."""
        return bool(self.sessions)

    def is_local(self, vehicle_name: str) -> bool:
        return vehicle_name in self.local_nodes

    def open(self, vehicle: Vehicle) -> None:
        """Follow the vehicle's journal. A vehicle running here keeps its card."""
        if vehicle.name in self.cards:
            return
        session = node_monitor(vehicle, self)
        self.sessions[vehicle.name] = session
        self.add_card(vehicle.name, session)
        self.output.emit(DEVELOPER_TEXT["monitor_open"].format(vehicle=vehicle.name))
        session.start()
        self.repack()

    def open_local(self, vehicle: Vehicle, node: LocalProcess) -> None:
        """Run the vehicle's node here; its card is its log until it stops."""
        if vehicle.name in self.cards:
            self.close(vehicle.name)
        self.local_nodes[vehicle.name] = node
        self.add_card(vehicle.name, node)
        node.start()
        self.repack()

    def add_card(self, vehicle_name: str, session) -> None:
        """A card showing every line the session prints, once it is started."""
        monitor_card = Card(self, vehicle_name)
        terminal = TerminalView(monitor_card)
        terminal.setMinimumHeight(DEVELOPER_MONITOR_MIN_HEIGHT)
        monitor_card.add_widget(terminal, stretch=1)
        self.cards[vehicle_name] = monitor_card

        # Beside the name: a long log is easier to read from empty again.
        clear_button = QPushButton(DEVELOPER_TEXT["clear_text"], monitor_card)
        set_variant(clear_button, VARIANT_GHOST)
        clear_button.clicked.connect(terminal.clear)
        monitor_card.add_header_widget(clear_button)

        session.line_received.connect(lambda line: self.show_line(terminal, line))
        session.finished.connect(lambda exit_code: self.ended(vehicle_name, exit_code))

    @staticmethod
    def show_line(terminal: TerminalView, line: str) -> None:
        """A node logs in colour, and the escape codes it uses cannot be
        printed — so the line is shown plain, in the colour of its level."""
        text, log_state = decode_log_line(line)
        terminal.append_line(text, STATE_COLORS.get(log_state))

    def ended(self, vehicle_name: str, exit_code: int) -> None:
        """The journal or the local node stopped on its own."""
        if vehicle_name in self.local_nodes:
            self.output.emit(
                DEVELOPER_TEXT["local_node_ended"].format(vehicle=vehicle_name, exit_code=exit_code)
            )
            self.local_ended.emit(vehicle_name, exit_code)
        elif vehicle_name in self.sessions:
            self.output.emit(
                DEVELOPER_TEXT["monitor_ended"].format(vehicle=vehicle_name, exit_code=exit_code)
            )
        else:
            return  # closed from a button, which reports it itself
        self.close(vehicle_name)
        self.repack()

    def close(self, vehicle_name: str) -> None:
        """Stop what feeds one card and take the card off the grid."""
        if vehicle_name in self.local_nodes:
            session = self.local_nodes.pop(vehicle_name)
        else:
            session = self.sessions.pop(vehicle_name)
        session.stop()
        session.deleteLater()
        monitor_card = self.cards.pop(vehicle_name)
        self.grid.removeWidget(monitor_card)
        monitor_card.deleteLater()

    def close_local(self, vehicle_name: str) -> None:
        """Stop the vehicle's node running here."""
        self.close(vehicle_name)
        self.repack()

    def close_journals(self) -> None:
        """The MONITOR button: every journal closes, the local nodes stay."""
        for vehicle_name in list(self.sessions):
            self.close(vehicle_name)
            self.output.emit(DEVELOPER_TEXT["monitor_closed"].format(vehicle=vehicle_name))
        self.repack()

    def close_all(self) -> None:
        """Before the tab goes away: every journal and every local node."""
        for vehicle_name in list(self.cards):
            self.close(vehicle_name)
        self.repack()

    def repack(self) -> None:
        """Lay the open monitors out again, so a closed one leaves no hole."""
        while self.grid.count():
            self.grid.takeAt(0)
        for slot_index, monitor_card in enumerate(self.cards.values()):
            grid_row = slot_index // DEVELOPER_MONITOR_COLUMNS
            grid_column = slot_index % DEVELOPER_MONITOR_COLUMNS
            self.grid.addWidget(monitor_card, grid_row, grid_column)
        self.empty_label.setVisible(not self.cards)
