"""Generic offline file -> YOLO26 -> short-term tracks -> passage evidence."""
import argparse
import hashlib
import json
import math
import os
import sys
import time
import traceback
import uuid
from collections import deque
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .geometry import Transform
from .tracking import TrackingSession
from .backends import OnnxDetector, O8Detector, decode


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def memory_snapshot():
    result = {}
    try:
        import resource
        result["process_peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:
        result["process_peak_rss_kib"] = None
    path = Path("/proc/meminfo")
    if path.is_file():
        result["system_kib"] = {line.split(":")[0]: int(line.split()[1])
                                for line in path.read_text().splitlines()
                                if line.split(":")[0] in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}}
    return result


def validate_config(config):
    if config.get("axis", "y") not in ("x", "y"):
        raise ValueError("axis must be x or y")
    lo, hi = config.get("perpendicular_roi", [0., 1.])
    if not 0 <= lo < hi <= 1:
        raise ValueError("perpendicular_roi must be two ordered fractions")
    if not 0 <= config.get("confidence", .2) <= 1:
        raise ValueError("confidence must be in [0,1]")
    if config.get("sample_hz") is not None and config["sample_hz"] <= 0:
        raise ValueError("sample_hz must be positive or null for every frame")
    for name in ("decode_start_frame0", "scope_start_frame0"):
        if int(config.get(name, 0)) < 0:
            raise ValueError("Source frame boundaries must be nonnegative")


class Timing:
    def __init__(self):
        self.last = deque(maxlen=10000)
        self.n, self.total, self.maximum = 0, 0., 0.

    def add(self, value):
        self.n += 1
        self.total += value
        self.maximum = max(self.maximum, value)
        self.last.append(value)

    def summary(self):
        return {"count": self.n, "mean_ms": self.total / self.n if self.n else None,
                "maximum_ms": self.maximum if self.n else None,
                "p50_ms": float(np.median(self.last)) if self.last else None,
                "p95_ms": float(np.percentile(self.last, 95)) if self.last else None,
                "percentile_scope": "last 10000 processed frames", "retained_samples": len(self.last)}


