"""Where the objects really are, and how far off the detector put each one.

These points are typed in on this laptop and never leave it. Nobody knows where
the mannequin really is except whoever walked out and put it there, so there is
nobody to ask: the aircraft cannot be sent the answer it is being marked
against, and the error has to be worked out here, on the ground.

The error is the distance from a truth point to the nearest sighting of the same
class. Nearest rather than newest, because the bench wants to know what the
detector is capable of before it wants to know how steady it is, and the count
that comes with it says how many sightings that best was picked from — one lucky
frame out of sixty is a different result from one out of two.

Plain Python: no Qt, no MQTT, no disk. Everything here is arithmetic on numbers
somebody typed in and numbers that came off the link.
"""

from competitions.suas.geometry import distance_metres


class TruthPoint:
    """One object, and where somebody measured it to be."""

    def __init__(self, point_id: str, target_class: str, latitude: float,
                 longitude: float) -> None:
        self.point_id = point_id
        self.target_class = target_class
        self.latitude = latitude
        self.longitude = longitude


class TruthPointStore:
    """The truth points, and every sighting this session has seen."""

    def __init__(self) -> None:
        self.points: list[TruthPoint] = []
        self.sightings: list = []
        self.added_count = 0

    def add(self, target_class: str, latitude: float, longitude: float) -> TruthPoint:
        """Take one point down and hand it back, with an id of its own."""
        self.added_count += 1
        point = TruthPoint(str(self.added_count), target_class, latitude, longitude)
        self.points.append(point)
        return point

    def remove(self, point_id: str) -> None:
        self.points = [point for point in self.points if point.point_id != point_id]

    def note_sighting(self, sighting) -> None:
        """Keep every sighting, including the ones with nowhere to put them.

        They are dropped when the error is worked out rather than on the way in,
        so the page can still count what the detector saw.
        """
        self.sightings.append(sighting)

    def error_for(self, point: TruthPoint) -> tuple:
        """How far the nearest sighting of this class was, and out of how many.

        Returns:
            tuple: (metres, sighting_count), or (None, 0) while nothing of that
            class has been given a place yet.
        """
        wanted_class = class_key(point.target_class)
        distances = []
        for sighting in self.sightings:
            position = sighting.position()
            if position is None:
                continue
            if class_key(sighting.target_class) != wanted_class:
                continue
            distances.append(
                distance_metres(point.latitude, point.longitude, position[0], position[1])
            )

        if not distances:
            return None, 0
        return min(distances), len(distances)

    def error_of(self, sighting) -> tuple:
        """How far one sighting was from the nearest truth point of its class.

        The other way round from :meth:`error_for`, and for a different reader:
        the table wants the best the detector managed, the log written beside
        each sighting wants how far out that one sighting was.

        Returns:
            tuple: (metres, point_id), or (None, None) when the sighting has
            no place or there is no truth point of its class.
        """
        position = sighting.position()
        if position is None:
            return None, None

        wanted_class = class_key(sighting.target_class)
        nearest = (None, None)
        for point in self.points:
            if class_key(point.target_class) != wanted_class:
                continue
            metres = distance_metres(point.latitude, point.longitude,
                                     position[0], position[1])
            if nearest[0] is None or metres < nearest[0]:
                nearest = (metres, point.point_id)
        return nearest


def class_key(target_class: str) -> str:
    """Classes are matched with the case and the stray spaces ignored.

    The class beside a truth point is typed by hand and the one on a sighting
    comes from the model, so MANNEQUIN and mannequin have to be the same object
    or the bench measures nothing at all.
    """
    return target_class.strip().casefold()
