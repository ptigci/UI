"""The competition drawn on the map: flight boundary, search boundaries, runways.

Rule 3.0.6 requires the display to show the flight boundaries and "all other
competition elements", and the GCS judge sits watching it. So these are drawn
from the coordinates in config/mission.toml, always, and the flight boundary is
drawn thick enough to see the aircraft approaching it — an excursion terminates
the mission (3.0.4), and the operator should never be surprised by one.

The search boundary for the other runway is drawn too, but dimmed. Both are in
the handbook and the judge can see which one we think is ours.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen, QPolygonF

from competitions.suas.config import (
    FLIGHT_BOUNDARY,
    MAP_COLORS,
    MAP_FLIGHT_BOUNDARY_WIDTH,
    MAP_RUNWAY_WIDTH,
    MAP_SEARCH_BOUNDARY_WIDTH,
    RUNWAY_OUTLINES,
    RUNWAY_PROFILE,
    SEARCH_BOUNDARIES,
)


def draw_boundaries(painter, projection) -> None:
    draw_flight_boundary(painter, projection)
    draw_search_boundaries(painter, projection)
    draw_runways(painter, projection)


def draw_flight_boundary(painter, projection) -> None:
    painter.setPen(
        QPen(QColor(MAP_COLORS["flight_boundary"]), MAP_FLIGHT_BOUNDARY_WIDTH)
    )
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPolygon(polygon_for(projection, FLIGHT_BOUNDARY))


def draw_search_boundaries(painter, projection) -> None:
    """Ours in full colour, the other runway's dimmed but present."""
    for profile, boundary in SEARCH_BOUNDARIES.items():
        if not boundary:
            continue
        if profile == RUNWAY_PROFILE:
            colour = MAP_COLORS["search_boundary"]
        else:
            colour = MAP_COLORS["search_boundary_inactive"]
        painter.setPen(QPen(QColor(colour), MAP_SEARCH_BOUNDARY_WIDTH))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(polygon_for(projection, boundary))


def draw_runways(painter, projection) -> None:
    """Empty until the corner coordinates are taken off the Appendix A file."""
    painter.setPen(QPen(QColor(MAP_COLORS["runway"]), MAP_RUNWAY_WIDTH))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for outline in RUNWAY_OUTLINES.values():
        if not outline:
            continue
        painter.drawPolygon(polygon_for(projection, outline))


def polygon_for(projection, coordinates: list) -> QPolygonF:
    return QPolygonF(
        [projection.to_point(latitude, longitude) for latitude, longitude in coordinates]
    )
