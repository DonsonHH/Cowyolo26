"""Replay actual decoded detections through tracking/counting; no model or video decode."""
import argparse
import copy
import hashlib
import json
import time
import uuid
from pathlib import Path

import numpy as np

from counting.tracking import TrackingSession


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def replay(run, output, stable_samples=None, expected_in=None, postprocess_profile=None):
    run, output = Path(run), Path(output)
    source = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    if source["status"] != "COMPLETED_UNSCORED" or source.get("cached_detection_replay_only"):
        raise ValueError("A completed original detector run is required")
    config = copy.deepcopy(source["config"])
    if postprocess_profile is not None:
        if stable_samples is not None:
            raise ValueError("Choose either a stability override or a postprocess profile")
        profile = json.loads(Path(postprocess_profile).read_text(encoding="utf-8"))
        allowed = {"axis", "perpendicular_roi", "in_direction", "counter", "tracker",
                   "lost_seconds", "track_only_in_channel", "channel_polygon"}
        for name, value in profile.items():
            if name in allowed:
                config[name] = ({**config.get(name, {}), **value}
                                if name in ("counter", "tracker") else copy.deepcopy(value))
            elif name in config and value != config[name]:
                raise ValueError(f"Cache replay cannot change detector/input setting: {name}")
    enforce_track_parity = postprocess_profile is None
    if stable_samples is not None:
        if stable_samples < 1:
            raise ValueError("stable_samples must be positive")
        config.setdefault("counter", {})["stable_samples"] = stable_samples
    output.mkdir(parents=True, exist_ok=False)
    width, height = source["source_size"]
    session = TrackingSession(config, width, height, source["effective_nominal_sample_hz"], source["session_id"])
    run_id = str(uuid.uuid4())
    counts, processed, uncertain_count = {"IN": 0, "OUT": 0, "NET": 0}, 0, 0
    maximum_box_difference, changed_track_rows = 0., 0
    started = time.monotonic()
    summary = {"status": "RUNNING", "execution_mode": "DETECTION_CACHE_REPLAY",
               "cached_detection_replay_only": True, "new_video_decodes": 0, "model_forwards": 0,
               "software_fixture_only": source.get("software_fixture_only", False),
               "accuracy_verified": False, "run_id": run_id, "derived_from_run_id": source["run_id"],
               "session_id": source["session_id"], "video_id": source["video_id"],
               "video_sha256": source["video_sha256"], "source_size": source["source_size"],
               "nominal_fps": source["nominal_fps"],
               "effective_nominal_sample_hz": source["effective_nominal_sample_hz"],
               "source_model_sha256": source["model_sha256"], "config": config,
               "input_observations_sha256": sha(run / "frames.jsonl"),
               "source_summary_sha256": sha(run / "summary.json"),
               "postprocess_profile_sha256": sha(Path(postprocess_profile)) if postprocess_profile else None,
               "exact_source_track_parity_enforced": enforce_track_parity}

    def write(file, value):
        file.write(json.dumps(value, allow_nan=False) + "\n")

    try:
        with (run / "frames.jsonl").open(encoding="utf-8") as observations, \
                (output / "frames.jsonl").open("w", encoding="utf-8") as frame_file, \
                (output / "events.jsonl").open("w", encoding="utf-8") as event_file, \
                (output / "uncertain.jsonl").open("w", encoding="utf-8") as uncertain_file:
            for line in observations:
                row = json.loads(line)
                tracks, events, uncertain = session.update(row["frame0"], row["time_s"], row["detections"])
                original = {track["track_id"]: track for track in row["tracks"]}
                current = {track["track_id"]: track for track in tracks}
                row_matches = original.keys() == current.keys()
                if not row_matches and enforce_track_parity:
                    raise AssertionError(f"Track identity mismatch at source frame {row['frame0']}")
                for tid in current.keys() & original.keys():
                    track = current[tid]
                    difference = float(np.max(np.abs(np.asarray(track["xyxy"]) - original[tid]["xyxy"])))
                    if enforce_track_parity:
                        maximum_box_difference = max(maximum_box_difference, difference)
                    if difference > .002:
                        row_matches = False
                        if enforce_track_parity:
                            raise AssertionError(f"Track box mismatch at source frame {row['frame0']}")
                changed_track_rows += int(not row_matches)
                in_scope = row["frame0"] >= config.get("scope_start_frame0", 0)
                for event in events:
                    event.update(run_id=run_id, video_id=source["video_id"], in_statistical_scope=in_scope)
                    if in_scope:
                        counts[event["kind"]] += 1
                        write(event_file, event)
                for record in uncertain:
                    record.update(run_id=run_id, video_id=source["video_id"])
                    write(uncertain_file, record)
                    uncertain_count += 1
                counts["NET"] = counts["IN"] - counts["OUT"]
                write(frame_file, {**row, "run_id": run_id, "tracks": tracks, "counts": counts.copy()})
                processed += 1
            for record in session.finish():
                record.update(run_id=run_id, video_id=source["video_id"])
                write(uncertain_file, record)
                uncertain_count += 1
        if processed != source["processed_frames"]:
            raise AssertionError("Observation cache does not cover the complete source run")
        summary["status"] = "COMPLETED_UNSCORED"
    except BaseException as error:
        summary.update(status="FAILED", error=repr(error))
        raise
    finally:
        summary.update(counts=counts, processed_frames=processed, uncertain_records=uncertain_count,
                       elapsed_s=time.monotonic() - started,
                       maximum_track_box_difference_px=maximum_box_difference if enforce_track_parity else None,
                       changed_track_rows_from_source=changed_track_rows,
                       track_identity_rows_match_source=(changed_track_rows == 0 and summary["status"] == "COMPLETED_UNSCORED"))
        if expected_in is not None:
            summary["count_check"] = {"expected_IN": expected_in, "passed": counts["IN"] == expected_in}
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--stable-samples", type=int)
    group.add_argument("--postprocess-profile", type=Path)
    parser.add_argument("--expect-in", type=int)
    args = parser.parse_args()
    result = replay(args.run, args.output, args.stable_samples, args.expect_in, args.postprocess_profile)
    print(json.dumps({key: result[key] for key in ("status", "counts", "processed_frames", "model_forwards")}))
    if result.get("count_check", {}).get("passed") is False:
        raise SystemExit(1)
