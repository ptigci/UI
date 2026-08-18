"""The target list: what the swarm is flying to, and what is still waiting.

Rows are coloured by target state with the same colours as the map, so the
list and the map read as one picture. The two actions here are the operator's
only say over the pool: drop a target, or put one back.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
)

from competitions.international_uav.config import (
    MAP_COLORS,
    MAP_TARGET_COLORS,
    MISSING_VALUE_TEXT,
    REQUEUE_TEXT,
    TARGET_AGENT_FORMAT,
    TARGET_CANDIDATE_TITLE,
    TARGET_CONFIDENCE_FORMAT,
    TARGET_CONFIRMED_TITLE,
    TARGET_EMPTY_TEXT,
    TARGET_LIST_MIN_HEIGHT,
    TARGET_NO_AGENT_TEXT,
    TARGET_PANEL_TITLE,
    TARGET_POSITION_FORMAT,
    TARGET_ROW_FORMAT,
    TARGET_SORT_LABELS,
    TARGET_STATE_FORMAT,
    VETO_CONFIRM_QUESTION,
    VETO_CONFIRM_TITLE,
    VETO_TEXT,
)
from theme import flush_layout, set_role, set_variant
from theme.tokens import ROLE_HEADING, VARIANT_DANGER
from widgets import Card

# Sort keys, in the order they appear in the picker.
SORT_BY_PRIORITY = "priority"
SORT_BY_CONFIDENCE = "confidence"
SORT_BY_ID = "target_id"


class TargetPanel(Card):
    """Confirmed targets on top, candidates underneath, two verdict buttons."""

    target_selected = pyqtSignal(str)
    veto_requested = pyqtSignal(str)
    requeue_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, TARGET_PANEL_TITLE)
        self.selected_target_id: str | None = None

        self.sortbox = QComboBox(self)
        for sort_key in (SORT_BY_PRIORITY, SORT_BY_CONFIDENCE, SORT_BY_ID):
            self.sortbox.addItem(TARGET_SORT_LABELS[sort_key], sort_key)
        self.add_header_widget(self.sortbox)

        self.confirmedlbl = self.build_group_heading(TARGET_CONFIRMED_TITLE)
        self.confirmedlist = self.build_target_list()
        self.candidatelbl = self.build_group_heading(TARGET_CANDIDATE_TITLE)
        self.candidatelist = self.build_target_list()

        self.vetobtn = QPushButton(VETO_TEXT, self)
        set_variant(self.vetobtn, VARIANT_DANGER)
        self.requeuebtn = QPushButton(REQUEUE_TEXT, self)

        action_layout = QHBoxLayout()
        flush_layout(action_layout)
        action_layout.addWidget(self.vetobtn)
        action_layout.addWidget(self.requeuebtn)

        self.add_widget(self.confirmedlbl)
        self.add_widget(self.confirmedlist)
        self.add_widget(self.candidatelbl)
        self.add_widget(self.candidatelist)
        self.add_layout(action_layout)

        self.targets: list = []
        self.confirmedlist.itemSelectionChanged.connect(
            lambda: self.handle_selection(self.confirmedlist)
        )
        self.candidatelist.itemSelectionChanged.connect(
            lambda: self.handle_selection(self.candidatelist)
        )
        self.sortbox.currentIndexChanged.connect(lambda: self.show_targets(self.targets))
        self.vetobtn.clicked.connect(self.request_veto)
        self.requeuebtn.clicked.connect(self.request_requeue)

        self.refresh_buttons()

    def build_target_list(self) -> QListWidget:
        """Both lists scroll rather than force the column taller than the screen."""
        target_list = QListWidget(self)
        target_list.setMinimumHeight(TARGET_LIST_MIN_HEIGHT)
        return target_list

    def build_group_heading(self, text: str) -> QLabel:
        """The two lists inside the card each get the same quiet heading."""
        heading = QLabel(text, self)
        set_role(heading, ROLE_HEADING)
        return heading

    # Display

    def show_targets(self, targets: list) -> None:
        """Rebuild both lists without losing the operator's place."""
        self.targets = targets
        sorted_targets = self.sorted_targets(targets)

        self.fill_list(
            self.confirmedlist, [target for target in sorted_targets if not target.is_open()]
        )
        self.fill_list(
            self.candidatelist, [target for target in sorted_targets if target.is_open()]
        )
        self.refresh_buttons()

    def fill_list(self, list_widget: QListWidget, targets: list) -> None:
        scroll_position = list_widget.verticalScrollBar().value()
        list_widget.blockSignals(True)
        list_widget.clear()

        if not targets:
            list_widget.addItem(QListWidgetItem(TARGET_EMPTY_TEXT))
        for target in targets:
            item = QListWidgetItem(self.target_text(target))
            item.setForeground(QColor(self.target_color(target)))
            item.setData(Qt.ItemDataRole.UserRole, target.target_id)
            list_widget.addItem(item)
            if target.target_id == self.selected_target_id:
                list_widget.setCurrentItem(item)

        list_widget.blockSignals(False)
        list_widget.verticalScrollBar().setValue(scroll_position)

    def sorted_targets(self, targets: list) -> list:
        sort_key = self.sortbox.currentData()
        if sort_key == SORT_BY_ID:
            return sorted(targets, key=lambda target: target.target_id)
        if sort_key == SORT_BY_CONFIDENCE:
            return sorted(targets, key=lambda target: sortable(target.confidence), reverse=True)
        return sorted(targets, key=lambda target: sortable(target.priority), reverse=True)

    @staticmethod
    def target_color(target) -> str:
        color = MAP_TARGET_COLORS.get(target.state)
        if color is None:
            return MAP_COLORS["label"]
        return color

    def target_text(self, target) -> str:
        if target.agent_id is None:
            agent_text = TARGET_NO_AGENT_TEXT
        else:
            agent_text = TARGET_AGENT_FORMAT.format(agent_id=target.agent_id)
        row = TARGET_ROW_FORMAT.format(
            target_id=target.target_id,
            label=or_missing(target.label),
            confidence=self.confidence_text(target),
            position=self.position_text(target),
        )
        state_text = TARGET_STATE_FORMAT.format(state=target.state)
        return f"{row}   {state_text}   {agent_text}"

    @staticmethod
    def confidence_text(target) -> str:
        if target.confidence is None:
            return MISSING_VALUE_TEXT
        return TARGET_CONFIDENCE_FORMAT.format(value=target.confidence)

    @staticmethod
    def position_text(target) -> str:
        if not target.has_position():
            return MISSING_VALUE_TEXT
        return TARGET_POSITION_FORMAT.format(
            latitude=target.latitude, longitude=target.longitude
        )

    # Selection and actions

    def handle_selection(self, list_widget: QListWidget) -> None:
        item = list_widget.currentItem()
        if item is None:
            return
        target_id = item.data(Qt.ItemDataRole.UserRole)
        if target_id is None:
            return
        self.selected_target_id = target_id
        self.refresh_buttons()
        self.target_selected.emit(target_id)

    def select_target(self, target_id: str) -> None:
        """Follow a click made on the map."""
        self.selected_target_id = target_id
        self.show_targets(self.targets)

    def selected_target(self):
        for target in self.targets:
            if target.target_id == self.selected_target_id:
                return target
        return None

    def refresh_buttons(self) -> None:
        target = self.selected_target()
        if target is None:
            self.vetobtn.setEnabled(False)
            self.requeuebtn.setEnabled(False)
            return
        # a vetoed target is the only one worth putting back
        self.vetobtn.setEnabled(not target.is_vetoed())
        self.requeuebtn.setEnabled(target.is_vetoed())

    def request_veto(self) -> None:
        target = self.selected_target()
        if target is None:
            return
        confirmed = QMessageBox.question(
            self,
            VETO_CONFIRM_TITLE,
            VETO_CONFIRM_QUESTION.format(target_id=target.target_id),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            self.veto_requested.emit(target.target_id)

    def request_requeue(self) -> None:
        target = self.selected_target()
        if target is None:
            return
        self.requeue_requested.emit(target.target_id)


def sortable(value: float | None) -> float:
    """Targets with nothing to sort on go to the bottom, not to the top."""
    if value is None:
        return float("-inf")
    return value


def or_missing(value) -> str:
    if value is None:
        return MISSING_VALUE_TEXT
    return str(value)
