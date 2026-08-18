"""Per-hop link health and the antenna tracker's pointing state.

Nothing here is a command; it is the earliest warning the operator gets that
the mission is about to lose a vehicle's telemetry.
"""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem

from competitions.international_uav.config import (
    LINK_AGE_FORMAT,
    LINK_EMPTY_TEXT,
    LINK_LATENCY_FORMAT,
    LINK_LOSS_FORMAT,
    LINK_NO_DATA_TEXT,
    LINK_PANEL_TITLE,
    LINK_ROW_FORMAT,
    MISSING_VALUE_TEXT,
    TRACKER_LOCKED_FORMAT,
    TRACKER_LOST_TEXT,
    TRACKER_UNKNOWN_TEXT,
)
from theme import set_role
from theme.tokens import ROLE_READOUT, STATUS_CRITICAL, TEXT_SECONDARY
from widgets import Card


class LinkHealthPanel(Card):
    """One row per link, plus the antenna tracker line underneath."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent, LINK_PANEL_TITLE)

        self.linklist = QListWidget(self)
        self.trackerlbl = QLabel(TRACKER_UNKNOWN_TEXT, self)
        set_role(self.trackerlbl, ROLE_READOUT)

        self.add_widget(self.linklist)
        self.add_widget(self.trackerlbl)

    def show_links(self, links: list, tracker) -> None:
        self.linklist.clear()
        if not links:
            self.linklist.addItem(QListWidgetItem(LINK_EMPTY_TEXT))
        for link in links:
            self.linklist.addItem(self.link_item(link))
        self.trackerlbl.setText(self.tracker_text(tracker))

    def link_item(self, link) -> QListWidgetItem:
        item = QListWidgetItem(self.link_text(link))
        # A list item paints its own text, so the state colour is read from the
        # design tokens rather than matched by a stylesheet rule.
        if link.is_degraded():
            item.setForeground(QColor(STATUS_CRITICAL))
        else:
            item.setForeground(QColor(TEXT_SECONDARY))
        return item

    def link_text(self, link) -> str:
        return LINK_ROW_FORMAT.format(
            name=link.name,
            latency=self.measured(LINK_LATENCY_FORMAT, link.latency_ms),
            loss=self.measured(LINK_LOSS_FORMAT, link.loss_percent),
            age=self.age_text(link.last_seen_ms),
        )

    @staticmethod
    def measured(value_format: str, value: float | None) -> str:
        if value is None:
            return MISSING_VALUE_TEXT
        return value_format.format(value=value)

    @staticmethod
    def age_text(last_seen_ms: float | None) -> str:
        if last_seen_ms is None:
            return LINK_NO_DATA_TEXT
        return LINK_AGE_FORMAT.format(last_seen_ms=last_seen_ms)

    @staticmethod
    def tracker_text(tracker) -> str:
        if tracker.locked is None:
            return TRACKER_UNKNOWN_TEXT
        if not tracker.locked:
            return TRACKER_LOST_TEXT
        if tracker.error_degrees is None:
            return TRACKER_UNKNOWN_TEXT
        return TRACKER_LOCKED_FORMAT.format(error_deg=tracker.error_degrees)
