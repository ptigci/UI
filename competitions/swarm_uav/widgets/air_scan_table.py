"""The link test's second table: the WiFi networks every node heard on the air."""

from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from competitions.swarm_uav.config import (
    LINK_TEST_AIR_COLUMNS,
    LINK_TEST_AIR_HIDDEN_NETWORK_TEXT,
    LINK_TEST_AIR_OVERLAP_MARK,
)

MISSING_VALUE_TEXT = "-"


class AirScanTable(QTableWidget):
    """One row per network per node, in the order the ground station sent them."""

    def __init__(self, node_name, parent=None) -> None:
        super().__init__(0, len(LINK_TEST_AIR_COLUMNS), parent)
        self.node_name = node_name  # callable(node_id) -> display name
        self.setHorizontalHeaderLabels(LINK_TEST_AIR_COLUMNS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def show_networks(self, networks: list) -> None:
        self.setRowCount(len(networks))
        for row_index, network in enumerate(networks):
            values = [
                self.node_name(network.get("node")),
                self.network_name(network.get("ssid")),
                self.cell_text(network.get("chan")),
                self.cell_text(network.get("signal")),
                self.cell_text(network.get("busy")),
                self.overlap_text(network.get("overlap")),
            ]
            for column_index, value in enumerate(values):
                self.setItem(row_index, column_index, QTableWidgetItem(value))

    @staticmethod
    def network_name(ssid) -> str:
        if not ssid:
            return LINK_TEST_AIR_HIDDEN_NETWORK_TEXT
        return str(ssid)

    @staticmethod
    def overlap_text(overlap) -> str:
        if overlap:
            return LINK_TEST_AIR_OVERLAP_MARK
        return ""

    @staticmethod
    def cell_text(value) -> str:
        if value is None:
            return MISSING_VALUE_TEXT
        return str(value)
