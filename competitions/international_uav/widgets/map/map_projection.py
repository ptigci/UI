"""Turns latitude/longitude into pixels on the map widget.

The mission area is a few hundred metres across, so a local flat projection
around an origin is accurate enough and costs nothing: east/north metres from
the origin, then a scale and a centre to place them on screen.
"""

import math

from PyQt6.QtCore import QPointF

from competitions.international_uav.config import (
    MAP_DEFAULT_LATITUDE,
    MAP_DEFAULT_LONGITUDE,
    MAP_DEFAULT_SPAN_METRES,
    MAP_FIT_MARGIN,
    MAP_ZOOM_MAX,
    MAP_ZOOM_MIN,
)

# Mean earth radius in metres, used for the flat local projection.
EARTH_RADIUS_METRES = 6371000.0


class MapProjection:
    """Where the map is centred, how far it is zoomed in, and the maths for both."""

    def __init__(self) -> None:
        self.origin_latitude = MAP_DEFAULT_LATITUDE
        self.origin_longitude = MAP_DEFAULT_LONGITUDE
        self.origin_set = False
        # Centre of the view, in metres east and north of the origin.
        self.centre_east = 0.0
        self.centre_north = 0.0
        self.pixels_per_metre = 1.0
        self.view_width = 0
        self.view_height = 0

    def set_view_size(self, width: int, height: int) -> None:
        self.view_width = width
        self.view_height = height

    def set_origin(self, latitude: float, longitude: float) -> None:
        """First position seen becomes the origin; everything else is relative."""
        self.origin_latitude = latitude
        self.origin_longitude = longitude
        self.origin_set = True

    def to_metres(self, latitude: float, longitude: float) -> tuple[float, float]:
        latitude_radians = math.radians(self.origin_latitude)
        east = math.radians(longitude - self.origin_longitude) * EARTH_RADIUS_METRES * math.cos(
            latitude_radians
        )
        north = math.radians(latitude - self.origin_latitude) * EARTH_RADIUS_METRES
        return east, north

    def to_point(self, latitude: float, longitude: float) -> QPointF:
        east, north = self.to_metres(latitude, longitude)
        return self.metres_to_point(east, north)

    def metres_to_point(self, east: float, north: float) -> QPointF:
        x = self.view_width / 2 + (east - self.centre_east) * self.pixels_per_metre
        # north is up on the map, y grows downwards on the screen
        y = self.view_height / 2 - (north - self.centre_north) * self.pixels_per_metre
        return QPointF(x, y)

    def fit(self, coordinates: list) -> None:
        """Centre and zoom so every given coordinate is comfortably on screen."""
        if not coordinates or not self.view_width or not self.view_height:
            return

        eastings = []
        northings = []
        for latitude, longitude in coordinates:
            east, north = self.to_metres(latitude, longitude)
            eastings.append(east)
            northings.append(north)

        self.centre_east = (min(eastings) + max(eastings)) / 2
        self.centre_north = (min(northings) + max(northings)) / 2

        east_span = max(max(eastings) - min(eastings), MAP_DEFAULT_SPAN_METRES)
        north_span = max(max(northings) - min(northings), MAP_DEFAULT_SPAN_METRES)
        margin = 1 + 2 * MAP_FIT_MARGIN
        self.pixels_per_metre = min(
            self.view_width / (east_span * margin),
            self.view_height / (north_span * margin),
        )

    def zoom_by(self, factor: float) -> None:
        zoomed = self.pixels_per_metre * factor
        self.pixels_per_metre = max(MAP_ZOOM_MIN, min(zoomed, MAP_ZOOM_MAX))

    def pan_by(self, dx_pixels: float, dy_pixels: float) -> None:
        self.centre_east -= dx_pixels / self.pixels_per_metre
        self.centre_north += dy_pixels / self.pixels_per_metre
