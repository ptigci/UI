"""One vehicle's card in the left column.

Everything the operator needs to answer "is this aircraft healthy" at a
glance. A value the vehicle has not reported stays blank instead of showing a
zero, and a vehicle that has gone quiet says how long it has been quiet.
"""

from PyQt6.QtWidgets import QLabel

from competitions.international_uav.config import (
    BATTERY_CRITICAL_PERCENT,
    BATTERY_WARNING_PERCENT,
    CARD_AIRSPEED_FORMAT,
    CARD_ALTITUDE_FORMAT,
    CARD_ARMED_TEXT,
    CARD_BATTERY_FORMAT,
    CARD_DISARMED_TEXT,
    CARD_GPS_FORMAT,
    CARD_MODE_FORMAT,
    CARD_NO_TARGET_TEXT,
    CARD_NO_WAYPOINT_TEXT,
    CARD_POSITION_FORMAT,
    CARD_SPEED_FORMAT,
    CARD_STALE_FORMAT,
    CARD_STATE_FORMAT,
    CARD_TARGET_FORMAT,
    CARD_WAYPOINT_FORMAT,
    MISSING_VALUE_TEXT,
)
from theme import set_role, set_state
from theme.tokens import (
    ROLE_READOUT,
    SPACE_XS,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_OK,
    STATE_STALE,
)
from widgets import Card, StatusDot

MILLISECONDS_PER_SECOND = 1000


class VehicleCard(Card):
    """The live state of one vehicle, Pasifik or swarm agent."""

    def __init__(self, vehicle, parent=None) -> None:
        super().__init__(parent, vehicle.title)
        self.vehicle = vehicle

        # The dot repeats the rail on the card's edge, up where the eye starts.
        self.health_dot = StatusDot(STATE_OK, self)
        self.add_header_widget(self.health_dot)

        self.statelbl = self.build_line()
        self.batterylbl = self.build_line()
        self.positionlbl = self.build_line()
        self.altitudelbl = self.build_line()
        self.speedlbl = self.build_line()
        self.gpslbl = self.build_line()
        self.missionlbl = self.build_line()

        self.stalelbl = self.build_line()
        set_state(self.stalelbl, STATE_CRITICAL)

        # Lines of one vehicle's readings sit closer together than the cards do.
        self.card_layout.setSpacing(SPACE_XS)

        self.refresh()

    def build_line(self) -> QLabel:
        """Every reading is monospaced, so the column reads down as a table."""
        line = QLabel(self)
        set_role(line, ROLE_READOUT)
        self.add_widget(line)
        return line

    def refresh(self) -> None:
        """Redraw every value from the model."""
        self.statelbl.setText(self.state_text())
        self.batterylbl.setText(self.battery_text())
        self.positionlbl.setText(self.position_text())
        self.altitudelbl.setText(self.altitude_text())
        self.speedlbl.setText(self.speed_text())
        self.gpslbl.setText(self.gps_text())
        self.missionlbl.setText(self.mission_text())
        self.refresh_staleness()

    def refresh_staleness(self) -> None:
        """Age of the last message, and the colour that goes with it."""
        age_milliseconds = self.vehicle.age_milliseconds()
        if age_milliseconds is None or self.vehicle.is_stale():
            self.stalelbl.setVisible(True)
            if age_milliseconds is None:
                self.stalelbl.setText(MISSING_VALUE_TEXT)
            else:
                self.stalelbl.setText(
                    CARD_STALE_FORMAT.format(seconds=age_milliseconds / MILLISECONDS_PER_SECOND)
                )
        else:
            self.stalelbl.setVisible(False)
        self.apply_card_state(self.card_state())

    def card_state(self) -> str:
        if self.vehicle.is_stale():
            return STATE_STALE
        battery_percent = self.vehicle.battery_percent
        if battery_percent is None:
            return STATE_OK
        if battery_percent <= BATTERY_CRITICAL_PERCENT:
            return STATE_CRITICAL
        if battery_percent <= BATTERY_WARNING_PERCENT:
            return STATE_CAUTION
        return STATE_OK

    def apply_card_state(self, card_state: str) -> None:
        self.set_state(card_state)
        self.health_dot.set_state(card_state)

    # Text for each line

    def state_text(self) -> str:
        state = CARD_STATE_FORMAT.format(state=self.value_or_missing(self.vehicle.state))
        mode = CARD_MODE_FORMAT.format(mode=self.value_or_missing(self.vehicle.mode))
        if self.vehicle.armed is None:
            return f"{state}   {mode}"
        if self.vehicle.armed:
            armed_text = CARD_ARMED_TEXT
        else:
            armed_text = CARD_DISARMED_TEXT
        return f"{state}   {mode}   {armed_text}"

    def battery_text(self) -> str:
        if self.vehicle.battery_percent is None or self.vehicle.battery_voltage is None:
            return MISSING_VALUE_TEXT
        return CARD_BATTERY_FORMAT.format(
            percent=self.vehicle.battery_percent, voltage=self.vehicle.battery_voltage
        )

    def position_text(self) -> str:
        if not self.vehicle.has_position():
            return MISSING_VALUE_TEXT
        return CARD_POSITION_FORMAT.format(
            latitude=self.vehicle.latitude, longitude=self.vehicle.longitude
        )

    def altitude_text(self) -> str:
        if self.vehicle.altitude_agl is None:
            return MISSING_VALUE_TEXT
        return CARD_ALTITUDE_FORMAT.format(altitude=self.vehicle.altitude_agl)

    def speed_text(self) -> str:
        if self.vehicle.ground_speed is None:
            return MISSING_VALUE_TEXT
        speed_text = CARD_SPEED_FORMAT.format(ground_speed=self.vehicle.ground_speed)
        # airspeed comes from the pitot tube, which only the Pasifik carries
        if self.vehicle.is_pasifik and self.vehicle.airspeed is not None:
            speed_text = f"{speed_text}   {CARD_AIRSPEED_FORMAT.format(airspeed=self.vehicle.airspeed)}"
        return speed_text

    def gps_text(self) -> str:
        return CARD_GPS_FORMAT.format(
            gps_fix=self.value_or_missing(self.vehicle.gps_fix),
            rtk_status=self.value_or_missing(self.vehicle.rtk_status),
        )

    def mission_text(self) -> str:
        """The Pasifik flies a mission of waypoints; the agents are sent to a target."""
        if self.vehicle.is_pasifik:
            if self.vehicle.waypoint is None or self.vehicle.waypoint_total is None:
                return CARD_NO_WAYPOINT_TEXT
            return CARD_WAYPOINT_FORMAT.format(
                current=self.vehicle.waypoint, total=self.vehicle.waypoint_total
            )
        if self.vehicle.assigned_target is None:
            return CARD_NO_TARGET_TEXT
        return CARD_TARGET_FORMAT.format(target_id=self.vehicle.assigned_target)

    @staticmethod
    def value_or_missing(value) -> str:
        if value is None:
            return MISSING_VALUE_TEXT
        return str(value)
