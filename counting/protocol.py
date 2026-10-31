"""Canonical original-coordinate counting gate, shared with reference intake."""
import math


def canonical_gate(value):
    axis = value["axis"]
    lo, hi = value["perpendicular_roi"]
    lower, upper = value["lower"], value["upper"]
    if axis not in ("x", "y") or not all(math.isfinite(x) for x in (lo, hi, lower, upper)):
        raise ValueError("Invalid counting gate")
    if not (0 <= lo < hi <= 1 and 0 <= lower < upper <= 1):
        raise ValueError("Invalid counting gate boundaries")
    return {"axis": axis, "perpendicular_roi": [lo, hi], "lower": lower, "upper": upper}


def gate_from_config(config):
    counter = config.get("counter", {})
    return canonical_gate({"axis": config.get("axis", "y"),
                           "perpendicular_roi": config.get("perpendicular_roi", [0., 1.]),
                           "lower": counter.get("lower", .4), "upper": counter.get("upper", .6)})
