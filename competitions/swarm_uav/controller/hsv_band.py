"""Turning the pixels the operator selected into HSV bands for a drone.

The band is measured the way the drone matches it: OpenCV's HSV, hue 0-179 and
saturation/value 0-255, which is Qt's HSV with the hue halved.

Hue is a circle cut open at 179/0, and red sits right on the cut — half of a
red circle's pixels read just above 0 and half just below 179. Read as a
minimum and a maximum that would come out as "0 to 179", a band that matches
everything on the field, so the hues are read around the circle instead: the
widest gap between neighbouring hues is the part of the circle the color does
not use, and the color is everything else.

The band comes out tight on hue and wide on the other two. Hue and saturation
are ratios between the red, green and blue a pixel carries, so the same paint
under half the light reads them in much the same place; value is the one that
carries the light itself. A band that fits the value it was measured at is a
band that stops matching the moment a cloud goes over, so only the floors are
measured here and both ceilings sit at the channel maximum.
"""

import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from competitions.swarm_uav.config import (
    COLOR_HUE_MARGIN,
    COLOR_MAX_SAMPLE_PIXELS,
    COLOR_MINIMUM_SATURATION,
    COLOR_SATURATION_MARGIN,
    COLOR_TRIM_PERCENT,
    COLOR_VALUE_FLOOR_RATIO,
)

HUE_MAXIMUM = 179
SATURATION_MAXIMUM = 255
VALUE_MAXIMUM = 255
HUE_CIRCLE = HUE_MAXIMUM + 1
QT_HUE_PER_OPENCV_HUE = 2
# What Qt answers for a pixel that has no hue at all — pure grey, or white.
ACHROMATIC_HUE = -1


def bands_from_samples(hues, saturations, values):
    """The HSV bands covering the sampled pixels, or None when none have a hue.

    Parameters:
        hues, saturations, values (list): one list per channel, as sample_hsv
            reads them. Several boxes can be measured into the same lists, and
            the band then covers all of them — which is how the same circle is
            taken once in sun and once under cloud.

    Returns:
        list: [[lower, upper], ...] HSV triples — two bands when the color
        wraps around the hue seam, one otherwise.
    """
    if not hues:
        return None

    saturation_range = (saturation_floor(saturations), SATURATION_MAXIMUM)
    value_range = (value_floor(values), VALUE_MAXIMUM)
    hue_low, hue_high = hue_range(hues)
    return split_at_seam(hue_low, hue_high, saturation_range, value_range)


def sample_hsv(image, selection):
    """Read the selected pixels into one list per HSV channel.

    Pixels with no hue are left out of the hue list only: they are still part
    of what was selected, and the saturation band is what ends up excluding
    them.
    """
    crop = subsampled(image.copy(selection))
    hues = []
    saturations = []
    values = []
    for row in range(crop.height()):
        for column in range(crop.width()):
            hue, saturation, value, _ = QColor(crop.pixel(column, row)).getHsv()
            if hue != ACHROMATIC_HUE:
                hues.append(hue // QT_HUE_PER_OPENCV_HUE)
            saturations.append(saturation)
            values.append(value)
    return hues, saturations, values


def joined_samples(earlier, later):
    """Two sets of channel samples as one, so a second box widens the first."""
    if earlier is None:
        return later
    return tuple(
        earlier_channel + later_channel
        for earlier_channel, later_channel in zip(earlier, later)
    )


def subsampled(crop):
    """The crop cut down to the sample limit, keeping its own pixel values.

    Nearest-neighbour on purpose: a smooth scale would average neighbouring
    pixels into colours that are not in the picture, and those averages are
    exactly what a band must not be built from.
    """
    selected_pixels = crop.width() * crop.height()
    if selected_pixels <= COLOR_MAX_SAMPLE_PIXELS:
        return crop
    sample_scale = math.sqrt(COLOR_MAX_SAMPLE_PIXELS / selected_pixels)
    return crop.scaled(
        max(1, int(crop.width() * sample_scale)),
        max(1, int(crop.height() * sample_scale)),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )


def trimmed_low_end(channel_values):
    """One channel's low end, with the extremes trimmed off."""
    ordered = sorted(channel_values)
    return ordered[len(ordered) * COLOR_TRIM_PERCENT // 100]


def saturation_floor(saturations):
    """The saturation floor, never below the configured minimum.

    This is the one number holding grey ground out of the mask. Hue says
    nothing about a pixel with no colour in it, so asphalt, dry grass and deep
    shadow carry whatever hue the noise gives them and a fair share of them
    land inside any band. A calibration taken in poor light reads saturations
    that are low and scattered, and the measured floor would follow them all
    the way down.
    """
    measured_floor = trimmed_low_end(saturations) - COLOR_SATURATION_MARGIN
    return max(COLOR_MINIMUM_SATURATION, measured_floor)


def value_floor(values):
    """The value floor as a share of what was measured, not a subtraction.

    Light is multiplicative: a cloud halves every value in the picture rather
    than taking a fixed count off it. A floor ninety counts below a circle
    measured at 190 covers one stop and not the second, and reads as generous
    right up until the afternoon it is not.
    """
    return int(trimmed_low_end(values) * COLOR_VALUE_FLOOR_RATIO)


def hue_range(hues):
    """Where the hues sit on the circle, as a start and an end going upwards.

    The end may run past 179: that is what says the color crosses the seam,
    and split_at_seam turns it back into bands the drone can match.
    """
    ordered = sorted(hues)
    arc_start = widest_gap_index(ordered)
    around_the_circle = (
        ordered[arc_start:] + [hue + HUE_CIRCLE for hue in ordered[:arc_start]]
    )
    trim_index = len(around_the_circle) * COLOR_TRIM_PERCENT // 100
    low_end = around_the_circle[trim_index] - COLOR_HUE_MARGIN
    high_end = around_the_circle[len(around_the_circle) - 1 - trim_index] + COLOR_HUE_MARGIN
    return low_end, high_end


def widest_gap_index(ordered_hues):
    """Index of the hue that opens the arc the color occupies."""
    widest_gap = ordered_hues[0] + HUE_CIRCLE - ordered_hues[-1]  # across the seam
    arc_start = 0
    for index in range(1, len(ordered_hues)):
        gap = ordered_hues[index] - ordered_hues[index - 1]
        if gap > widest_gap:
            widest_gap = gap
            arc_start = index
    return arc_start


def split_at_seam(hue_low, hue_high, saturation_range, value_range):
    """The measured range as bands, cut in two where it crosses the hue seam."""
    if hue_high - hue_low >= HUE_MAXIMUM:
        return [band(0, HUE_MAXIMUM, saturation_range, value_range)]

    low_end = hue_low % HUE_CIRCLE
    high_end = hue_high % HUE_CIRCLE
    if low_end <= high_end:
        return [band(low_end, high_end, saturation_range, value_range)]
    return [
        band(low_end, HUE_MAXIMUM, saturation_range, value_range),
        band(0, high_end, saturation_range, value_range),
    ]


def band(hue_low, hue_high, saturation_range, value_range):
    """One band as the drone reads it: a lower HSV triple and an upper one."""
    saturation_low, saturation_high = saturation_range
    value_low, value_high = value_range
    return [
        [hue_low, saturation_low, value_low],
        [hue_high, saturation_high, value_high],
    ]


def band_text(bands):
    """The bands on one line, for the operator to see what was sent."""
    return " + ".join(f"{lower}-{upper}" for lower, upper in bands)
