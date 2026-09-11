"""The picture of the ground under the mission: the Pasifik's scan, live.

The ground station warps each still the aircraft sends onto a fixed grid of
georeferenced tiles and writes them to this machine's disk. Each message names
one tile, says where its top left corner is and what one of its pixels is worth
on the ground — which is everything needed to draw it, so this layer never has
to know where the mosaic's origin is or how big it has grown.

Both programs run on the mission laptop, so a tile is opened from the path it
was written to. Nothing here reaches the network.
"""

import logging
from collections import OrderedDict

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QImage

from competitions.international_uav.config import MAP_MOSAIC_MAX_TILES

logger = logging.getLogger(__name__)


class MosaicLayer:
    """Holds the tiles that have arrived and draws the ones on screen."""

    def __init__(self) -> None:
        # Ordered by when each tile was last painted on, so the stalest goes
        # first when the layer is full.
        self.tiles: OrderedDict = OrderedDict()
        # Which ground station run the held tiles came from. A new run builds
        # its map from nothing, so tiles from before it are its predecessor's
        # — and their revisions, which restart with the run, say nothing about
        # the tiles the new run sends.
        self.session = None

    def add_tile(self, tile_id, latitude, longitude, metres_per_pixel, size_pixels, path,
                 revision, session) -> bool:
        """Take one tile the ground station has just written.

        Returns:
            bool: Whether anything changed and the map needs repainting.
        """
        # Letting go of a run's tiles is itself a change worth repainting for.
        cleared = False
        if session != self.session:
            cleared = bool(self.tiles)
            self.tiles.clear()
            self.session = session

        held = self.tiles.get(tile_id)
        if held is not None and held.revision >= revision:
            return cleared

        image = QImage(path)
        if image.isNull():
            logger.warning(f"Map tile {tile_id} could not be read from {path}.")
            return cleared

        self.tiles[tile_id] = MosaicTile(
            image, latitude, longitude, metres_per_pixel, size_pixels, revision
        )
        self.tiles.move_to_end(tile_id)
        while len(self.tiles) > MAP_MOSAIC_MAX_TILES:
            self.tiles.popitem(last=False)
        return True

    def is_empty(self) -> bool:
        return not self.tiles

    def corners(self) -> list:
        """Where the held tiles are, for the map to place and fit itself by.

        A tile is a position like any other: the ground under it was flown over
        and georeferenced. Without this the mosaic could be on screen while the
        projection still had no origin, and a right-click on ground the operator
        could see was refused for having nowhere to put it.
        """
        return [(tile.latitude, tile.longitude) for tile in self.tiles.values()]


class MosaicTile:
    """One square of the ground, and where it belongs."""

    def __init__(self, image, latitude, longitude, metres_per_pixel, size_pixels, revision) -> None:
        self.image = image
        # The tile's top left corner, which is where it is anchored on the map.
        self.latitude = latitude
        self.longitude = longitude
        self.metres_per_pixel = metres_per_pixel
        self.size_pixels = size_pixels
        self.revision = revision

    def screen_rectangle(self, projection) -> QRectF:
        """Where this tile sits on the widget right now."""
        top_left = projection.to_point(self.latitude, self.longitude)
        side = self.size_pixels * self.metres_per_pixel * projection.pixels_per_metre
        return QRectF(top_left.x(), top_left.y(), side, side)


def draw_mosaic(painter, projection, layer) -> None:
    """Paint every tile that falls inside the view, under everything else."""
    view = QRectF(0, 0, projection.view_width, projection.view_height)
    for tile in list(layer.tiles.values()):
        rectangle = tile.screen_rectangle(projection)
        if not view.intersects(rectangle):
            continue
        painter.drawImage(rectangle, tile.image)
