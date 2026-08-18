"""Turns latitude/longitude into pixels, the way a tile map does it.

This is Web Mercator — the projection the tiles in the MBTiles file were cut in.
Using anything else would mean the imagery and the drawn boundaries disagreed
with each other, and on this display the boundary is the thing a judge checks.

Zoom is kept as a float so the view can be fitted to a polygon, while the tiles
themselves are fetched at the nearest whole zoom level and drawn scaled. That is
how slippy maps have always handled fractional zoom.
"""

import math

from PyQt6.QtCore import QPointF

from competitions.suas.config import (
    MAP_DEFAULT_LATITUDE,
    MAP_DEFAULT_LONGITUDE,
    MAP_DEFAULT_ZOOM,
    MAP_FIT_MARGIN_FRACTION,
    MAP_MAXIMUM_ZOOM,
    MAP_MINIMUM_ZOOM,
    MAP_TILE_SIZE_PIXELS,
)

# Length of the equator in metres, which is the width of the Mercator world.
EARTH_CIRCUMFERENCE_METRES = 40075016.686

# Mercator cannot represent the poles; this is the usual working limit.
MAXIMUM_MERCATOR_LATITUDE = 85.05112878


class MapProjection:
    """Where the map is centred, how far it is zoomed, and the maths for both."""

    def __init__(self) -> None:
        self.centre_latitude = MAP_DEFAULT_LATITUDE
        self.centre_longitude = MAP_DEFAULT_LONGITUDE
        self.zoom = float(MAP_DEFAULT_ZOOM)
        self.view_width = 0
        self.view_height = 0

    def set_view_size(self, width: int, height: int) -> None:
        self.view_width = width
        self.view_height = height

    def set_centre(self, latitude: float, longitude: float) -> None:
        self.centre_latitude = clamp_latitude(latitude)
        self.centre_longitude = longitude

    # Screen and world

    def world_size_pixels(self, zoom: float | None = None) -> float:
        if zoom is None:
            zoom = self.zoom
        return MAP_TILE_SIZE_PIXELS * (2.0**zoom)

    def to_world(self, latitude: float, longitude: float, zoom: float | None = None):
        """Global pixel position at a zoom level, origin at the top left."""
        world_size = self.world_size_pixels(zoom)
        latitude_radians = math.radians(clamp_latitude(latitude))
        x = (longitude + 180.0) / 360.0 * world_size
        y = (
            1.0
            - math.log(math.tan(latitude_radians) + 1.0 / math.cos(latitude_radians)) / math.pi
        ) / 2.0 * world_size
        return x, y

    def from_world(self, x: float, y: float, zoom: float | None = None):
        world_size = self.world_size_pixels(zoom)
        longitude = x / world_size * 360.0 - 180.0
        latitude = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / world_size))))
        return latitude, longitude

    def to_point(self, latitude: float, longitude: float) -> QPointF:
        centre_x, centre_y = self.to_world(self.centre_latitude, self.centre_longitude)
        x, y = self.to_world(latitude, longitude)
        return QPointF(
            self.view_width / 2 + (x - centre_x),
            self.view_height / 2 + (y - centre_y),
        )

    def to_coordinate(self, point: QPointF):
        """The inverse, for a click on the map."""
        centre_x, centre_y = self.to_world(self.centre_latitude, self.centre_longitude)
        x = centre_x + point.x() - self.view_width / 2
        y = centre_y + point.y() - self.view_height / 2
        return self.from_world(x, y)

    # Scale

    def metres_per_pixel(self) -> float:
        latitude_radians = math.radians(self.centre_latitude)
        return (
            EARTH_CIRCUMFERENCE_METRES
            * math.cos(latitude_radians)
            / self.world_size_pixels()
        )

    def pixels_per_metre(self) -> float:
        metres_per_pixel = self.metres_per_pixel()
        if metres_per_pixel <= 0:
            return 0.0
        return 1.0 / metres_per_pixel

    # Movement

    def zoom_by(self, steps: float) -> None:
        self.zoom = clamp(self.zoom + steps, MAP_MINIMUM_ZOOM, MAP_MAXIMUM_ZOOM)

    def pan_by(self, dx_pixels: float, dy_pixels: float) -> None:
        centre_x, centre_y = self.to_world(self.centre_latitude, self.centre_longitude)
        latitude, longitude = self.from_world(centre_x - dx_pixels, centre_y - dy_pixels)
        self.set_centre(latitude, longitude)

    def fit(self, coordinates: list) -> None:
        """Centre and zoom so every coordinate sits comfortably on screen."""
        if not coordinates or not self.view_width or not self.view_height:
            return

        latitudes = [latitude for latitude, _ in coordinates]
        longitudes = [longitude for _, longitude in coordinates]
        self.set_centre(
            (min(latitudes) + max(latitudes)) / 2,
            (min(longitudes) + max(longitudes)) / 2,
        )

        # Walk up the zoom levels and keep the last one that still fits. A
        # closed-form solution exists, but this is two dozen cheap iterations
        # and it reads as what it does.
        margin = 1 + 2 * MAP_FIT_MARGIN_FRACTION
        fitted_zoom = MAP_MINIMUM_ZOOM
        candidate = MAP_MINIMUM_ZOOM
        while candidate <= MAP_MAXIMUM_ZOOM:
            width_pixels, height_pixels = self.span_pixels(coordinates, candidate)
            fits_across = width_pixels * margin <= self.view_width
            fits_down = height_pixels * margin <= self.view_height
            if not fits_across or not fits_down:
                break
            fitted_zoom = candidate
            candidate += 1
        self.zoom = fitted_zoom

    def span_pixels(self, coordinates: list, zoom: float):
        xs = []
        ys = []
        for latitude, longitude in coordinates:
            x, y = self.to_world(latitude, longitude, zoom)
            xs.append(x)
            ys.append(y)
        return max(xs) - min(xs), max(ys) - min(ys)


def clamp(value: float, lowest: float, highest: float) -> float:
    return max(lowest, min(value, highest))


def clamp_latitude(latitude: float) -> float:
    return clamp(latitude, -MAXIMUM_MERCATOR_LATITUDE, MAXIMUM_MERCATOR_LATITUDE)
