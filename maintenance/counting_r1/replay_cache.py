"""One cached development stream, one baseline and one second-stage-IoU pass.

Consumes existing detection JSON only. No video decode, neural inference or board
access. Historical prehistory is replayed from this same video, not a state blob.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from .tracker import SecondStageIoUTracker, verify_method_scope
from frame_pipeline import FramePipeline


def load(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(rows, spec, protocol, fixed):
    pipeline = FramePipeline(spec, protocol["tracker_config"], protocol["counter_kwargs"])
    if fixed:
        from types import SimpleNamespace
        pipeline.tracker = SecondStageIoUTracker(SimpleNamespace(**protocol["tracker_config"]))
    out = {"observations": [], "post_tracker": [], "confirmed_only_events": [], "handoff_events": []}
    for row in rows:
        result = pipeline.update(row["frame0"], row["predictions"])
        out["observations"].append(result["observation"])
        for name in ("post_tracker", "confirmed_only_events", "handoff_events"):
            out[name].extend(result[name])
    return out


def event_signature(events):
    return [(row["frame0"], row["time_s"], row["direction"]) for row in events]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--reference-trace", type=Path, required=True)
    parser.add_argument("--scene", default="original")
    parser.add_argument("--stride", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.stride < 1:
        raise ValueError("Positive source stride required")
    protocol = load(args.protocol)
    spec = next(row for row in protocol["videos"] if row["name"] == args.scene)
    rows = [row for row in load(args.cache) if row["frame0"] % args.stride == 0]
    if not rows or any(b["frame0"] <= a["frame0"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Cache must have a nonempty, strictly increasing source timeline")
    original = load(args.reference_trace)
    baseline = run(rows, spec, protocol, False)
    candidate = run(rows, spec, protocol, True)
    # Frozen board/CPU AABB comparison tolerance, not a newly fitted threshold.
    numeric_tolerance = 0.002
    original_post, baseline_post = original["post_tracker"], baseline["post_tracker"]
    same_post_structure = (len(original_post) == len(baseline_post)
                           and all((a["frame0"], a["track_id"]) == (b["frame0"], b["track_id"])
                                   for a, b in zip(original_post, baseline_post)))
    max_box_difference = (max((max(abs(x - y) for x, y in zip(a["xyxy"], b["xyxy"]))
                               for a, b in zip(original_post, baseline_post)), default=0.0)
                          if same_post_structure else None)
    baseline_verified = (same_post_structure and max_box_difference <= numeric_tolerance
                         and baseline["handoff_events"] == original["handoff_events"]
                         and baseline["confirmed_only_events"] == original["confirmed_only_events"])
    start, end = spec["scope_start_frame0"], spec["scope_end_exclusive"]
    def scoped(events):
        return [row for row in events if start <= row["frame0"] < end]
    base_events = scoped(baseline["handoff_events"])
    candidate_events = scoped(candidate["handoff_events"])
    base_by_frame, candidate_by_frame = {}, {}
    for output, target in ((baseline, base_by_frame), (candidate, candidate_by_frame)):
        for row in output["post_tracker"]:
            target.setdefault(row["frame0"], []).append(row)
    changed_frames = sorted(frame for frame in base_by_frame.keys() | candidate_by_frame.keys()
                            if base_by_frame.get(frame, []) != candidate_by_frame.get(frame, []))
    result = {
        "status": "PASS_BASELINE_REPRODUCED" if baseline_verified else "BASELINE_MISMATCH_REVIEW_REQUIRED",
        "scope": "one existing original-video detection cache; CPU tracker replay only",
        "input_files": [{"path": str(path.resolve()), "sha256": sha(path)}
                        for path in (args.cache, args.protocol, args.reference_trace)],
        "source_ticks": len(rows), "source_first_frame0": rows[0]["frame0"],
        "source_last_frame0": rows[-1]["frame0"], "source_stride": args.stride,
        "scope_start_frame0": start, "scope_end_exclusive": end,
        "same_video_prehistory_ticks": sum(row["frame0"] < start for row in rows),
        "tracker_config": protocol["tracker_config"], "counter_kwargs": protocol["counter_kwargs"],
        "method_scope": verify_method_scope(),
        "baseline_reference": {"event_dicts_identical": baseline["handoff_events"] == original["handoff_events"],
                               "confirmed_only_event_dicts_identical": baseline["confirmed_only_events"] == original["confirmed_only_events"],
                               "frame_and_ID_rows_identical": same_post_structure,
                               "max_box_difference_px": max_box_difference, "box_tolerance_px": numeric_tolerance},
        "baseline": {"handoff_events": base_events, "post_tracker_rows": len(baseline["post_tracker"]),
                     "confirmed_only_events": scoped(baseline["confirmed_only_events"])},
        "candidate": {"handoff_events": candidate_events, "post_tracker_rows": len(candidate["post_tracker"]),
                      "confirmed_only_events": scoped(candidate["confirmed_only_events"])},
        "same_event_times_and_directions_without_ids": event_signature(base_events) == event_signature(candidate_events),
        "same_full_event_dicts_with_ids": base_events == candidate_events,
        "changed_post_tracker_frame_count": len(changed_frames),
        "changed_post_tracker_frames0": changed_frames,
        "user_confirmed_total": 12, "human_event_reference_received": False,
        "event_precision_recall_available": False, "accuracy_improvement_proven": False,
        "new_model_forwards": 0, "board_connections": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "source_ticks", "same_event_times_and_directions_without_ids",
                                                    "changed_post_tracker_frame_count", "same_full_event_dicts_with_ids")}))
    print(json.dumps({"baseline_events": len(base_events), "candidate_events": len(candidate_events)}))
    raise SystemExit(0 if baseline_verified else 1)


if __name__ == "__main__":
    main()
