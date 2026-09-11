"""The link test's progress and result in a window of its own: the probes'
round trip and loss, how old every other link's last word is, and DIAGNOSE to
say in words why anything is missing."""

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from competitions.suas.config import DEVELOPER_LINK_TEST, DEVELOPER_NETWORK
from competitions.suas.dev import LinkTestResult
from theme import fade_in, set_role, space_layout
from theme.tokens import ROLE_HINT, SPACE_LG, SPACE_XL
from widgets.card import Card

LABEL_COLUMN = 0
VALUE_COLUMN = 1


class LinkTestDialog(QDialog):
    """A bar fills while the probes go out, then the table shows."""

    retest_requested = pyqtSignal()
    diagnose_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(DEVELOPER_LINK_TEST["window_title"])
        self.resize(DEVELOPER_LINK_TEST["window_width"], DEVELOPER_LINK_TEST["window_height"])
        self.setSizeGripEnabled(True)
        self.test_running = False
        self.mission_flying = False

        dialog_layout = QVBoxLayout(self)
        space_layout(dialog_layout, SPACE_XL, SPACE_LG)

        progress_card = Card(self, DEVELOPER_LINK_TEST["window_title"])
        dialog_layout.addWidget(progress_card)
        self.diagnose_button = QPushButton(DEVELOPER_LINK_TEST["diagnose_text"], self)
        self.diagnose_button.clicked.connect(self.diagnose_requested)
        progress_card.add_header_widget(self.diagnose_button)
        self.retest_button = QPushButton(DEVELOPER_LINK_TEST["retest_text"], self)
        self.retest_button.setEnabled(False)
        self.retest_button.clicked.connect(self.retest_requested)
        progress_card.add_header_widget(self.retest_button)
        self.status_label = self.hint_label()
        progress_card.add_widget(self.status_label)
        self.progress_bar = QProgressBar(self)
        progress_card.add_widget(self.progress_bar)

        results_card = Card(self, DEVELOPER_LINK_TEST["results_title"])
        dialog_layout.addWidget(results_card, stretch=1)
        rows = DEVELOPER_LINK_TEST["rows"]
        self.row_index = {key: index for index, key in enumerate(rows)}
        self.table = QTableWidget(len(rows), len(DEVELOPER_LINK_TEST["columns"]), self)
        self.table.setHorizontalHeaderLabels(DEVELOPER_LINK_TEST["columns"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for key, label in rows.items():
            self.table.setItem(self.row_index[key], LABEL_COLUMN, QTableWidgetItem(label))
        self.clear_values()
        results_card.add_widget(self.table, stretch=1)

        diagnosis_card = Card(self, DEVELOPER_LINK_TEST["diagnosis_title"])
        dialog_layout.addWidget(diagnosis_card)
        self.diagnosis_label = self.hint_label()
        diagnosis_card.add_widget(self.diagnosis_label)

        # The probing has a known length, so the bar ticks along it and then
        # goes busy while the last replies are waited for.
        self.elapsed_ms = 0
        self.total_ms = DEVELOPER_NETWORK["probe_count"] * DEVELOPER_NETWORK["probe_interval_ms"]
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(DEVELOPER_LINK_TEST["progress_tick_ms"])
        self.tick_timer.timeout.connect(self.tick)

    def hint_label(self) -> QLabel:
        label = QLabel(self)
        label.setWordWrap(True)
        set_role(label, ROLE_HINT)
        return label

    def clear_values(self) -> None:
        for key in self.row_index:
            self.set_value(key, DEVELOPER_LINK_TEST["missing_text"])

    def set_value(self, key: str, text: str) -> None:
        self.table.setItem(self.row_index[key], VALUE_COLUMN, QTableWidgetItem(text))

    # Running

    def show_running(self) -> None:
        self.test_running = True
        self.update_buttons()
        self.clear_values()
        self.progress_bar.show()
        self.status_label.setText(DEVELOPER_LINK_TEST["running_text"].format(
            count=DEVELOPER_NETWORK["probe_count"], interval_ms=DEVELOPER_NETWORK["probe_interval_ms"]
        ))
        self.elapsed_ms = 0
        self.progress_bar.setRange(0, self.total_ms)
        self.progress_bar.setValue(0)
        self.tick_timer.start()
        self.bring_up()

    def tick(self) -> None:
        self.elapsed_ms += DEVELOPER_LINK_TEST["progress_tick_ms"]
        if self.elapsed_ms < self.total_ms:
            self.progress_bar.setValue(self.elapsed_ms)
            return
        self.tick_timer.stop()
        self.progress_bar.setRange(0, 0)
        self.status_label.setText(DEVELOPER_LINK_TEST["waiting_text"])

    # The result

    def show_result(self, result: LinkTestResult) -> None:
        self.tick_timer.stop()
        self.progress_bar.hide()
        probes = result.probes
        self.set_value("sent", str(probes.sent))
        self.set_value("received", str(probes.received))
        self.set_value("loss", number_text(probes.loss_percent))
        self.set_value("rtt_average", number_text(probes.rtt_average_ms))
        self.set_value("rtt_max", number_text(probes.rtt_max_ms))
        self.set_value("jitter", number_text(probes.jitter_ms))
        self.set_value("longest_gap", number_text(probes.longest_gap_ms))
        self.set_value("telemetry_age", age_text(result.telemetry_age_s))
        self.set_value("safety_age", age_text(result.safety_heartbeat_age_s))
        self.set_value("broker", yes_no_text(result.broker_connected))
        self.set_value("video_age", age_text(result.video_frame_age_s))
        self.status_label.setText(DEVELOPER_LINK_TEST["done_text"].format(
            received=probes.received, sent=probes.sent
        ))
        self.test_running = False
        self.update_buttons()
        self.bring_up()

    def show_diagnosis(self, reasons: list[str]) -> None:
        self.diagnosis_label.setText(DEVELOPER_LINK_TEST["diagnosis_separator"].join(reasons))
        self.bring_up()

    def set_mission_active(self, mission_flying: bool) -> None:
        """The test loads the mission link, so a retest is refused while the aircraft flies."""
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


def number_text(value: float | None) -> str:
    if value is None:
        return DEVELOPER_LINK_TEST["missing_text"]
    return DEVELOPER_LINK_TEST["number_format"].format(value=value)


def age_text(age_s: float | None) -> str:
    if age_s is None:
        return DEVELOPER_LINK_TEST["never_text"]
    return DEVELOPER_LINK_TEST["age_format"].format(age_s=age_s)


def yes_no_text(value: bool) -> str:
    if value:
        return DEVELOPER_LINK_TEST["yes_text"]
    return DEVELOPER_LINK_TEST["no_text"]
