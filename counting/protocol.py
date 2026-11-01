"""Canonical original-coordinate counting gate, shared with reference intake."""
import math
from .channel import ChannelPolygon


def canonical_gate(value):
    axis = value["axis"]
    lo, hi = value["perpendicular_roi"]
    lower, upper = value["lower"], value["upper"]
    if axis not in ("x", "y") or not all(math.isfinite(x) for x in (lo, hi, lower, upper)):
        raise ValueError("Invalid counting gate")
    if not (0 <= lo < hi <= 1 and 0 <= lower < upper <= 1):
        raise ValueError("Invalid counting gate boundaries")
    gate = {"axis": axis, "perpendicular_roi": [lo, hi], "lower": lower, "upper": upper}
    if value.get("channel_polygon") is not None:
        if lo != 0 or hi != 1:
            raise ValueError("channel_polygon defines the full region; perpendicular_roi must be [0, 1]")
        polygon = ChannelPolygon(value["channel_polygon"])
        if not polygon.gate_segments(axis, lower) or not polygon.gate_segments(axis, upper):
            raise ValueError("Both counting gates must cross the channel_polygon interior")
        gate["channel_polygon"] = polygon.as_list()
    return gate


def gate_from_config(config):
    counter = config.get("counter", {})
    return canonical_gate({"axis": config.get("axis", "y"),
                           "perpendicular_roi": config.get("perpendicular_roi", [0., 1.]),
                           "lower": counter.get("lower", .4), "upper": counter.get("upper", .6),
                           "channel_polygon": config.get("channel_polygon")})
