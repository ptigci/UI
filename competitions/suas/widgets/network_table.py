"""The ping test's table: one row per thing on the network, what this laptop
sees of it on the left and what the VTOL's Pi sees on the right.

Draws a NetworkReport and nothing else; the rows fill in as the answers land,
so a cell that has not been answered yet says so instead of staying blank.
"""

from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from competitions.suas.config import DEVELOPER_NETWORK, NETWORK_TEXT
from competitions.suas.dev import NetworkReport
from competitions.suas.dev.vtol_commands import vtol_address

LABEL_COLUMN = 0
GCS_COLUMN = 1
PI_COLUMN = 2


class NetworkTable(QTableWidget):

    def __init__(self, parent=None) -> None:
        rows = NETWORK_TEXT["rows"]
        super().__init__(len(rows), len(NETWORK_TEXT["columns"]), parent)
        self.row_index = {key: index for index, key in enumerate(rows)}
        self.setHorizontalHeaderLabels(NETWORK_TEXT["columns"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(
            LABEL_COLUMN, QHeaderView.ResizeMode.ResizeToContents
        )
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setWordWrap(True)
        for key, label in rows.items():
            self.setItem(self.row_index[key], LABEL_COLUMN, QTableWidgetItem(label))
        self.show_empty()

    def show_empty(self) -> None:
        for key in self.row_index:
            self.set_cells(key, NETWORK_TEXT["not_applicable_text"], NETWORK_TEXT["not_applicable_text"])

    def show_pending(self) -> None:
        for key in self.row_index:
            self.set_cells(key, NETWORK_TEXT["pending_text"], NETWORK_TEXT["pending_text"])

    def show_report(self, report: NetworkReport) -> None:
        not_applicable = NETWORK_TEXT["not_applicable_text"]
        gcs_pings = report.gcs_ping
        pi_pings = report.pi_ping
        self.set_cells("addresses", list_text(report.gcs_addresses), self.pi_addresses_text(report))
        self.set_cells(
            "rocket_ground",
            ping_text(gcs_pings, DEVELOPER_NETWORK["rocket_ground"]),
            self.pi_text(report, lambda: ping_text(pi_pings, DEVELOPER_NETWORK["rocket_ground"])),
        )
        self.set_cells(
            "rocket_air",
            ping_text(gcs_pings, DEVELOPER_NETWORK["rocket_air"]),
            self.pi_text(report, lambda: ping_text(pi_pings, DEVELOPER_NETWORK["rocket_air"])),
        )
        self.set_cells("pi", ping_text(gcs_pings, vtol_address()), not_applicable)
        self.set_cells("laptop", not_applicable, self.pi_text(report, lambda: laptop_text(report)))
        self.set_cells(
            "siyi", not_applicable,
            self.pi_text(report, lambda: ping_text(pi_pings, DEVELOPER_NETWORK["siyi"])),
        )
        self.set_cells(
            "neighbours", list_text(report.gcs_neighbours),
            self.pi_text(report, lambda: list_text(report.pi_neighbours)),
        )
        self.set_cells(
            "rocket_link", rocket_client_text(report),
            self.pi_text(report, lambda: pi_link_socket_text(report)),
        )
        self.resizeRowsToContents()

    def set_cells(self, key: str, gcs_text: str, pi_text: str) -> None:
        row = self.row_index[key]
        self.setItem(row, GCS_COLUMN, QTableWidgetItem(gcs_text))
        self.setItem(row, PI_COLUMN, QTableWidgetItem(pi_text))

    @staticmethod
    def pi_text(report: NetworkReport, reached_text) -> str:
        """The Pi's answer, or why there is none: not asked yet, or ssh failed."""
        if report.pi_reached is None:
            return NETWORK_TEXT["pending_text"]
        if not report.pi_reached:
            return NETWORK_TEXT["pi_unreachable_text"]
        return reached_text()

    def pi_addresses_text(self, report: NetworkReport) -> str:
        return self.pi_text(report, lambda: list_text([
            NETWORK_TEXT["interface_format"].format(interface=interface, address=address)
            for interface, address in report.pi_addresses.items()
        ]))


def ping_text(pings: dict[str, float | None], host: str | None) -> str:
    """A ping that has not been asked yet, one that got nothing back, or its time."""
    if host is None or host not in pings:
        return NETWORK_TEXT["pending_text"]
    if pings[host] is None:
        return NETWORK_TEXT["no_reply_text"]
    return NETWORK_TEXT["ping_format"].format(average_ms=pings[host])


def list_text(entries: list[str] | None) -> str:
    if entries is None:
        return NETWORK_TEXT["pending_text"]
    if not entries:
        return NETWORK_TEXT["not_applicable_text"]
    return NETWORK_TEXT["address_separator"].join(entries)


def laptop_text(report: NetworkReport) -> str:
    dialled = DEVELOPER_NETWORK["link_ground_host"]
    actual = report.gcs_rocket_address()
    return NETWORK_TEXT["laptop_pi_format"].format(
        dialled=dialled, dialled_result=ping_text(report.pi_ping, dialled),
        actual=actual, actual_result=ping_text(report.pi_ping, actual),
    )


def rocket_client_text(report: NetworkReport) -> str:
    if report.rocket_client_seen is None:
        return NETWORK_TEXT["pending_text"]
    if report.rocket_client_seen:
        return NETWORK_TEXT["rocket_client_text"]
    return NETWORK_TEXT["rocket_no_client_text"]


def pi_link_socket_text(report: NetworkReport) -> str:
    if report.pi_link_socket_seen:
        return NETWORK_TEXT["rocket_pi_link_text"].format(port=DEVELOPER_NETWORK["link_port"])
    return NETWORK_TEXT["rocket_pi_no_link_text"]
