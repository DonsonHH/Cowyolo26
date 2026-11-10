"""Observe the unchanged frozen tracker on recorded detections, without parameter search.

The cost and solver wrappers delegate to the original functions exactly once and
are restored on exit. Recorded tracks must match the actual board trace. This is
post-hoc error analysis, never a second held-out accuracy evaluation.
"""
import argparse
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path
from types import MethodType

import numpy as np

from counting.tracking import TrackingSession
from maintenance.counting_r1.tracker import matching


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def track_snapshot(track, time_s):
    last = getattr(track, "source_last_observed_s", None)
    return {"id": int(track.track_id), "state": int(track.state),
            "activated": bool(track.is_activated), "predicted_xyxy": track.xyxy.astype(float).tolist(),
            "last_observed_s": last, "age_s": None if last is None else time_s - last,
            "score": float(track.score)}


def audit(run_dir):
    run_dir = Path(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    if summary["status"] != "COMPLETED_UNSCORED" or summary.get("cached_detection_replay_only"):
        raise ValueError("An original completed detector run is required")
    config = summary["config"]
    width, height = summary["source_size"]
    session = TrackingSession(config, width, height, summary["effective_nominal_sample_hz"], summary["session_id"])
    original_cost = session.tracker.get_dists
    original_solver = matching.linear_assignment
    trace = []
    context = {}

    def costs(tracker, tracks, detections):
        matrix = original_cost(tracks, detections)
        context["cost_calls"].append({
            "stage": inspect.currentframe().f_back.f_code.co_name,
            "tracks": [track_snapshot(t, context["time_s"]) for t in tracks],
            "detections": [{"xyxy": d.xyxy.astype(float).tolist(), "score": float(d.score),
                            "index_in_gated_input": int(d.idx)} for d in detections],
            "cost_matrix": matrix.astype(float).tolist(),
        })
        return matrix

    def solve(matrix, thresh, use_lap=True):
        result = original_solver(matrix, thresh, use_lap)
        context["solver_calls"].append({
            "stage": inspect.currentframe().f_back.f_code.co_name,
            "threshold": float(thresh), "matrix_shape": list(matrix.shape),
            "matches": np.asarray(result[0], dtype=int).reshape(-1, 2).tolist(),
            "unmatched_tracks": np.asarray(result[1], dtype=int).tolist(),
            "unmatched_detections": np.asarray(result[2], dtype=int).tolist(),
        })
        return result

    processed, maximum_difference = 0, 0.
    observed_counts = {"IN": 0, "OUT": 0}
    session.tracker.get_dists = MethodType(costs, session.tracker)
    matching.linear_assignment = solve
    try:
        with (run_dir / "frames.jsonl").open(encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                context = {"source_frame0": row["frame0"], "time_s": row["time_s"],
                           "cost_calls": [], "solver_calls": []}
                tracks, events, uncertain = session.update(row["frame0"], row["time_s"], row["detections"])
                before = {t["track_id"]: t for t in row["tracks"]}
                after = {t["track_id"]: t for t in tracks}
                if before.keys() != after.keys():
                    raise AssertionError(f"Instrumentation changed track IDs at {row['frame0']}")
                for tid in before:
                    difference = float(np.max(np.abs(np.asarray(before[tid]["xyxy"]) - after[tid]["xyxy"])))
                    maximum_difference = max(maximum_difference, difference)
                    if difference > .002:
                        raise AssertionError("Instrumentation changed a recorded track box")
                for event in events:
                    if row["in_statistical_scope"]:
                        observed_counts[event["kind"]] += 1
                context.update(raw_candidates=row["detections"], actual_output_tracks=tracks,
                               events=events, uncertain=uncertain,
                               counter_states={tid: asdict(state) for tid, state in session.counter.states.items()})
                if row["detections"]:
                    trace.append(context)
                processed += 1
        terminal_diagnostics = session.finish()
    finally:
        matching.linear_assignment = original_solver
        session.tracker.get_dists = original_cost
    if processed != summary["processed_frames"] or any(observed_counts[k] != summary["counts"][k] for k in observed_counts):
        raise AssertionError("Audit does not reproduce the complete recorded detector run")
    return {"debug_tag": "ASSOCIATION_AUDIT_20261101", "purpose": "POST_HOC_FROZEN_FAILURE_ANALYSIS",
            "source_summary_sha256": sha(run_dir / "summary.json"),
            "source_frames_sha256": sha(run_dir / "frames.jsonl"),
            "source_video_sha256": summary["video_sha256"], "source_run_id": summary["run_id"],
            "unchanged_config": config, "parameter_search_or_overrides": False,
            "new_model_forwards": 0, "new_video_decodes": 0,
            "replayed_observations": processed, "candidate_observations": len(trace),
            "count_result": observed_counts, "actual_board_track_ids_match": True,
            "maximum_board_box_difference_px": maximum_difference,
            "original_solver_restored": matching.linear_assignment is original_solver,
            "counterfactual_matching_or_counting_performed": False,
            "terminal_diagnostics": terminal_diagnostics, "candidate_observation_trace": trace}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = audit(args.run)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("replayed_observations", "candidate_observations", "count_result",
                      "actual_board_track_ids_match", "maximum_board_box_difference_px", "new_model_forwards")}))
