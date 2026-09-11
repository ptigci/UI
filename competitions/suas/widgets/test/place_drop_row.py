"""A drop on a place the operator names, in three steps that stay apart.

Type a latitude and longitude and press PLAN THE ROUTE. The aircraft works out
the way there with the route planner it already has, publishes the route, and
the map draws it. Nothing moves. Only when the operator presses FLY IT AND DROP
does the aircraft fly that route and let the payload go when it arrives.

The three steps are separate on purpose. A route that flew itself the moment it
was computed would give nobody the chance to see it was wrong -- and a route
that goes the long way round, through the boundary, or to a place with a digit
mistyped in it is exactly what this page is for catching.

The payloads start from the config so the row works before the aircraft is
talking, and the payload state it publishes replaces them, so the chooser
holds whatever it says it is carrying rather than a list written here.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from competitions.suas.config import (
    ROUTE_STATE_APPROVED,
    ROUTE_STATE_DONE,
    ROUTE_STATE_FLYING,
    ROUTE_STATE_PROPOSED,
    ROUTE_STATE_REJECTED,
    TEST_DROP_TEXT,
)
from competitions.suas.widgets.command_button import command_button
from theme import flush_layout, set_role, set_state
from theme.tokens import (
    ROLE_HINT,
    ROLE_SUBHEADING,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    STATE_CAUTION,
    STATE_IDLE,
    STATE_NONE,
    STATE_OK,
    VARIANT_CAUTION,
    VARIANT_GHOST,
    VARIANT_PRIMARY,
)


class PlaceDropRow(QWidget):
    """The place, the route the aircraft offers, and the answer to it."""

    # Both presses carry the same five: where, how high, which payload, and
    # how close counts as arrived.
    plan_requested = pyqtSignal(float, float, float, str, float)
    plan_and_drop_requested = pyqtSignal(float, float, float, str, float)
    approve_requested = pyqtSignal(str)
    reject_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # The answer carries the id of the route it is answering, so an APPROVE
        # left on screen while the aircraft replans cannot fly a route the
        # operator has already moved on from.
        self.route_id: str = ""
        self.station_names: list[str] = []

        self.latitude_input = coordinate_input(
            TEST_DROP_TEXT["latitude_minimum"], TEST_DROP_TEXT["latitude_maximum"], self
        )
        self.longitude_input = coordinate_input(
            TEST_DROP_TEXT["longitude_minimum"], TEST_DROP_TEXT["longitude_maximum"], self
        )

        self.altitude_input = QDoubleSpinBox(self)
        self.altitude_input.setRange(TEST_DROP_TEXT["altitude_minimum_metres"],
                                     TEST_DROP_TEXT["altitude_maximum_metres"])
        self.altitude_input.setSingleStep(TEST_DROP_TEXT["altitude_step_metres"])
        self.altitude_input.setSuffix(TEST_DROP_TEXT["altitude_suffix"])

        # How close to the place counts as arrived. The operator says what
        # "there" means rather than inheriting the mission's own radius, which
        # was chosen for flying a lap and not for putting a bottle on a mannequin.
        self.radius_input = QDoubleSpinBox(self)
        self.radius_input.setDecimals(TEST_DROP_TEXT["radius_decimals"])
        self.radius_input.setRange(TEST_DROP_TEXT["radius_minimum_metres"],
                                   TEST_DROP_TEXT["radius_maximum_metres"])
        self.radius_input.setSingleStep(TEST_DROP_TEXT["radius_step_metres"])
        self.radius_input.setValue(TEST_DROP_TEXT["radius_default_metres"])
        self.radius_input.setSuffix(TEST_DROP_TEXT["radius_suffix"])

        self.station_choice = QComboBox(self)
        # Filled from the config so there is something to choose before the
        # aircraft has said what it is carrying; its word replaces the list.
        self.show_station_names(TEST_DROP_TEXT["stations"])

        place_row = QHBoxLayout()
        flush_layout(place_row, SPACE_MD)
        place_row.addWidget(field(TEST_DROP_TEXT["latitude_caption"],
                                 self.latitude_input, self))
        place_row.addWidget(field(TEST_DROP_TEXT["longitude_caption"],
                                 self.longitude_input, self))

        payload_row = QHBoxLayout()
        flush_layout(payload_row, SPACE_MD)
        payload_row.addWidget(field(TEST_DROP_TEXT["altitude_caption"],
                                    self.altitude_input, self))
        payload_row.addWidget(field(TEST_DROP_TEXT["radius_caption"],
                                    self.radius_input, self))
        payload_row.addWidget(field(TEST_DROP_TEXT["station_caption"],
                                    self.station_choice, self))

        # Two ways to fly the same delivery, side by side. The left one plans
        # and waits to be looked at; the right one goes. The right one is the
        # more dangerous of the two and is coloured like the other presses that
        # put a payload out of the aircraft.
        plan_button = command_button(TEST_DROP_TEXT["plan_text"], VARIANT_PRIMARY, self)
        plan_button.clicked.connect(self.request_plan)

        drop_button = command_button(TEST_DROP_TEXT["drop_on_arrival_text"],
                                     VARIANT_CAUTION, self)
        drop_button.clicked.connect(self.request_plan_and_drop)

        press_row = QHBoxLayout()
        flush_layout(press_row, SPACE_SM)
        press_row.addWidget(plan_button)
        press_row.addWidget(drop_button)

        hint_label = QLabel(TEST_DROP_TEXT["place_hint_text"], self)
        set_role(hint_label, ROLE_HINT)
        hint_label.setWordWrap(True)

        self.route_label = QLabel(self)
        self.route_label.setWordWrap(True)

        self.approve_button = command_button(TEST_DROP_TEXT["approve_text"],
                                             VARIANT_CAUTION, self)
        self.approve_button.clicked.connect(self.request_approve)

        self.reject_button = command_button(TEST_DROP_TEXT["reject_text"],
                                            VARIANT_GHOST, self)
        self.reject_button.clicked.connect(self.request_reject)

        answer_row = QHBoxLayout()
        flush_layout(answer_row, SPACE_SM)
        answer_row.addWidget(self.approve_button)
        answer_row.addWidget(self.reject_button)

        heading_label = QLabel(TEST_DROP_TEXT["place_title"], self)
        set_role(heading_label, ROLE_SUBHEADING)

        row_layout = QVBoxLayout(self)
        flush_layout(row_layout, SPACE_SM)
        row_layout.addWidget(heading_label)
        row_layout.addLayout(place_row)
        row_layout.addLayout(payload_row)
        row_layout.addLayout(press_row)
        row_layout.addWidget(hint_label)
        row_layout.addWidget(self.route_label)
        row_layout.addLayout(answer_row)

        self.show_answer_buttons(False)
        self.show_route_status(TEST_DROP_TEXT["no_route_text"], STATE_NONE)

    # The operator's side

    def request_plan(self) -> None:
        """Work the route out and wait. Nothing moves until it is approved."""
        self.show_route_status(TEST_DROP_TEXT["route_planning_text"], STATE_CAUTION)
        self.request(self.plan_requested)

    def request_plan_and_drop(self) -> None:
        """Go there and drop, with nobody asked in between.

        The route is flown before anyone has looked at it, which is the whole
        difference between this press and the one beside it.
        """
        self.show_route_status(TEST_DROP_TEXT["planning_and_dropping_text"],
                               STATE_CAUTION)
        self.request(self.plan_and_drop_requested)

    def request(self, signal) -> None:
        """Send the place and how close counts as arrived, on either press."""
        self.show_answer_buttons(False)
        signal.emit(
            self.latitude_input.value(),
            self.longitude_input.value(),
            self.altitude_input.value(),
            self.station_choice.currentData(),
            self.radius_input.value(),
        )

    def request_approve(self) -> None:
        if not self.route_id:
            return
        self.approve_requested.emit(self.route_id)

    def request_reject(self) -> None:
        if not self.route_id:
            return
        self.reject_requested.emit(self.route_id)

    # What the aircraft says

    def show_stations(self, payload_state) -> None:
        """Fill the chooser from what the aircraft says it is carrying."""
        names = [station.name for station in payload_state.stations]
        if not names:
            return
        self.show_station_names(names)

    def show_station_names(self, names: list) -> None:
        """Put one entry per payload in the chooser, keeping what is chosen."""
        if names == self.station_names:
            return
        self.station_names = names
        self.station_choice.clear()
        for name in names:
            self.station_choice.addItem(bay_label(name), name)

    def show_route(self, route_plan) -> None:
        """The route on offer, and whether there is anything left to answer."""
        self.route_id = route_plan.route_id
        proposed = route_plan.state == ROUTE_STATE_PROPOSED
        self.show_answer_buttons(proposed)

        if proposed:
            self.show_route_status(
                TEST_DROP_TEXT["route_proposed_format"].format(
                    length=route_plan.length_metres,
                    seconds=route_plan.estimated_time_seconds,
                ),
                STATE_CAUTION,
            )
            return

        if route_plan.state in (ROUTE_STATE_APPROVED, ROUTE_STATE_FLYING):
            status, state = TEST_DROP_TEXT["route_flying_text"], STATE_CAUTION
        elif route_plan.state == ROUTE_STATE_DONE:
            status, state = TEST_DROP_TEXT["route_done_text"], STATE_OK
        elif route_plan.state == ROUTE_STATE_REJECTED:
            status, state = TEST_DROP_TEXT["route_rejected_text"], STATE_IDLE
        else:
            status, state = TEST_DROP_TEXT["no_route_text"], STATE_NONE
        self.show_route_reason(status, state, route_plan.reason)

    def show_answer_buttons(self, visible: bool) -> None:
        """Hidden rather than disabled: with no route there is nothing to answer."""
        self.approve_button.setVisible(visible)
        self.reject_button.setVisible(visible)

    def show_route_status(self, status: str, state: str) -> None:
        self.route_label.setText(status)
        set_state(self.route_label, state)

    def show_route_reason(self, status: str, state: str, reason: str) -> None:
        """The line, with whatever the aircraft had to add about the route.

        On a route it could not plan the reason is the whole diagnosis, and a
        line that said only "no route planned" would hide it.
        """
        if not reason:
            self.show_route_status(status, state)
            return
        self.show_route_status(
            TEST_DROP_TEXT["route_reason_format"].format(status=status,
                                                         reason=reason),
            state,
        )


def coordinate_input(minimum: float, maximum: float, parent) -> QDoubleSpinBox:
    """A latitude or longitude box, at the number of places a drop needs."""
    coordinate_box = QDoubleSpinBox(parent)
    coordinate_box.setDecimals(TEST_DROP_TEXT["coordinate_decimals"])
    coordinate_box.setRange(minimum, maximum)
    coordinate_box.setSingleStep(TEST_DROP_TEXT["coordinate_step"])
    return coordinate_box


def field(caption: str, input_widget, parent) -> QWidget:
    """One captioned input, so a row of them lines up."""
    caption_label = QLabel(caption, parent)
    set_role(caption_label, ROLE_HINT)

    holder = QWidget(parent)
    holder_layout = QVBoxLayout(holder)
    flush_layout(holder_layout, SPACE_XS)
    holder_layout.addWidget(caption_label)
    holder_layout.addWidget(input_widget)
    return holder


def bay_label(station_name: str) -> str:
    """"water_bottle" is a config name; the page says WATER BOTTLE."""
    return station_name.replace("_", " ").upper()
