"""The link test's progress and result in a window of its own: one row per
pair of the mesh, and what else was on the air while it ran.

The three tables get a tab each rather than sharing the width or the height:
side by side none of them was wide enough — the pair table alone carries ten
columns — and stacked they each got a third of the height and needed
scrolling. The window still opens filling the screen for those ten columns.
"""

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from competitions.swarm_uav.config import (
    LINK_TEST_AIR_HINT,
    LINK_TEST_AIR_ONLY_RUNNING_TEXT,
    LINK_TEST_AIR_ONLY_TEXT,
    LINK_TEST_AIR_SUMMARY_LINE,
    LINK_TEST_AIR_SUMMARY_MISSING_LINE,
    LINK_TEST_AIR_SWARM_ONLY_TEXT,
    LINK_TEST_AIR_TAB_TITLE,
    LINK_TEST_CHANGE_CHANNEL_QUESTION,
    LINK_TEST_CHANGE_CHANNEL_TEXT,
    LINK_TEST_CHANGE_CHANNEL_TITLE,
    LINK_TEST_CHANNEL_CONFIG_TEXT,
    LINK_TEST_CHANNEL_ITEM_TEXT,
    LINK_TEST_CHANNEL_LINE,
    LINK_TEST_CHANNEL_MAX,
    LINK_TEST_CHANNEL_MIN,
    LINK_TEST_CHANNEL_MISSING_LINE,
    LINK_TEST_CHANNEL_SEPARATOR,
    LINK_TEST_COLLECTING_TEXT,
    LINK_TEST_COLUMNS,
    LINK_TEST_FILE_TEXT,
    LINK_TEST_NETWORKS_TAB_TITLE,
    LINK_TEST_PAIRS_TAB_TITLE,
    LINK_TEST_PROGRESS_TICK_MS,
    LINK_TEST_RETEST_TEXT,
    LINK_TEST_RUNNING_TEXT,
    LINK_TEST_SWARM_ONLY_HINT,
    LINK_TEST_SWARM_ONLY_TEXT,
    LINK_TEST_TESTED_ON_TEXT,
    LINK_TEST_WINDOW_TITLE,
)
from competitions.swarm_uav.widgets.air_scan_table import AirScanTable
from competitions.swarm_uav.widgets.air_sniff_table import AirSniffTable
from theme import fade_in, set_role, space_layout
from theme.tokens import ROLE_HINT, SPACE_LG, SPACE_XL
from widgets.card import Card

ROW_KEYS = ("heard", "lost", "loss", "rtt_avg", "rtt_max", "jitter", "gap_max", "corrupt")
MISSING_VALUE_TEXT = "-"
MILLISECONDS_PER_SECOND = 1000


