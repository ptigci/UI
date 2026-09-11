"""The link test's table of what held the channel: every source each node's bridge heard."""

from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from competitions.swarm_uav.config import (
    LINK_TEST_AIR_HIDDEN_NETWORK_TEXT,
    LINK_TEST_SNIFF_COLUMNS,
    LINK_TEST_SNIFF_KIND_NAMES,
)

MISSING_VALUE_TEXT = "-"
ACCESS_POINT_KIND = "ap"


class AirSniffTable(QTableWidget):
    """One row per source per node, the biggest share of the air first."""

    def __init__(self, node_name, parent=None) -> None:
        super().__init__(0, len(LINK_TEST_SNIFF_COLUMNS), parent)
        self.node_name = node_name  # callable(node_id) -> display name
        self.setHorizontalHeaderLabels(LINK_TEST_SNIFF_COLUMNS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def show_air(self, reports: list) -> None:
        rows = [
            (report.get("node"), source)
            for report in reports
            for source in report.get("sources", [])
        ]
        self.setRowCount(len(rows))
        for row_index, (node_id, source) in enumerate(rows):
            values = [
                self.node_name(node_id),
                self.cell_text(source.get("mac")),
                self.kind_name(source.get("kind")),
                self.source_name(source),
                self.cell_text(source.get("frames")),
                self.cell_text(source.get("air")),
                self.cell_text(source.get("rssi")),
                self.cell_text(source.get("rate")),
            ]
            for column_index, value in enumerate(values):
                self.setItem(row_index, column_index, QTableWidgetItem(value))

    @staticmethod
    def kind_name(kind) -> str:
        return LINK_TEST_SNIFF_KIND_NAMES.get(str(kind), str(kind))

    @staticmethod
    def source_name(source: dict) -> str:
        """An access point with no name is hidden; anything else without a name has none."""
        name = source.get("name")
        if name:
            return str(name)
        if source.get("kind") == ACCESS_POINT_KIND:
            return LINK_TEST_AIR_HIDDEN_NETWORK_TEXT
        return ""

    @staticmethod
    def cell_text(value) -> str:
        if value is None:
            return MISSING_VALUE_TEXT
        return str(value)
