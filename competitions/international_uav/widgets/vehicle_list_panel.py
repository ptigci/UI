"""The left column: one card per vehicle, Pasifik first."""

from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from competitions.international_uav.widgets.vehicle_card import VehicleCard
from theme import flush_layout


class VehicleListPanel(QScrollArea):
    """Scrolling list of vehicle cards that keeps its own card index."""

    def __init__(self, vehicles: list, parent=None) -> None:
        super().__init__(parent)
        self.cards: dict[str, VehicleCard] = {}

        card_container = QWidget(self)
        container_layout = QVBoxLayout(card_container)
        flush_layout(container_layout)
        for vehicle in vehicles:
            card = VehicleCard(vehicle, card_container)
            self.cards[vehicle.vehicle_id] = card
            container_layout.addWidget(card)
        container_layout.addStretch()

        self.setWidget(card_container)
        self.setWidgetResizable(True)

    def refresh_vehicle(self, vehicle_id: str) -> None:
        card = self.cards.get(vehicle_id)
        if card is not None:
            card.refresh()

    def refresh_staleness(self) -> None:
        """Called on the window's timer: ages keep counting without new data."""
        for card in self.cards.values():
            card.refresh_staleness()