class LinkTestDialog(QDialog):
    """A bar fills while the test probes, then the tables and the file show."""

    # The RETEST button: the main window runs the test again with the drones
    # ticked at that moment. Offered once a result is in, never during a
    # test or a mission.
    retest_requested = pyqtSignal()
    # CHANGE CHANNEL: move every node to the chosen channel for good.
    channel_change_requested = pyqtSignal(int)

    def __init__(self, vehicle_name, parent=None) -> None:
        super().__init__(parent)
        self.vehicle_name = vehicle_name  # callable(vehicle_id) -> display name
        self.setWindowTitle(LINK_TEST_WINDOW_TITLE)
        self.setSizeGripEnabled(True)
        self.test_running = False
        self.mission_flying = False

        dialog_layout = QVBoxLayout(self)
        space_layout(dialog_layout, SPACE_XL, SPACE_LG)

        progress_card = Card(self, LINK_TEST_WINDOW_TITLE)
        dialog_layout.addWidget(progress_card)
        # Ticked, the bridges are left alone during the test, as in flight:
        # the loss measured is the real one, and nothing is learned about the air.
        self.swarm_only_box = QCheckBox(LINK_TEST_SWARM_ONLY_TEXT, self)
        self.swarm_only_box.setToolTip(LINK_TEST_SWARM_ONLY_HINT)
        progress_card.add_header_widget(self.swarm_only_box)
        # A chosen channel is tried for the next test alone; the bridges come
        # back afterwards. CHANGE CHANNEL makes it the channel for good.
        self.channel_box = QComboBox(self)
        self.channel_box.addItem(LINK_TEST_CHANNEL_CONFIG_TEXT, None)
        for channel in range(LINK_TEST_CHANNEL_MIN, LINK_TEST_CHANNEL_MAX + 1):
            self.channel_box.addItem(LINK_TEST_CHANNEL_ITEM_TEXT.format(channel=channel), channel)
        self.channel_box.currentIndexChanged.connect(self.update_buttons)
        progress_card.add_header_widget(self.channel_box)
        self.change_channel_button = QPushButton(LINK_TEST_CHANGE_CHANNEL_TEXT, self)
        self.change_channel_button.setEnabled(False)
        self.change_channel_button.clicked.connect(self.confirm_channel_change)
        progress_card.add_header_widget(self.change_channel_button)
        self.retest_button = QPushButton(LINK_TEST_RETEST_TEXT, self)
        self.retest_button.setEnabled(False)
        self.retest_button.clicked.connect(self.retest_requested)
        progress_card.add_header_widget(self.retest_button)
        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        set_role(self.status_label, ROLE_HINT)
        progress_card.add_widget(self.status_label)
        self.progress_bar = QProgressBar(self)
        progress_card.add_widget(self.progress_bar)

        self.results_tabs = QTabWidget(self)
        dialog_layout.addWidget(self.results_tabs, stretch=1)

        pairs_layout = self.add_page(LINK_TEST_PAIRS_TAB_TITLE)
        self.table = QTableWidget(0, len(LINK_TEST_COLUMNS), self)
        self.table.setHorizontalHeaderLabels(LINK_TEST_COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        pairs_layout.addWidget(self.table, stretch=1)

        air_layout = self.add_page(LINK_TEST_AIR_TAB_TITLE)
        self.channel_label = QLabel(self)
        self.channel_label.setWordWrap(True)
        air_layout.addWidget(self.channel_label)
        self.air_summary_label = QLabel(self)
        self.air_summary_label.setWordWrap(True)
        set_role(self.air_summary_label, ROLE_HINT)
        air_layout.addWidget(self.air_summary_label)
        self.sniff_table = AirSniffTable(self.node_name, self)
        air_layout.addWidget(self.sniff_table, stretch=1)

        networks_layout = self.add_page(LINK_TEST_NETWORKS_TAB_TITLE)
        self.air_hint = QLabel(self)
        self.air_hint.setWordWrap(True)
        set_role(self.air_hint, ROLE_HINT)
        networks_layout.addWidget(self.air_hint)
        self.air_table = AirScanTable(self.node_name, self)
        networks_layout.addWidget(self.air_table, stretch=1)

        # One page looks much like the next, so the fade says which just arrived.
        self.results_tabs.currentChanged.connect(self.reveal_page)

        # The probing has a known length, so the bar ticks along it. The rows
        # then travel from every drone over the mesh, which takes as long as
        # it takes, so that last stretch shows as a busy bar instead.
        self.elapsed_ms = 0
        self.total_ms = 0
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(LINK_TEST_PROGRESS_TICK_MS)
        self.tick_timer.timeout.connect(self.tick)

    def add_page(self, title: str) -> QVBoxLayout:
        """A tab holding one section. The tab pane is already a card surface,
        so the section sits straight on it with a card's padding and no card.
        """
        page = QWidget(self)
        page_layout = QVBoxLayout(page)
        space_layout(page_layout)
        self.results_tabs.addTab(page, title)
        return page_layout

    def reveal_page(self, page_index: int) -> None:
        page = self.results_tabs.widget(page_index)
        if page is not None:
            fade_in(page)

    def swarm_only(self) -> bool:
        return self.swarm_only_box.isChecked()

    def test_channel(self):
        """The channel chosen for the next test, or None for the configured one."""
        return self.channel_box.currentData()

    def confirm_channel_change(self) -> None:
        channel = self.test_channel()
        if channel is None:
            return
        answer = QMessageBox.question(
            self,
            LINK_TEST_CHANGE_CHANNEL_TITLE,
            LINK_TEST_CHANGE_CHANNEL_QUESTION.format(channel=channel),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        # The chosen channel becomes the configured one, so the box goes back
        # to meaning "the configured channel".
        self.channel_box.setCurrentIndex(0)
        self.channel_change_requested.emit(channel)

    def show_running(self, seconds: float, probing: bool) -> None:
        """probing is False when no drone was ticked: only the air is scanned,
        which has no known length, so the bar is busy from the start."""
        self.test_running = True
        self.update_buttons()
        self.table.setRowCount(0)
        self.sniff_table.setRowCount(0)
        self.air_table.setRowCount(0)
        self.channel_label.clear()
        self.air_summary_label.clear()
        self.progress_bar.show()
        if not probing:
            self.status_label.setText(LINK_TEST_AIR_ONLY_RUNNING_TEXT)
            self.progress_bar.setRange(0, 0)
            self.bring_up()
            return
        self.status_label.setText(LINK_TEST_RUNNING_TEXT.format(seconds=seconds))
        self.total_ms = int(seconds * MILLISECONDS_PER_SECOND)
        self.elapsed_ms = 0
        self.progress_bar.setRange(0, self.total_ms)
        self.progress_bar.setValue(0)
        self.tick_timer.start()
        self.bring_up()

    def tick(self) -> None:
        self.elapsed_ms += LINK_TEST_PROGRESS_TICK_MS
        if self.elapsed_ms < self.total_ms:
            self.progress_bar.setValue(self.elapsed_ms)
            return
        self.tick_timer.stop()
        self.progress_bar.setRange(0, 0)
        self.status_label.setText(LINK_TEST_COLLECTING_TEXT)

    def show_result(self, payload: dict) -> None:
        self.tick_timer.stop()
        self.progress_bar.hide()
        rows = payload.get("rows", [])
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [self.node_name(row.get("from")), self.node_name(row.get("to"))]
            values.extend(self.cell_text(row.get(key)) for key in ROW_KEYS)
            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))
        self.channel_label.setText(
            LINK_TEST_CHANNEL_SEPARATOR.join(
                self.channel_text(entry) for entry in payload.get("channels", [])
            )
        )
        self.show_air(payload)
        self.air_hint.setText(
            LINK_TEST_AIR_HINT.format(channel=self.cell_text(payload.get("mesh_channel")))
        )
        self.air_table.show_networks(payload.get("networks", []))
        file_path = payload.get("file")
        if file_path is None:
            status = LINK_TEST_AIR_ONLY_TEXT
        else:
            status = LINK_TEST_FILE_TEXT.format(file=file_path)
        if payload.get("test_channel") is not None:
            status = LINK_TEST_TESTED_ON_TEXT.format(channel=payload["test_channel"]) + status
        self.status_label.setText(status)
        self.test_running = False
        self.update_buttons()
        self.bring_up()

    def show_air(self, payload: dict) -> None:
        """What the bridges heard: one summary line per node and the sources table."""
        reports = payload.get("air", [])
        if payload.get("swarm_only"):
            self.air_summary_label.setText(LINK_TEST_AIR_SWARM_ONLY_TEXT)
            reports = []
        else:
            self.air_summary_label.setText(
                LINK_TEST_CHANNEL_SEPARATOR.join(self.air_summary_text(report) for report in reports)
            )
        self.sniff_table.show_air(reports)

    def set_mission_active(self, mission_flying: bool) -> None:
        """The test loads the mesh, so a retest is refused while a mission flies."""
        self.mission_flying = mission_flying
        self.update_buttons()

    def update_buttons(self) -> None:
        idle = not self.test_running and not self.mission_flying
        self.retest_button.setEnabled(idle)
        self.change_channel_button.setEnabled(idle and self.test_channel() is not None)

    def channel_text(self, entry: dict) -> str:
        """One node's channel line; a node that sent nothing reads as no answer."""
        node = self.node_name(entry.get("node"))
        if entry.get("config") is None and entry.get("radio") is None:
            return LINK_TEST_CHANNEL_MISSING_LINE.format(node=node)
        return LINK_TEST_CHANNEL_LINE.format(
            node=node,
            radio=self.cell_text(entry.get("radio")),
            config=self.cell_text(entry.get("config")),
        )

    def air_summary_text(self, report: dict) -> str:
        """One node's air line; a node whose bridge sent nothing reads as no report."""
        node = self.node_name(report.get("node"))
        if report.get("busy") is None:
            return LINK_TEST_AIR_SUMMARY_MISSING_LINE.format(node=node)
        return LINK_TEST_AIR_SUMMARY_LINE.format(
            node=node,
            busy=self.cell_text(report.get("busy")),
            noise=self.cell_text(report.get("noise")),
            seconds=self.cell_text(report.get("seconds")),
        )

    def bring_up(self) -> None:
        """Show the window in front, filling the screen.

        A window that is already up keeps the size the operator gave it and
        does not fade again.
        """
        if self.isVisible():
            self.raise_()
            return
        self.showMaximized()
        self.raise_()
        fade_in(self)

    def node_name(self, node_id) -> str:
        if node_id is None:
            return MISSING_VALUE_TEXT
        try:
            return self.vehicle_name(int(node_id))
        except (TypeError, ValueError):
            return str(node_id)

    @staticmethod
    def cell_text(value) -> str:
        if value is None:
            return MISSING_VALUE_TEXT
        return str(value)
