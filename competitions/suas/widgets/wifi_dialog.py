"""The VTOL has no wifi, and the operator pressed GIT PULL.

Opens instead of the pull: lists what the Pi's radio can hear, takes a
password, joins the network, waits until the Pi reports a way out to the
internet, and then runs the pull or checkout that was asked for. CANCEL leaves
everything as it was.

This dialog only exists in developer mode, on the bench: the operations
window itself keeps to the no-dialogs rule of §3.0.6.
"""

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from competitions.suas.config import DEVELOPER_WIFI, WIFI_DIALOG_TEXT
from competitions.suas.dev import (
    SshSession,
    WifiNetwork,
    WifiState,
    connectivity_check,
    parse_connectivity,
    parse_wifi_scan,
    vtol_host,
    wifi_connect,
    wifi_scan,
)
from theme import fade_in, set_role, set_variant, space_layout
from theme.tokens import ROLE_HINT, ROLE_PAGE_TITLE, SPACE_LG, SPACE_XL, VARIANT_PRIMARY
from widgets.card import Card

SUCCESS_EXIT_CODE = 0
SSID_COLUMN = 0
SIGNAL_COLUMN = 1
SECURITY_COLUMN = 2
MILLISECONDS_PER_SECOND = 1000


class WifiDialog(QDialog):
    """Pick a network, CONNECT, and the pull runs by itself afterwards."""

    # The Pi has a way out: whatever was asked for can run now.
    connected = pyqtSignal()

    def __init__(self, state: WifiState, action_text: str, parent=None) -> None:
        super().__init__(parent)
        self.action_text = action_text
        self.networks: list[WifiNetwork] = []
        self.joined_network: WifiNetwork | None = None
        self.session: SshSession | None = None
        self.wait_left_ms = 0
        self.setWindowTitle(WIFI_DIALOG_TEXT["window_title"])
        self.setMinimumSize(WIFI_DIALOG_TEXT["window_width"], WIFI_DIALOG_TEXT["window_height"])
        self.setSizeGripEnabled(True)

        dialog_layout = QVBoxLayout(self)
        space_layout(dialog_layout, SPACE_XL, SPACE_LG)
        card = Card(self)
        dialog_layout.addWidget(card, stretch=1)

        title_label = QLabel(title_text(state), self)
        title_label.setWordWrap(True)
        set_role(title_label, ROLE_PAGE_TITLE)
        card.add_widget(title_label)
        card.add_widget(self.hint_label(state_text(state)))
        card.add_widget(self.hint_label(WIFI_DIALOG_TEXT["hint"].format(action=action_text)))

        self.table = QTableWidget(0, len(WIFI_DIALOG_TEXT["columns"]), self)
        self.table.setHorizontalHeaderLabels(WIFI_DIALOG_TEXT["columns"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        card.add_widget(self.table, stretch=1)

        card.add_widget(fixed_row(self.build_form_row()))
        self.status_label = self.hint_label("")
        card.add_widget(self.status_label)
        card.add_widget(fixed_row(self.build_button_row()))

        self.wait_timer = QTimer(self)
        self.wait_timer.setInterval(DEVELOPER_WIFI["poll_interval_ms"])
        self.wait_timer.timeout.connect(self.check_connectivity)
        self.rescan()
        fade_in(self)

    # Construction

    def hint_label(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setWordWrap(True)
        set_role(label, ROLE_HINT)
        return label

    def build_form_row(self) -> QHBoxLayout:
        form_row = QHBoxLayout()
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText(WIFI_DIALOG_TEXT["password_placeholder"])
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setEnabled(False)
        self.password_input.returnPressed.connect(self.connect_network)
        form_row.addWidget(self.password_input, stretch=1)
        self.show_button = QPushButton(WIFI_DIALOG_TEXT["show_password_text"], self)
        self.show_button.clicked.connect(self.toggle_password)
        form_row.addWidget(self.show_button)
        return form_row

    def build_button_row(self) -> QHBoxLayout:
        button_row = QHBoxLayout()
        self.rescan_button = QPushButton(WIFI_DIALOG_TEXT["rescan_text"], self)
        self.rescan_button.clicked.connect(self.rescan)
        button_row.addWidget(self.rescan_button)
        button_row.addStretch()
        self.connect_button = QPushButton(WIFI_DIALOG_TEXT["connect_text"], self)
        set_variant(self.connect_button, VARIANT_PRIMARY)
        self.connect_button.clicked.connect(self.connect_network)
        button_row.addWidget(self.connect_button)
        cancel_button = QPushButton(WIFI_DIALOG_TEXT["cancel_text"], self)
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(cancel_button)
        return button_row

    # The networks

    def rescan(self) -> None:
        self.status_label.setText(WIFI_DIALOG_TEXT["scanning_text"])
        self.set_busy(True)
        self.run(wifi_scan(self), self.scan_finished)

    def scan_finished(self, exit_code: int, lines: list[str]) -> None:
        self.set_busy(False)
        if exit_code != SUCCESS_EXIT_CODE:
            self.status_label.setText(WIFI_DIALOG_TEXT["failed_text"].format(reason=last_line(lines)))
            return
        self.status_label.clear()
        self.show_networks(parse_wifi_scan(lines))

    def show_networks(self, networks: list[WifiNetwork]) -> None:
        self.networks = networks
        self.table.setRowCount(len(networks))
        for row_index, network in enumerate(networks):
            if network.secured:
                security_text = WIFI_DIALOG_TEXT["locked_text"]
            else:
                security_text = WIFI_DIALOG_TEXT["open_text"]
            self.table.setItem(row_index, SSID_COLUMN, QTableWidgetItem(network.ssid))
            self.table.setItem(row_index, SIGNAL_COLUMN, QTableWidgetItem(str(network.signal_percent)))
            self.table.setItem(row_index, SECURITY_COLUMN, QTableWidgetItem(security_text))
        self.selection_changed()

    def selected_network(self) -> WifiNetwork | None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        return self.networks[selected_rows[0].row()]

    def selection_changed(self) -> None:
        network = self.selected_network()
        self.password_input.setEnabled(network is not None and network.secured)

    def toggle_password(self) -> None:
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_button.setText(WIFI_DIALOG_TEXT["hide_password_text"])
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_button.setText(WIFI_DIALOG_TEXT["show_password_text"])

    # Connecting

    def connect_network(self) -> None:
        network = self.selected_network()
        if network is None:
            self.status_label.setText(WIFI_DIALOG_TEXT["no_network_text"])
            return
        self.status_label.setText(WIFI_DIALOG_TEXT["connecting_text"].format(ssid=network.ssid))
        self.set_busy(True)
        self.run(
            wifi_connect(network.ssid, self.password_input.text(), self),
            lambda exit_code, lines: self.connect_finished(network, exit_code, lines),
        )

    def connect_finished(self, network: WifiNetwork, exit_code: int, lines: list[str]) -> None:
        if exit_code != SUCCESS_EXIT_CODE:
            self.set_busy(False)
            self.status_label.setText(WIFI_DIALOG_TEXT["failed_text"].format(reason=last_line(lines)))
            return
        self.joined_network = network
        self.wait_left_ms = DEVELOPER_WIFI["connect_timeout_ms"]
        self.wait_timer.start()
        self.check_connectivity()

    def check_connectivity(self) -> None:
        """Ask once per tick whether the Pi has a way out, until it does or time is up."""
        if self.session is not None:
            return  # the last question is still being answered
        if self.wait_left_ms <= 0:
            self.wait_timer.stop()
            self.set_busy(False)
            self.status_label.setText(WIFI_DIALOG_TEXT["timeout_text"].format(
                ssid=self.joined_network.ssid,
                seconds=DEVELOPER_WIFI["connect_timeout_ms"] // MILLISECONDS_PER_SECOND,
            ))
            return
        self.status_label.setText(WIFI_DIALOG_TEXT["waiting_text"].format(
            seconds=self.wait_left_ms // MILLISECONDS_PER_SECOND
        ))
        self.wait_left_ms -= DEVELOPER_WIFI["poll_interval_ms"]
        self.run(connectivity_check(self), self.connectivity_answered)

    def connectivity_answered(self, exit_code: int, lines: list[str]) -> None:
        if not parse_connectivity(lines).has_internet():
            return
        self.wait_timer.stop()
        self.status_label.setText(WIFI_DIALOG_TEXT["connected_text"].format(action=self.action_text))
        self.connected.emit()
        self.accept()

    # Plumbing

    def run(self, session: SshSession, on_finished) -> None:
        """One ssh at a time; its whole answer goes to on_finished when it ends."""
        self.session = session
        session.finished.connect(lambda exit_code: self.session_finished(session, exit_code, on_finished))
        session.start()

    def session_finished(self, session: SshSession, exit_code: int, on_finished) -> None:
        self.session = None
        session.deleteLater()
        on_finished(exit_code, session.lines)

    def set_busy(self, busy: bool) -> None:
        self.rescan_button.setEnabled(not busy)
        self.connect_button.setEnabled(not busy)

    def reject(self) -> None:
        self.wait_timer.stop()
        if self.session is not None:
            self.session.stop()
        super().reject()


def title_text(state: WifiState) -> str:
    if state.wifi_connected():
        return WIFI_DIALOG_TEXT["no_internet_line"]
    return WIFI_DIALOG_TEXT["title_line"]


def state_text(state: WifiState) -> str:
    """How the Pi was reached, and what nmcli says each device is doing."""
    devices = WIFI_DIALOG_TEXT["device_separator"].join(
        WIFI_DIALOG_TEXT["device_format"].format(device=device, state=device_state)
        for device, device_state in state.device_states.items()
    )
    return WIFI_DIALOG_TEXT["state_line"].format(host=vtol_host(), devices=devices)


def fixed_row(row_layout: QHBoxLayout) -> QWidget:
    """A row that keeps its height, so the table above takes the stretch."""
    row = QWidget()
    row.setLayout(row_layout)
    row.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    return row


def last_line(lines: list[str]) -> str:
    """The last line with something on it, which is where nmcli puts its verdict."""
    for line in reversed(lines):
        if line.strip():
            return line.strip()
    return ""
