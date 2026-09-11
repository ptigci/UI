"""The link test's progress and result in a window of its own: every link the
mission uses, in tables, with the last ping test under them and DIAGNOSE to
say in words why anything is missing."""

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from competitions.international_uav.config import (
    KEY_RESULT_AGE_S,
    KEY_RESULT_BROKER,
    KEY_RESULT_FILE,
    KEY_RESULT_MESH_ROWS,
    KEY_RESULT_ROCKET,
    KEY_RESULT_STILL_COUNT,
    KEY_RESULT_STILL_RATE_HZ,
    KEY_RESULT_STILLS,
    KEY_RESULT_TELEMETRY_AGES,
    KEY_RESULT_VEHICLE,
    LINK_TEST,
)
from competitions.international_uav.dev import NetworkReport, Vehicle
from competitions.international_uav.widgets.network_table import NetworkTable
from theme import fade_in, set_role, space_layout
from theme.tokens import ROLE_HINT, SPACE_LG, SPACE_XL
from widgets.card import Card

# The probes' own column names, as the ground station writes them.
MESH_ROW_KEYS = ("heard", "lost", "loss", "rtt_avg", "rtt_max", "jitter", "gap_max", "corrupt")
LINK_ROW_KEYS = ("sent", "heard", "lost", "loss", "rtt_avg", "rtt_max", "jitter", "gap_max")
MISSING_VALUE_TEXT = "-"
MILLISECONDS_PER_SECOND = 1000


