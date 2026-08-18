"""Map imagery, read from an MBTiles file on disk.

There is no network code in here, and that is a requirement rather than a
preference: Appendix B and rule 5.3.5 forbid safety-critical function from
depending on the public internet, and there is no promising internet at a range
in Tulsa with fifty teams on site. The tiles are cut and packed before we
travel, and the map is verified with the laptop's networking switched off.

MBTiles stores rows bottom-up (TMS) while slippy-map maths counts them top-down,
so the row is flipped on the way in. That single line is the whole difference
between a correct map and a mirrored one.
"""

import logging
import sqlite3
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPixmap

from competitions.suas.config import MAP_TILE_CACHE_LIMIT, MAP_TILE_SIZE_PIXELS

logger = logging.getLogger(__name__)

TILE_QUERY = (
    "SELECT tile_data FROM tiles "
    "WHERE zoom_level = ? AND tile_column = ? AND tile_row = ? LIMIT 1"
)


class TileLayer:
    """Reads tiles out of one MBTiles file and keeps the recent ones decoded."""

    def __init__(self, tile_file: Path) -> None:
        self.tile_file = tile_file
        self.connection: sqlite3.Connection | None = None
        self.pixmap_cache: dict[tuple[int, int, int], QPixmap | None] = {}
        self.open_tile_file()

    def open_tile_file(self) -> None:
        if not self.tile_file.exists():
            logger.error(
                f"Map tile file is missing: {self.tile_file}. The map will draw the "
                f"mission on an empty background, and 3.0.6 needs a map to fly."
            )
            return
        try:
            # Read-only, and shared across threads is never needed: painting
            # happens on the Qt thread only.
            self.connection = sqlite3.connect(
                f"file:{self.tile_file}?mode=ro", uri=True, check_same_thread=True
            )
        except sqlite3.Error as database_error:
            logger.error(f"Map tile file could not be opened: {database_error}")
            return
        logger.info(f"Map tiles loaded from {self.tile_file}")

    def is_available(self) -> bool:
        return self.connection is not None

    def tile_pixmap(self, zoom: int, column: int, row: int) -> QPixmap | None:
        """One tile, decoded, or None when the file has no such tile."""
        cache_key = (zoom, column, row)
        if cache_key in self.pixmap_cache:
            return self.pixmap_cache[cache_key]

        pixmap = self.read_tile(zoom, column, row)
        self.remember(cache_key, pixmap)
        return pixmap

    def read_tile(self, zoom: int, column: int, row: int) -> QPixmap | None:
        if self.connection is None:
            return None

        flipped_row = (2**zoom - 1) - row
        try:
            cursor = self.connection.execute(TILE_QUERY, (zoom, column, flipped_row))
            found = cursor.fetchone()
        except sqlite3.Error as database_error:
            logger.warning(f"Map tile could not be read: {database_error}")
            return None

        if found is None:
            return None

        pixmap = QPixmap()
        if not pixmap.loadFromData(found[0]):
            logger.warning(f"Map tile {zoom}/{column}/{row} could not be decoded.")
            return None
        return pixmap

    def remember(self, cache_key, pixmap) -> None:
        """Keep the cache bounded; panning a whole mission would grow it forever."""
        if len(self.pixmap_cache) >= MAP_TILE_CACHE_LIMIT:
            self.pixmap_cache.clear()
        self.pixmap_cache[cache_key] = pixmap


def draw_tiles(painter, projection, tile_layer: TileLayer) -> int:
    """Cover the view with tiles from the nearest whole zoom level.

    Each tile is placed by projecting its own corners, so a fractional zoom or a
    fitted view simply scales the imagery instead of misaligning it.

    Returns how many tiles were actually drawn. A file that opened but has
    nothing at this zoom level draws none, and the caller has to be able to say
    so out loud — an empty background looks like a map with nothing on it, and
    3.0.6 does not let us fly without a map.
    """
    if not tile_layer.is_available():
        return 0

    tiles_drawn = 0
    tile_zoom = int(round(projection.zoom))
    tile_count = 2**tile_zoom

    top_left = projection.to_coordinate(QPointF(0, 0))
    bottom_right = projection.to_coordinate(
        QPointF(projection.view_width, projection.view_height)
    )

    first_column, first_row = tile_indices(projection, top_left, tile_zoom)
    last_column, last_row = tile_indices(projection, bottom_right, tile_zoom)

    for column in range(max(first_column, 0), min(last_column + 1, tile_count)):
        for row in range(max(first_row, 0), min(last_row + 1, tile_count)):
            pixmap = tile_layer.tile_pixmap(tile_zoom, column, row)
            if pixmap is None:
                continue
            # The whole tile scales into the rectangle its own corners project
            # to, which is what makes a fractional zoom look right.
            painter.drawPixmap(
                tile_rectangle(projection, tile_zoom, column, row),
                pixmap,
                QRectF(pixmap.rect()),
            )
            tiles_drawn += 1
    return tiles_drawn


def tile_indices(projection, coordinate, tile_zoom: int):
    latitude, longitude = coordinate
    x, y = projection.to_world(latitude, longitude, tile_zoom)
    return int(x // MAP_TILE_SIZE_PIXELS), int(y // MAP_TILE_SIZE_PIXELS)


def tile_rectangle(projection, tile_zoom: int, column: int, row: int) -> QRectF:
    """Where one tile lands on screen, from its own north-west and south-east corners."""
    north_west_latitude, north_west_longitude = projection.from_world(
        column * MAP_TILE_SIZE_PIXELS, row * MAP_TILE_SIZE_PIXELS, tile_zoom
    )
    south_east_latitude, south_east_longitude = projection.from_world(
        (column + 1) * MAP_TILE_SIZE_PIXELS, (row + 1) * MAP_TILE_SIZE_PIXELS, tile_zoom
    )
    return QRectF(
        projection.to_point(north_west_latitude, north_west_longitude),
        projection.to_point(south_east_latitude, south_east_longitude),
    )
