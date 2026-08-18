"""Is the aircraft inside the boundary, and how close is the edge.

Rule 3.0.4 terminates the mission for going out of bounds, so the ribbon shows
the distance to the boundary continuously and the operator is never surprised by
one. Both answers are needed every telemetry update, which is why they are plain
functions over a coordinate list rather than anything with state.

The flight area is about a mile across, so a flat local projection around the
point being tested is accurate to well under a metre and costs nothing.
"""

import math

# Mean earth radius in metres, for the flat local projection.
EARTH_RADIUS_METRES = 6371000.0


def offset_metres(from_latitude, from_longitude, to_latitude, to_longitude):
    """East and north metres from one coordinate to another."""
    latitude_radians = math.radians(from_latitude)
    east = (
        math.radians(to_longitude - from_longitude)
        * EARTH_RADIUS_METRES
        * math.cos(latitude_radians)
    )
    north = math.radians(to_latitude - from_latitude) * EARTH_RADIUS_METRES
    return east, north


def distance_metres(from_latitude, from_longitude, to_latitude, to_longitude) -> float:
    east, north = offset_metres(from_latitude, from_longitude, to_latitude, to_longitude)
    return math.hypot(east, north)


def is_inside_polygon(latitude: float, longitude: float, polygon: list) -> bool:
    """Ray casting: count the edges a ray to the east crosses."""
    if len(polygon) < 3:
        return False

    inside = False
    previous_latitude, previous_longitude = polygon[-1]
    for vertex_latitude, vertex_longitude in polygon:
        spans_latitude = (vertex_latitude > latitude) != (previous_latitude > latitude)
        if spans_latitude:
            latitude_fraction = (latitude - vertex_latitude) / (
                previous_latitude - vertex_latitude
            )
            crossing_longitude = vertex_longitude + latitude_fraction * (
                previous_longitude - vertex_longitude
            )
            if longitude < crossing_longitude:
                inside = not inside
        previous_latitude, previous_longitude = vertex_latitude, vertex_longitude
    return inside


def distance_to_polygon_metres(latitude: float, longitude: float, polygon: list) -> float | None:
    """Shortest distance to the boundary itself, inside or outside it."""
    if len(polygon) < 2:
        return None

    shortest = None
    previous_vertex = polygon[-1]
    for vertex in polygon:
        edge_distance = distance_to_segment_metres(
            latitude, longitude, previous_vertex, vertex
        )
        if shortest is None or edge_distance < shortest:
            shortest = edge_distance
        previous_vertex = vertex
    return shortest


def distance_to_segment_metres(latitude, longitude, start_vertex, end_vertex) -> float:
    """Distance to one edge, worked in metres east and north of the query point."""
    start_east, start_north = offset_metres(
        latitude, longitude, start_vertex[0], start_vertex[1]
    )
    end_east, end_north = offset_metres(latitude, longitude, end_vertex[0], end_vertex[1])

    edge_east = end_east - start_east
    edge_north = end_north - start_north
    edge_length_squared = edge_east**2 + edge_north**2
    if edge_length_squared == 0:
        return math.hypot(start_east, start_north)

    # Where along the edge the closest point sits, clamped to its ends.
    along_edge = -(start_east * edge_east + start_north * edge_north) / edge_length_squared
    along_edge = max(0.0, min(1.0, along_edge))
    closest_east = start_east + along_edge * edge_east
    closest_north = start_north + along_edge * edge_north
    return math.hypot(closest_east, closest_north)