class LinkTestDialog(QDialog):
    """A bar fills while the test probes, then the tables show."""

    # RETEST: the main window runs the test again with the agents ticked now.
    retest_requested = pyqtSignal()
    # DIAGNOSE: the main window reads the last tables and hands back sentences.
    diagnose_requested = pyqtSignal()

    def __init__(self, vehicle_name, agents: list[Vehicle], parent=None) -> None:
        super().__init__(parent)
        self.vehicle_name = vehicle_name  # callable(node_id) -> display name
        self.setWindowTitle(LINK_TEST["window_title"])
        self.resize(LINK_TEST["window_width"], LINK_TEST["window_height"])
        self.setSizeGripEnabled(True)
        self.test_running = False
        self.mission_flying = False

        # Six cards are taller than a small screen, so the page scrolls.
        page = QWidget(self)
        page_layout = QVBoxLayout(page)
        space_layout(page_layout, SPACE_XL, SPACE_LG)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(page)
        dialog_layout = QVBoxLayout(self)
        space_layout(dialog_layout, SPACE_LG, SPACE_LG)
        dialog_layout.addWidget(scroll_area)

        progress_card = Card(self, LINK_TEST["window_title"])
        page_layout.addWidget(progress_card)
        self.diagnose_button = QPushButton(LINK_TEST["diagnose_text"], self)
        self.diagnose_button.clicked.connect(self.diagnose_requested)
        progress_card.add_header_widget(self.diagnose_button)
        self.retest_button = QPushButton(LINK_TEST["retest_text"], self)
        self.retest_button.setEnabled(False)
        self.retest_button.clicked.connect(self.retest_requested)
        progress_card.add_header_widget(self.retest_button)
        self.status_label = self.hint_label()
        progress_card.add_widget(self.status_label)
        self.progress_bar = QProgressBar(self)
        progress_card.add_widget(self.progress_bar)

        self.mesh_table = self.build_table(page_layout, LINK_TEST["mesh_title"], LINK_TEST["mesh_columns"])
        self.links_table = self.build_table(page_layout, LINK_TEST["links_title"], LINK_TEST["links_columns"])

        vehicles_card = Card(self, LINK_TEST["vehicles_title"])
        page_layout.addWidget(vehicles_card)
        self.telemetry_label = self.hint_label()
        vehicles_card.add_widget(self.telemetry_label)
        self.stills_label = self.hint_label()
        vehicles_card.add_widget(self.stills_label)

        network_card = Card(self, LINK_TEST["network_title"])
        page_layout.addWidget(network_card)
        self.network_table = NetworkTable(agents, self)
        network_card.add_widget(self.network_table)

        diagnosis_card = Card(self, LINK_TEST["diagnosis_title"])
        page_layout.addWidget(diagnosis_card)
        self.diagnosis_label = self.hint_label()
        diagnosis_card.add_widget(self.diagnosis_label)
        page_layout.addStretch()

        # The probing has a known length, so the bar ticks along it; the rows
        # then travel from every agent over the mesh, which takes as long as it
        # takes, so that last stretch shows as a busy bar instead.
        self.elapsed_ms = 0
        self.total_ms = 0
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(LINK_TEST["progress_tick_ms"])
        self.tick_timer.timeout.connect(self.tick)

    def hint_label(self) -> QLabel:
        label = QLabel(self)
        label.setWordWrap(True)
        set_role(label, ROLE_HINT)
        return label

    def build_table(self, page_layout: QVBoxLayout, title: str, columns: list[str]) -> QTableWidget:
        card = Card(self, title)
        page_layout.addWidget(card)
        table = QTableWidget(0, len(columns), self)
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        card.add_widget(table)
        return table

    # Running

    def show_running(self, seconds: float) -> None:
        self.test_running = True
        self.update_buttons()
        self.mesh_table.setRowCount(0)
        self.links_table.setRowCount(0)
        self.telemetry_label.clear()
        self.stills_label.clear()
        self.progress_bar.show()
        self.status_label.setText(LINK_TEST["running_text"].format(seconds=seconds))
        self.total_ms = int(seconds * MILLISECONDS_PER_SECOND)
        self.elapsed_ms = 0
        self.progress_bar.setRange(0, self.total_ms)
        self.progress_bar.setValue(0)
        self.tick_timer.start()
        self.bring_up()

    def tick(self) -> None:
        self.elapsed_ms += LINK_TEST["progress_tick_ms"]
        if self.elapsed_ms < self.total_ms:
            self.progress_bar.setValue(self.elapsed_ms)
            return
        self.tick_timer.stop()
        self.progress_bar.setRange(0, 0)
        self.status_label.setText(LINK_TEST["collecting_text"])

    # The result

    def show_result(self, payload: dict) -> None:
        self.tick_timer.stop()
        self.progress_bar.hide()
        rows = payload.get(KEY_RESULT_MESH_ROWS, [])
        self.mesh_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [self.node_name(row.get("from")), self.node_name(row.get("to"))]
            values.extend(cell_text(row.get(key)) for key in MESH_ROW_KEYS)
            self.fill_row(self.mesh_table, row_index, values)
        links = [
            (LINK_TEST["rocket_name"], payload.get(KEY_RESULT_ROCKET)),
            (LINK_TEST["broker_name"], payload.get(KEY_RESULT_BROKER)),
        ]
        self.links_table.setRowCount(len(links))
        for row_index, (link_name, link) in enumerate(links):
            if not isinstance(link, dict):
                link = {}
            values = [link_name]
            values.extend(cell_text(link.get(key)) for key in LINK_ROW_KEYS)
            self.fill_row(self.links_table, row_index, values)
        self.telemetry_label.setText(LINK_TEST["line_separator"].join(
            self.telemetry_text(entry) for entry in payload.get(KEY_RESULT_TELEMETRY_AGES, [])
        ))
        stills = payload.get(KEY_RESULT_STILLS, {})
        self.stills_label.setText(LINK_TEST["stills_format"].format(
            count=stills.get(KEY_RESULT_STILL_COUNT, 0), rate_hz=stills.get(KEY_RESULT_STILL_RATE_HZ) or 0.0
        ))
        file_path = payload.get(KEY_RESULT_FILE)
        if file_path is None:
            self.status_label.setText(LINK_TEST["no_file_text"])
        else:
            self.status_label.setText(LINK_TEST["file_text"].format(file=file_path))
        self.test_running = False
        self.update_buttons()
        self.bring_up()

    @staticmethod
    def fill_row(table: QTableWidget, row_index: int, values: list[str]) -> None:
        for column_index, value in enumerate(values):
            table.setItem(row_index, column_index, QTableWidgetItem(value))

    def telemetry_text(self, entry: dict) -> str:
        vehicle = entry.get(KEY_RESULT_VEHICLE)
        age_s = entry.get(KEY_RESULT_AGE_S)
        if age_s is None:
            return LINK_TEST["telemetry_missing_text"].format(vehicle=vehicle)
        return LINK_TEST["telemetry_format"].format(
            vehicle=vehicle, age=LINK_TEST["age_format"].format(age_s=age_s)
        )

    def show_network_report(self, report: NetworkReport) -> None:
        self.network_table.show_report(report)

    def show_diagnosis(self, reasons: list[str]) -> None:
        self.diagnosis_label.setText(LINK_TEST["diagnosis_separator"].join(reasons))
        self.bring_up()

    def set_mission_active(self, mission_flying: bool) -> None:
        """The test loads every link, so a retest is refused while anything flies."""
        self.mission_flying = mission_flying
        self.update_buttons()

    def update_buttons(self) -> None:
        self.retest_button.setEnabled(not self.test_running and not self.mission_flying)

    def bring_up(self) -> None:
        """Show the window in front; a window that is already up does not fade again."""
        was_visible = self.isVisible()
        self.show()
        self.raise_()
        if not was_visible:
            fade_in(self)

    def node_name(self, node_id) -> str:
        if node_id is None:
            return MISSING_VALUE_TEXT
        try:
            return self.vehicle_name(int(node_id))
        except (TypeError, ValueError):
            return str(node_id)


def cell_text(value) -> str:
    if value is None:
        return MISSING_VALUE_TEXT
    return str(value)
