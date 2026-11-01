"""A simple original-coordinate channel polygon and its counting cross-sections."""
import math
from numbers import Real

EPSILON = 1e-10


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a, b, p):
    return (abs(cross(a, b, p)) <= EPSILON
            and min(a[0], b[0]) - EPSILON <= p[0] <= max(a[0], b[0]) + EPSILON
            and min(a[1], b[1]) - EPSILON <= p[1] <= max(a[1], b[1]) + EPSILON)


def intersects(a, b, c, d):
    ab_c, ab_d, cd_a, cd_b = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    return ((ab_c * ab_d < 0 and cd_a * cd_b < 0)
            or on_segment(a, b, c) or on_segment(a, b, d)
            or on_segment(c, d, a) or on_segment(c, d, b))


class ChannelPolygon:
    def __init__(self, values):
        if not isinstance(values, (list, tuple)) or not 3 <= len(values) <= 64:
            raise ValueError("channel_polygon requires 3 to 64 normalized vertices")
        points = []
        for point in values:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError("channel_polygon vertices must be [x, y]")
            if any(isinstance(v, bool) or not isinstance(v, Real) or not math.isfinite(v) or not 0 <= v <= 1 for v in point):
                raise ValueError("channel_polygon coordinates must be finite numbers in [0, 1]")
            points.append(tuple(map(float, point)))
        if points[-1] == points[0]:
            points.pop()
        if len(points) < 3 or len(set(points)) != len(points):
            raise ValueError("channel_polygon has repeated or insufficient vertices")
        size = len(points)
        area = sum(points[i][0] * points[(i + 1) % size][1] - points[(i + 1) % size][0] * points[i][1] for i in range(size))
        if abs(area) <= EPSILON:
            raise ValueError("channel_polygon must have nonzero area")
        for i in range(size):
            a, b = points[i], points[(i + 1) % size]
            if math.dist(a, b) <= EPSILON:
                raise ValueError("channel_polygon has a zero length edge")
            for j in range(i + 1, size):
                if j == (i + 1) % size or (j + 1) % size == i:
                    continue
                if intersects(a, b, points[j], points[(j + 1) % size]):
                    raise ValueError("channel_polygon must be simple, without self intersections")
        if area < 0:
            points.reverse()
        start = min(range(size), key=points.__getitem__)
        self.points = tuple(points[start:] + points[:start])

    def as_list(self):
        return [list(point) for point in self.points]

    def contains(self, x, y):
        if not math.isfinite(x) or not math.isfinite(y):
            return False
        inside = False
        for a, b in zip(self.points, self.points[1:] + self.points[:1]):
            if on_segment(a, b, (x, y)):
                return False
            if (a[1] > y) != (b[1] > y):
                crossing_x = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                if x < crossing_x:
                    inside = not inside
        return inside

    def gate_segments(self, axis, level):
        if axis not in ("x", "y") or not math.isfinite(level) or not 0 <= level <= 1:
            raise ValueError("Invalid polygon counting cross-section")
        along, across = (1, 0) if axis == "y" else (0, 1)
        intersections = []
        for a, b in zip(self.points, self.points[1:] + self.points[:1]):
            # Collinear boundary endpoints also split the line. Without these,
            # a notch boundary can be drawn through or both valid sides lost.
            if abs(a[along] - level) <= EPSILON:
                intersections.append(a[across])
            if abs(b[along] - level) <= EPSILON:
                intersections.append(b[across])
            if (a[along] - level) * (b[along] - level) < 0:
                intersections.append(a[across] + (level - a[along]) * (b[across] - a[across]) / (b[along] - a[along]))
        intersections.sort()
        breaks = []
        for value in intersections:
            if not breaks or value - breaks[-1] > EPSILON:
                breaks.append(value)
        result = []
        for lower, upper in zip(breaks, breaks[1:]):
            midpoint = ((lower + upper) / 2, level) if axis == "y" else (level, (lower + upper) / 2)
            if upper - lower > EPSILON and self.contains(*midpoint):
                result.append(((lower, level), (upper, level)) if axis == "y" else ((level, lower), (level, upper)))
        return result