def run(video, config, output, detector_factory=None):
    import cv2
    validate_config(config)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cv2.setNumThreads(1)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError(f"Cannot decode video: {video}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Video has no usable nominal frame rate")
    width, height = int(cap.get(3)), int(cap.get(4))
    stride = max(1, round(fps / config["sample_hz"])) if config.get("sample_hz") else 1
    actual_hz = fps / stride
    session_id = str(config.get("session_id") or uuid.uuid4())
    video_id = str(config.get("video_id") or Path(video).stem)
    decode_start = int(config.get("decode_start_frame0", 0))
    scope_start = int(config.get("scope_start_frame0", decode_start))
    end = config.get("end_frame0_exclusive")
    if scope_start < decode_start or end is not None and int(end) <= scope_start:
        raise ValueError("Require decode_start <= scope_start < end")
    if decode_start and not cap.set(cv2.CAP_PROP_POS_FRAMES, decode_start):
        raise ValueError("Decoder cannot seek requested same-video preroll")
    if abs(cap.get(cv2.CAP_PROP_POS_FRAMES) - decode_start) > .1:
        raise ValueError("Decoder did not seek exact requested source frame")
    model = config["detector"]
    detector = None
    summary = {"status": "RUNNING", "session_id": session_id, "video_id": video_id,
               "PID": os.getpid(), "video_path": str(Path(video).resolve()), "video_sha256": sha(video),
               "config": config, "nominal_fps": fps, "source_size": [width, height],
               "source_stride": stride, "effective_nominal_sample_hz": actual_hz,
               "decoded_frames": 0, "processed_frames": 0, "wall_clock_skipped_frames": 0,
               "time_source": "opencv source PTS", "model_forwards": 0,
               "counts": {"IN": 0, "OUT": 0, "NET": 0}, "uncertain_records": 0,
               "accuracy_verified": False,
               "software_fixture_only": detector_factory is not None,
               "runtime_versions": {"python": sys.version, "numpy": np.__version__, "opencv": cv2.__version__},
               "startup_scope": "elapsed includes detector initialization, processing and close; excludes initial open, seek and input hashing",
               "memory_before_model": memory_snapshot(),
               "clock_contract": "fixed source-frame sampling; PTS evidence; large PTS gap censors and resets tracks",
               "latency_boundary": "decode selected source frame through event/log update; offline, no realtime deadline"}
    timings = {name: Timing() for name in ("decode", "preprocess", "inference", "tracking", "frame")}
    tracking = TrackingSession(config, width, height, actual_hz, session_id)
    counter_snapshot = None
    events_file = (output / "events.jsonl").open("w", encoding="utf-8", buffering=1)
    frames_file = (output / "frames.jsonl").open("w", encoding="utf-8", buffering=1)
    uncertain_file = (output / "uncertain.jsonl").open("w", encoding="utf-8", buffering=1)
    started = time.monotonic()
    def write(file, value):
        file.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
    try:
        if detector_factory is not None:
            detector = detector_factory(model)
        elif model["backend"] == "onnx":
            detector = OnnxDetector(model["model"], model.get("threads", 1))
            summary["model_sha256"] = sha(model["model"])
        elif model["backend"] == "o8":
            detector = O8Detector(model["root"], model["program"], model["plan"], model["size"])
            summary["model_sha256"] = sha(Path(model["program"]) / "graph.bin")
            summary["resident_plan_sha256"] = sha(model["plan"])
            summary["device_initialization"] = detector.initialization
            root = Path(model["root"])
            summary["runtime_asset_sha256"] = {str(path.relative_to(root)): sha(path) for path in (
                root / "native_sources/native_queue.so", root / "hardware/accepted/firmware_manifest.json",
                root / "hardware/accepted/optimization_8_resident.bit")}
        else:
            raise ValueError("detector.backend must be onnx or o8")
        transform = Transform.create(width, height, config.get("detection_roi_xyxy"),
                                     config.get("rotation_clockwise", 0), detector.size)
        save(output / "transform.json", asdict(transform))
        frame, previous_pts = decode_start, None
        while end is None or frame < int(end):
            tick = time.monotonic()
            ok, image = cap.read()
            decode_done = time.monotonic()
            if not ok:
                if end is not None and frame < int(end):
                    raise ValueError(f"Source ended at frame {frame} before requested end {end}")
                break
            summary["decoded_frames"] += 1
            pts = float(cap.get(cv2.CAP_PROP_POS_MSEC)) / 1000
            if not math.isfinite(pts) or previous_pts is not None and pts <= previous_pts:
                raise ValueError("Decoder did not provide strictly increasing source PTS; cannot fabricate source time")
            previous_pts = pts
            if frame % stride:
                frame += 1
                continue
            tensor = transform.preprocess(image)
            prepared = time.monotonic()
            raw = detector.infer(tensor)
            inferred = time.monotonic()
            summary["model_forwards"] += 1
            detections = decode(raw, transform, config.get("confidence", .2), config.get("cow_class_ids", [0]))
            tracks, events, uncertain = tracking.update(frame, pts, detections)
            tracked = time.monotonic()
            for event in events:
                event["video_id"] = video_id
                event["in_statistical_scope"] = frame >= scope_start
                if frame >= scope_start:
                    summary["counts"][event["kind"]] += 1
                    write(events_file, event)
            for row in uncertain:
                row["video_id"] = video_id
                write(uncertain_file, row)
                summary["uncertain_records"] += 1
            summary["counts"]["NET"] = summary["counts"]["IN"] - summary["counts"]["OUT"]
            write(frames_file, {"frame0": frame, "time_s": pts, "in_statistical_scope": frame >= scope_start,
                                "detections": detections.astype(float).tolist(), "tracks": tracks,
                                "counts": summary["counts"].copy(), "tracker_epoch": tracking.epoch})
            summary["processed_frames"] += 1
            summary["last_source_frame0"], summary["last_source_time_s"] = frame, pts
            for name, value in (("decode", decode_done - tick), ("preprocess", prepared - decode_done),
                                ("inference", inferred - prepared), ("tracking", tracked - inferred),
                                ("frame", time.monotonic() - tick)):
                timings[name].add(value * 1000)
            if summary["processed_frames"] % 25 == 0:
                save(output / "progress.json", summary)
            frame += 1
        for row in tracking.finish():
            row["video_id"] = video_id
            write(uncertain_file, row)
            summary["uncertain_records"] += 1
        counter_snapshot = tracking.counter.summary()
        if not summary["processed_frames"]:
            raise ValueError("No selected video frames processed")
        summary["status"] = "COMPLETED_UNSCORED"
    except BaseException as error:
        summary.update(status="FAILED", error=repr(error), traceback=traceback.format_exc())
        raise
    finally:
        cap.release()
        for file in (events_file, frames_file, uncertain_file):
            file.close()
        if detector is not None:
            try:
                detector.close()
            except Exception as error:
                summary.update(status="CLOSE_FAILED", close_error=repr(error))
        summary["counts"]["NET"] = summary["counts"]["IN"] - summary["counts"]["OUT"]
        summary["elapsed_s"] = time.monotonic() - started
        summary["timings"] = {name: timer.summary() for name, timer in timings.items()}
        summary["counter_after_finish"] = counter_snapshot
        summary["maximum_state_count"] = tracking.maximum_state_count
        summary["state_eviction_ttl_s"] = tracking.counter_config["ttl_s"]
        summary["memory_after_close"] = memory_snapshot()
        save(output / "summary.json", summary)
    if summary["status"] != "COMPLETED_UNSCORED":
        raise RuntimeError(summary["status"])
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.video, json.loads(args.config.read_text(encoding="utf-8-sig")), args.output)
    print(json.dumps({key: result[key] for key in ("status", "counts", "processed_frames", "elapsed_s")}))
