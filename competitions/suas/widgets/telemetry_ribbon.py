"""The row the judge reads.

Rule 3.0.6 requires the display to indicate the UAS position, ground speed in
knots and altitude in feet AGL, and Appendix B adds the waypoint threshold under
50 ft to the ground station inspection. Those units are not a preference: knots
and feet, converted here through units.py, never with a factor written inline.

Altitude is the field to be careful with. The envelope is [150, 400] ft AGL and
the terrain inside the flight boundary spans 633-748 ft MSL against a runway at
about 690 ft, so height above the launch point is not AGL over the high ground.
This shows what the aircraft reports as AGL and, when the aircraft also reports a
terrain clearance, prefers that — see gap 7 in COMPETITION_GAP_ANALYSIS.md.

Two link indicators, never one. They are different radios on different bands and
the operator has to know which of them died.

Every field is a shared Readout: a fixed caption over a monospaced value. The
caption is what lets the judge find a number on a row of eleven of them, and the
monospace is what stops the row shuffling sideways as the digits change.
"""

from PyQt6.QtWidgets import QGridLayout, QWidget

from competitions.suas.config import (
    ALTITUDE_CEILING_FEET,
    ALTITUDE_FLOOR_FEET,
    BOUNDARY_CAUTION_FEET,
    BOUNDARY_CRITICAL_FEET,
    MISSING_VALUE_TEXT,
    RIBBON_AIRSPEED_CAPTION,
    RIBBON_AIRSPEED_FORMAT,
    RIBBON_ALTITUDE_CAPTION,
    RIBBON_ALTITUDE_FORMAT,
    RIBBON_ARMED_CAPTION,
    RIBBON_ARMED_TEXT,
    RIBBON_BATTERY_CAPTION,
    RIBBON_BATTERY_FORMAT,
    RIBBON_BATTERY_SOURCE_FORMAT,
    RIBBON_BOUNDARY_CAPTION,
    RIBBON_BOUNDARY_FORMAT,
    RIBBON_BOUNDARY_OUTSIDE_TEXT,
    RIBBON_COLUMNS,
    RIBBON_DISARMED_TEXT,
    RIBBON_GPS_CAPTION,
    RIBBON_GPS_FORMAT,
    RIBBON_GROUND_SPEED_CAPTION,
    RIBBON_GROUND_SPEED_FORMAT,
    RIBBON_HOME_CAPTION,
    RIBBON_HOME_FORMAT,
    RIBBON_LINK_DOWN_TEXT,
    RIBBON_LINK_UP_TEXT,
    RIBBON_MINIMUM_HEIGHT,
    RIBBON_MISSION_LINK_CAPTION,
    RIBBON_MODE_CAPTION,
    RIBBON_MODE_FORMAT,
    RIBBON_SAFETY_LINK_CAPTION,
    RIBBON_WAYPOINT_RADIUS_CAPTION,
    RIBBON_WAYPOINT_RADIUS_FORMAT,
    WAYPOINT_THRESHOLD_LIMIT_FEET,
)
from competitions.suas.units import (
    metres_per_second_to_knots,
    metres_to_feet,
    metres_to_miles,
)
from theme import set_surface, space_layout
from theme.tokens import (
    AS_STRIP,
    SPACE_LG,
    SPACE_SM,
    SPACE_XL,
    STATE_CAUTION,
    STATE_CRITICAL,
    STATE_NONE,
)
from widgets import Readout


