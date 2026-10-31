"""Score a completed offline run against a reviewed, hash-bound human record."""
import argparse
import json
from pathlib import Path
from maintenance.counting_r1.event_metrics_v2 import evaluate_events


def evaluate_run(run_folder, reference_file):
    run_folder, reference_file = Path(run_folder), Path(reference_file)
    run = json.loads((run_folder / "summary.json").read_text(encoding="utf-8"))
    reference = json.loads(reference_file.read_text(encoding="utf-8-sig"))
    if run["status"] != "COMPLETED_UNSCORED":
        raise ValueError("Only completed runs can be evaluated")
    if reference.get("review_status") != "reviewed" or not reference.get("reviewer") or not reference.get("reviewed_at"):
        raise ValueError("Independent human review is still pending")
    if reference["source_video_sha256"] != run["video_sha256"]:
        raise ValueError("Reference and run source hashes differ")
    interval = reference["reviewed_interval"]
    start, end = interval["start_frame0"], interval["end_frame0"]
    if run["config"].get("scope_start_frame0", 0) != start or run["config"].get("end_frame0_exclusive") != end + 1:
        raise ValueError("Reference and run statistical windows differ")
    events = reference["events"]
    for row in events:
        if row.get("status") != "complete" or row.get("review_status") != "reviewed":
            raise ValueError("Only reviewed complete events belong in events; uncertainty is separate")
        if not row.get("key_source_frames0") or not start <= row["completion_source_frame0"] <= end:
            raise ValueError("Missing source keyframes or event outside reviewed interval")
        if not row.get("passage_position_or_local_trajectory"):
            raise ValueError("Each reference event requires an independent passage position or local trajectory")
        if row.get("video_id") != run["video_id"] or row.get("session_id") != run["session_id"]:
            raise ValueError("Reference and run video/session identifiers differ")
        if row.get("entry_time_s") is None or row["entry_time_s"] >= row["time_s"]:
            raise ValueError("Complete passages require entry before completion")
    prediction = [json.loads(line) for line in (run_folder / "events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    result = evaluate_events(events, prediction, float(reference.get("matching_tolerance_s", 2.)),
                             reference.get("physical_correspondence"))
    return {"status": "SCORED_AGAINST_SUPPLIED_HUMAN_REFERENCE", "reference_file": str(reference_file.resolve()),
            "reviewer": reference["reviewer"], "reviewed_at": reference["reviewed_at"],
            "source_sha256": run["video_sha256"], "run_folder": str(run_folder.resolve()),
            "reference_uncertain_or_truncated": len(reference.get("uncertain_or_truncated_records", [])),
            "prediction_uncertain_or_truncated": run["uncertain_records"],
            "single_video_demonstrates_generalization": False, "metrics": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = evaluate_run(args.run, args.reference)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"]))
