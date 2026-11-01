"""Replay a detector cache with already measured, exact-ROI sparse refinements.

This is a mechanism diagnostic, not a new whole-video neural execution. A missing
ROI measurement is reported explicitly and is never replaced by a prediction.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
from counting.endpoint_recovery import EndpointRecovery
from counting.tracking import TrackingSession
from counting.geometry import Transform


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_digest(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_probe(source, config, probe, binding, actual_probe_sha256):
    if probe.get("status") != "COMPLETED_SPARSE_NATIVE_DIAGNOSTIC":
        raise ValueError("Sparse native probe did not complete successfully")
    if binding.get("status") != "SOURCE_TENSORS_RECOMPUTED_AND_MATCHED":
        raise ValueError("Require independently recomputed same-source tensor binding")
    checks = ((binding["probe_sha256"], actual_probe_sha256),
              (binding["source_video_sha256"], source["video_sha256"]),
              (binding["source_run_id"], source["run_id"]),
              (binding["source_model_sha256"], source["model_sha256"]),
              (binding["source_config_digest"], config_digest(source["config"])),
              (binding["base_config_file_sha256"], probe["config_sha256"]),
              (binding["input_manifest_sha256"], probe["inputs_manifest_sha256"]),
              (binding["inputs_npz_sha256"], probe["inputs_npz_sha256"]))
    if any(expected != actual for expected, actual in checks):
        raise ValueError("Probe source/model/config/input binding mismatch")
    allowed_changes = {"session_id", "decode_start_frame0", "scope_start_frame0", "end_frame0_exclusive", "endpoint_recovery"}
    if {k: v for k, v in config.items() if k not in allowed_changes} != {k: v for k, v in source["config"].items() if k not in allowed_changes}:
        raise ValueError("Sparse replay cannot change the base detector or geometry")
    verified = {row["frame0"]: row for row in binding["verified_inputs"]}
    if len(verified) != len(binding["verified_inputs"]) or len(probe["rows"]) != len(verified) or probe["new_NPU_model_forwards"] != len(verified):
        raise ValueError("Probe coverage or duplicate frame mismatch")
    measured = {}
    for row in probe["rows"]:
        recorded = verified.get(row["frame0"])
        fields = ("frame0", "source_time_s", "key", "input_tensor_sha256", "transform")
        if recorded is None or any(row[name] != recorded[name] for name in fields):
            raise ValueError("Probe row differs from recomputed source input")
        transform = Transform.create(*source["source_size"], row["transform"]["roi"],
                                     config.get("rotation_clockwise", 0), config["detector"]["size"])
        expected = json.loads(json.dumps(asdict(transform)))
        if row["transform"] != expected:
            raise ValueError("Probe has a mismatched full Transform")
        key = (row["frame0"], tuple(transform.roi))
        if key in measured:
            raise ValueError("Duplicate sparse measurement")
        measured[key] = row
    return measured


def replay(run, config_path, probe_path, binding_path, output):
    source = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    if source["status"] != "COMPLETED_UNSCORED" or source.get("cached_detection_replay_only"):
        raise ValueError("Require an original completed detector cache")
    if output.exists():
        raise FileExistsError(output)
    measured = validate_probe(source, config, probe, binding, sha(probe_path))
    width, height = source["source_size"]
    tracking = TrackingSession(config, width, height, source["effective_nominal_sample_hz"], config["session_id"])
    policy = EndpointRecovery(config, width, height)
    attempts, events, uncertain, observations = [], [], [], 0
    for line in (run / "frames.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("run_id") != source["run_id"]:
            raise ValueError("Base observation belongs to another run")
        frame, stamp = row["frame0"], row["time_s"]
        if frame < config.get("decode_start_frame0", 0) or frame >= config.get("end_frame0_exclusive", float("inf")):
            continue
        detections = np.asarray(row["detections"], np.float32).reshape(-1, 6)
        for proposal in policy.proposals(stamp, detections, tracking.counter.states, tracking.counter.stable_samples):
            support = measured.get((frame, tuple(proposal["roi"])))
            if support is not None and abs(support["source_time_s"] - stamp) > 1e-8:
                raise ValueError("Sparse measurement PTS differs from base observation")
            candidates = support["candidates_original_xyxy_conf_class"] if support else []
            selected = policy.select(proposal, candidates, detections)
            attempts.append({"frame0": frame, "time_s": stamp, **proposal,
                             "prior_exact_ROI_native_measurement_available": support is not None,
                             "accepted_detection": None if selected is None else list(map(float, selected))})
            if selected is not None:
                detections = np.concatenate((detections, np.asarray(selected, np.float32)[None]))
        tracks, new_events, new_uncertain = tracking.update(frame, stamp, detections)
        policy.record(stamp, tracks, tracking.counter.states)
        events += new_events
        uncertain += new_uncertain
        observations += 1
    uncertain += tracking.finish()
    result = {"status": "CACHE_PLUS_PRIOR_SPARSE_NATIVE_MECHANISM_DIAGNOSTIC_NOT_NEW_FULL_BOARD_RUN",
              "counts": tracking.counter.summary(), "base_observations": observations,
              "new_model_forwards": 0, "new_video_decodes": 0,
              "unavailable_refinements": sum(not row["prior_exact_ROI_native_measurement_available"] for row in attempts),
              "attempts": attempts, "events": events, "uncertain": uncertain,
              "config_sha256": sha(config_path), "base_frames_sha256": sha(run / "frames.jsonl"),
              "probe_sha256": sha(probe_path), "binding_sha256": sha(binding_path),
              "software_accuracy_or_independent_validation_claimed": False}
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "config", "probe", "binding", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expect-in", type=int)
    args = parser.parse_args()
    result = replay(args.run, args.config, args.probe, args.binding, args.output)
    print(json.dumps({name: result[name] for name in ("counts", "base_observations", "unavailable_refinements", "new_model_forwards")}))
    if result["unavailable_refinements"] or args.expect_in is not None and result["counts"]["IN"] != args.expect_in:
        raise SystemExit(1)
