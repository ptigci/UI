"""The ping test's table: one row per thing on the network, what this laptop
sees of it on the left and what the Pasifik's Pi sees on the right.

Draws a NetworkReport and nothing else; the rows fill in as the answers land,
so a cell that has not been answered yet says so instead of staying blank.
"""

from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from competitions.international_uav.config import DEVELOPER_NETWORK, NETWORK_TEXT
from competitions.international_uav.dev import NetworkReport, PingResult, Vehicle

LABEL_COLUMN = 0
GCS_COLUMN = 1
PI_COLUMN = 2


class NetworkTable(QTableWidget):

    def __init__(self, agents: list[Vehicle], parent=None) -> None:
        rows = NETWORK_TEXT["rows"]
        super().__init__(len(rows), len(NETWORK_TEXT["columns"]), parent)
        self.agents = agents
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
        self.set_cells("addresses", self.addresses_text(report.gcs_addresses), self.pi_addresses_text(report))
        self.set_cells("rocket_ground", ping_text(report.gcs_rocket_ground), self.pi_ping_text(report, report.pi_rocket_ground))
        self.set_cells("rocket_air", ping_text(report.gcs_rocket_air), self.pi_ping_text(report, report.pi_rocket_air))
        self.set_cells("pasifik", ping_text(report.gcs_pasifik), not_applicable)
        self.set_cells("laptop", not_applicable, self.laptop_text(report))
        self.set_cells("camera", not_applicable, self.pi_ping_text(report, report.pi_camera))
        self.set_cells("neighbours", self.list_text(report.gcs_neighbours), self.pi_list_text(report, report.pi_neighbours))
        self.set_cells("rocket_link", self.rocket_client_text(report), self.pi_rocket_link_text(report))
        self.set_cells("agents", self.agents_text(report), not_applicable)
        self.set_cells("esp", self.esp_text(report), not_applicable)
        self.resizeRowsToContents()

    def set_cells(self, key: str, gcs_text: str, pi_text: str) -> None:
        row = self.row_index[key]
        self.setItem(row, GCS_COLUMN, QTableWidgetItem(gcs_text))
        self.setItem(row, PI_COLUMN, QTableWidgetItem(pi_text))

    # The laptop's cells

    @staticmethod
    def addresses_text(addresses: list[str]) -> str:
        if not addresses:
            return NETWORK_TEXT["pending_text"]
        return NETWORK_TEXT["address_separator"].join(addresses)

    @staticmethod
    def list_text(entries: list[str] | None) -> str:
        if entries is None:
            return NETWORK_TEXT["pending_text"]
        if not entries:
            return NETWORK_TEXT["not_applicable_text"]
        return NETWORK_TEXT["address_separator"].join(entries)

    @staticmethod
    def rocket_client_text(report: NetworkReport) -> str:
        if report.rocket_client_connected is None:
            return NETWORK_TEXT["pending_text"]
        if report.rocket_client_connected:
            return NETWORK_TEXT["rocket_client_text"]
        return NETWORK_TEXT["rocket_no_client_text"]

    def agents_text(self, report: NetworkReport) -> str:
        parts = []
        for agent in self.agents:
            parts.append(NETWORK_TEXT["agent_format"].format(
                name=agent.name, result=ping_text(report.gcs_agents.get(agent.agent_id))
            ))
        return NETWORK_TEXT["address_separator"].join(parts)

    @staticmethod
    def esp_text(report: NetworkReport) -> str:
        if report.esp_port_present is None:
            return NETWORK_TEXT["pending_text"]
        if report.esp_port_present:
            return NETWORK_TEXT["esp_present_text"].format(port=DEVELOPER_NETWORK["esp_port"])
        return NETWORK_TEXT["esp_missing_text"].format(port=DEVELOPER_NETWORK["esp_port"])

    # The Pi's cells

    @staticmethod
    def pi_text(report: NetworkReport, reached_text) -> str:
        """The Pi's answer, or why there is none: not asked yet, or ssh failed."""
        if report.pi_reached is None:
            return NETWORK_TEXT["pending_text"]
        if not report.pi_reached:
            return NETWORK_TEXT["pi_unreachable_text"]
        return reached_text()

    def pi_addresses_text(self, report: NetworkReport) -> str:
        return self.pi_text(report, lambda: NETWORK_TEXT["address_separator"].join(
            f"{interface} {address}" for interface, address in report.pi_addresses.items()
        ))

    def pi_ping_text(self, report: NetworkReport, result: PingResult | None) -> str:
        return self.pi_text(report, lambda: ping_text(result))

    def pi_list_text(self, report: NetworkReport, entries: list[str] | None) -> str:
        return self.pi_text(report, lambda: self.list_text(entries))

    def laptop_text(self, report: NetworkReport) -> str:
        return self.pi_text(report, lambda: NETWORK_TEXT["laptop_pi_format"].format(
            dialled=report.pi_dialled_address,
            dialled_result=ping_text(report.pi_laptop_dialled),
            actual=report.gcs_rocket_address,
            actual_result=ping_text(report.pi_laptop_actual),
        ))

    def pi_rocket_link_text(self, report: NetworkReport) -> str:
        def reached_text() -> str:
            if report.pi_rocket_link:
                return NETWORK_TEXT["rocket_pi_link_text"].format(port=DEVELOPER_NETWORK["rocket_port"])
            return NETWORK_TEXT["rocket_pi_no_link_text"]
        return self.pi_text(report, reached_text)


def ping_text(result: PingResult | None) -> str:
    if result is None:
        return NETWORK_TEXT["not_applicable_text"]
    if not result.answered():
        return NETWORK_TEXT["no_reply_text"]
    return NETWORK_TEXT["ping_format"].format(
        average_ms=result.average_ms, received=result.received, sent=result.sent
    )
