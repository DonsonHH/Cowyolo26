"""Score a completed offline run against a reviewed, hash-bound human record."""
import argparse
import json
import hashlib
import math
from pathlib import Path
from maintenance.counting_r1.event_metrics_v2 import evaluate_events
from .protocol import canonical_gate, gate_from_config


def _frame_index(value, start, end):
    if isinstance(value, bool) or not isinstance(value, int) or not start <= value <= end:
        raise ValueError('Source frame must be an integer inside the reviewed interval')
    return value


def _validate_times(row, completion, entry, source_time, frame_slack):
    for key in ('entry_time_s', 'time_s'):
        value = row.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Entry and completion times must be finite source timestamps')
    if row['entry_time_s'] >= row['time_s'] or entry >= completion:
        raise ValueError('Entry must precede completion in source time and source frame')
    for key, frame in (('entry_time_s', entry), ('time_s', completion)):
        if abs(row[key] - source_time(frame)) > frame_slack(frame) + 1e-8:
            raise ValueError('Event time is not bound to its declared source frame')


def evaluate_run(run_folder, reference_file, normalize_legacy_scope=False):
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
    if "review_gate" not in reference or canonical_gate(reference["review_gate"]) != gate_from_config(run["config"]):
        raise ValueError("Reference counting gate differs from the run configuration")
    start = _frame_index(start, 0, end)
    end = _frame_index(end, start, end)
    source_times = reference.get('source_frame_times_s')
    if source_times is not None:
        if (not isinstance(source_times, list) or len(source_times) <= end
                or any(isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) for t in source_times)
                or any(b <= a for a, b in zip(source_times, source_times[1:]))):
            raise ValueError('A verified increasing source-frame time index is required')
        source_time = lambda frame: source_times[frame]
        def frame_slack(frame):
            neighbors = [abs(source_times[frame]-source_times[j]) for j in (frame-1, frame+1)
                         if 0 <= j < len(source_times)]
            return max(neighbors, default=0.)
    elif run.get('time_source') == 'verified relative CFR source PTS':
        fps = run.get('nominal_fps')
        if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not math.isfinite(fps) or fps <= 0:
            raise ValueError('CFR source frames require a finite positive nominal_fps')
        source_time = lambda frame: frame / fps
        frame_slack = lambda frame: 1. / fps
    else:
        raise ValueError('Timed references require a source-frame time index or verified CFR timing')
    for row in events:
        keys = row['key_source_frames0']
        if not isinstance(keys, list) or not keys:
            raise ValueError('A list of independent source keyframes is required')
        for keyframe in keys:
            _frame_index(keyframe, start, end)
        completion = _frame_index(row['completion_source_frame0'], start, end)
        entry = _frame_index(row.get('entry_source_frame0', min(keys)), start, end)
        if completion not in keys:
            raise ValueError('Completion frame must occur in the independent keyframe record')
        _validate_times(row, completion, entry, source_time, frame_slack)
    prediction = [json.loads(line) for line in (run_folder / "events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    normalization=[]
    if not run.get('run_id'):
        raise ValueError('Run summary requires a bound run_id')
    for row in prediction:
        if row.get('run_id')!=run['run_id']:
            raise ValueError('Prediction run_id differs from summary or is missing')
        added={}
        for key in ('video_id','session_id'):
            if key not in row:
                if not normalize_legacy_scope:
                    raise ValueError('Prediction scope is missing '+key+'; explicit legacy normalization is required')
                row[key]=run[key]
                added[key]=run[key]
            elif row[key]!=run[key]:
                raise ValueError('Prediction '+key+' conflicts with summary scope')
        if added:normalization.append({'event_id':row.get('event_id'),'added_fields':added})
        completion = _frame_index(row.get('frame0'), start, end)
        entry = _frame_index(row.get('entry_frame0'), start, end)
        _validate_times(row, completion, entry, source_time, frame_slack)
    if any(not isinstance(row.get('event_id'), str) or not row['event_id'].strip()
           for row in events + prediction):
        raise ValueError('File-based event evaluation requires explicit nonempty event identifiers')
    result = evaluate_events(events, prediction, float(reference.get("matching_tolerance_s", 2.)),
                             reference.get("physical_correspondence"))
    def digest(path):
        value=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
        return value.hexdigest()
    return {"status": "SCORED_AGAINST_SUPPLIED_HUMAN_REFERENCE", "reference_file": str(reference_file.resolve()),
            'scope_adapter_version':'explicit-legacy-scope-20261109',
            'normalization_used':bool(normalization),'prediction_scope_normalizations':normalization,
            'input_file_sha256':{'summary.json':digest(run_folder/'summary.json'),
                                 'events.jsonl':digest(run_folder/'events.jsonl'),'reference':digest(reference_file)},
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
    parser.add_argument('--normalize-legacy-scope',action='store_true',
                        help='Explicitly add absent video/session fields from a verified summary; never rewrite raw logs')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = evaluate_run(args.run, args.reference, args.normalize_legacy_scope)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"]))
