import math

import cairo


def circle_region(size):
    radius = size / 2
    region = cairo.Region()
    for row in range(size):
        start, width = _row_span(radius, row + 0.5 - radius)
        if width > 0:
            region.union(cairo.RectangleInt(start, row, width, 1))
    return region


def _row_span(radius, distance_from_center):
    half_width = math.sqrt(max(radius**2 - distance_from_center**2, 0))
    start = round(radius - half_width)
    return start, round(radius + half_width) - start