class TelemetryRibbon(QWidget):
    """Mode, armed, knots, feet AGL, battery, GPS, both links, radius, distances."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        set_surface(self, AS_STRIP)
        self.setMinimumHeight(RIBBON_MINIMUM_HEIGHT)

        self.mode_reading = Readout(RIBBON_MODE_CAPTION, parent=self)
        self.armed_reading = Readout(RIBBON_ARMED_CAPTION, parent=self)
        self.ground_speed_reading = Readout(RIBBON_GROUND_SPEED_CAPTION, parent=self)
        self.airspeed_reading = Readout(RIBBON_AIRSPEED_CAPTION, parent=self)
        self.altitude_reading = Readout(RIBBON_ALTITUDE_CAPTION, parent=self)
        self.battery_reading = Readout(RIBBON_BATTERY_CAPTION, parent=self)
        self.gps_reading = Readout(RIBBON_GPS_CAPTION, parent=self)
        self.safety_link_reading = Readout(RIBBON_SAFETY_LINK_CAPTION, parent=self)
        self.mission_link_reading = Readout(RIBBON_MISSION_LINK_CAPTION, parent=self)
        self.waypoint_radius_reading = Readout(RIBBON_WAYPOINT_RADIUS_CAPTION, parent=self)
        self.boundary_reading = Readout(RIBBON_BOUNDARY_CAPTION, parent=self)
        self.home_reading = Readout(RIBBON_HOME_CAPTION, parent=self)

        self.readings = [
            self.mode_reading,
            self.armed_reading,
            self.ground_speed_reading,
            self.airspeed_reading,
            self.altitude_reading,
            self.battery_reading,
            self.gps_reading,
            self.safety_link_reading,
            self.mission_link_reading,
            self.waypoint_radius_reading,
            self.boundary_reading,
            self.home_reading,
        ]
        self.build_layout()
        self.show_nothing()

    def build_layout(self) -> None:
        """Two rows, so the row stays short and the map keeps the height."""
        ribbon_layout = QGridLayout(self)
        space_layout(ribbon_layout, SPACE_LG, SPACE_SM)
        ribbon_layout.setHorizontalSpacing(SPACE_XL)
        for position, reading in enumerate(self.readings):
            ribbon_layout.addWidget(
                reading, position // RIBBON_COLUMNS, position % RIBBON_COLUMNS
            )
        # Even columns, so a reading stays in the same place on the row whatever
        # the number in it happens to be that second.
        for column in range(RIBBON_COLUMNS):
            ribbon_layout.setColumnStretch(column, 1)

    # Display

    def show_nothing(self) -> None:
        """Before the first telemetry, every field says so rather than showing zero."""
        for reading in self.readings:
            reading.set_value(MISSING_VALUE_TEXT)
            reading.set_state(STATE_NONE)

    def show_vehicle(self, vehicle) -> None:
        self.show_mode(vehicle.mode)
        self.show_armed(vehicle.armed)
        self.show_ground_speed(vehicle.ground_speed_metres_per_second)
        self.show_airspeed(vehicle.airspeed_metres_per_second)
        self.show_altitude(vehicle)
        self.show_battery(vehicle.battery_voltage, vehicle.battery_percent,
                          vehicle.battery_source)
        self.show_gps(vehicle.gps_fix, vehicle.satellite_count)

    def show_mode(self, mode) -> None:
        if mode is None:
            self.mode_reading.set_value(MISSING_VALUE_TEXT)
            return
        self.mode_reading.set_value(RIBBON_MODE_FORMAT.format(mode=mode))

    def show_armed(self, armed) -> None:
        if armed is None:
            self.armed_reading.set_value(MISSING_VALUE_TEXT)
            return
        if armed:
            self.armed_reading.set_value(RIBBON_ARMED_TEXT)
        else:
            self.armed_reading.set_value(RIBBON_DISARMED_TEXT)

    def show_ground_speed(self, metres_per_second) -> None:
        if metres_per_second is None:
            self.ground_speed_reading.set_value(MISSING_VALUE_TEXT)
            return
        knots = metres_per_second_to_knots(metres_per_second)
        self.ground_speed_reading.set_value(RIBBON_GROUND_SPEED_FORMAT.format(knots=knots))

    def show_airspeed(self, metres_per_second) -> None:
        """What the operator flies by: metric first, the judge's knots beside it."""
        if metres_per_second is None:
            self.airspeed_reading.set_value(MISSING_VALUE_TEXT)
            return
        self.airspeed_reading.set_value(RIBBON_AIRSPEED_FORMAT.format(
            metres_per_second=metres_per_second,
            knots=metres_per_second_to_knots(metres_per_second),
        ))

    def show_altitude(self, vehicle) -> None:
        """Prefer a reported terrain clearance; barometric height is not AGL."""
        if vehicle.terrain_clearance_metres is not None:
            altitude_metres = vehicle.terrain_clearance_metres
        else:
            altitude_metres = vehicle.altitude_agl_metres

        if altitude_metres is None:
            self.altitude_reading.set_value(MISSING_VALUE_TEXT)
            self.altitude_reading.set_state(STATE_NONE)
            return

        feet = metres_to_feet(altitude_metres)
        self.altitude_reading.set_value(RIBBON_ALTITUDE_FORMAT.format(feet=feet))
        if feet < ALTITUDE_FLOOR_FEET or feet > ALTITUDE_CEILING_FEET:
            self.altitude_reading.set_state(STATE_CRITICAL)
        else:
            self.altitude_reading.set_state(STATE_NONE)

    def show_battery(self, voltage, percent, source) -> None:
        if voltage is None or percent is None:
            self.battery_reading.set_value(MISSING_VALUE_TEXT)
            return

        reading = RIBBON_BATTERY_FORMAT.format(voltage=voltage, percent=percent)
        if source is not None:
            reading += RIBBON_BATTERY_SOURCE_FORMAT.format(
                source=source.upper()
            )
        self.battery_reading.set_value(reading)

    def show_gps(self, fix, satellites) -> None:
        if fix is None or satellites is None:
            self.gps_reading.set_value(MISSING_VALUE_TEXT)
            return
        self.gps_reading.set_value(
            RIBBON_GPS_FORMAT.format(fix=fix, satellites=satellites)
        )

    def show_links(self, safety_up: bool, mission_up: bool) -> None:
        self.show_link(self.safety_link_reading, safety_up)
        self.show_link(self.mission_link_reading, mission_up)

    def show_link(self, reading: Readout, is_up: bool) -> None:
        if is_up:
            reading.set_value(RIBBON_LINK_UP_TEXT)
            reading.set_state(STATE_NONE)
        else:
            reading.set_value(RIBBON_LINK_DOWN_TEXT)
            reading.set_state(STATE_CRITICAL)

    def show_waypoint_radius(self, radius_metres) -> None:
        """The inspector reads this one off the screen, so it is always in feet."""
        if radius_metres is None:
            self.waypoint_radius_reading.set_value(MISSING_VALUE_TEXT)
            self.waypoint_radius_reading.set_state(STATE_NONE)
            return

        feet = metres_to_feet(radius_metres)
        self.waypoint_radius_reading.set_value(
            RIBBON_WAYPOINT_RADIUS_FORMAT.format(feet=feet)
        )
        if feet >= WAYPOINT_THRESHOLD_LIMIT_FEET:
            self.waypoint_radius_reading.set_state(STATE_CRITICAL)
        else:
            self.waypoint_radius_reading.set_state(STATE_NONE)

    def show_boundary_distance(self, distance_metres, inside: bool) -> None:
        if distance_metres is None:
            self.boundary_reading.set_value(MISSING_VALUE_TEXT)
            self.boundary_reading.set_state(STATE_NONE)
            return

        if not inside:
            self.boundary_reading.set_value(RIBBON_BOUNDARY_OUTSIDE_TEXT)
            self.boundary_reading.set_state(STATE_CRITICAL)
            return

        feet = metres_to_feet(distance_metres)
        self.boundary_reading.set_value(RIBBON_BOUNDARY_FORMAT.format(feet=feet))
        if feet <= BOUNDARY_CRITICAL_FEET:
            self.boundary_reading.set_state(STATE_CRITICAL)
        elif feet <= BOUNDARY_CAUTION_FEET:
            self.boundary_reading.set_state(STATE_CAUTION)
        else:
            self.boundary_reading.set_state(STATE_NONE)

    def show_home_distance(self, distance_metres) -> None:
        if distance_metres is None:
            self.home_reading.set_value(MISSING_VALUE_TEXT)
            return
        self.home_reading.set_value(
            RIBBON_HOME_FORMAT.format(miles=metres_to_miles(distance_metres))
        )
