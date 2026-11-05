"""Wall-paced capture with one latest frame, real detector and passage counting."""
import argparse
from dataclasses import asdict
from collections import deque
import json
import math
from pathlib import Path
import threading
import time
import traceback
import uuid

import numpy as np

from .backends import O8Detector, OnnxDetector, decode
from .endpoint_recovery import EndpointRecovery
from .geometry import Transform
from .runner import Timing, memory_snapshot, save, sha, validate_config
from .source_clock import SourceSampler
from .tracking import TrackingSession


class EntireStreamLatency:
    """Bounded global p95 upper bound: 1ms ceil bins, with explicit >1s overflow."""
    def __init__(self):
        self.bins, self.count, self.maximum = [0] * 1002, 0, 0.

    def add(self, value_ms):
        if not math.isfinite(value_ms) or value_ms < 0:
            raise ValueError("Latency must be finite and nonnegative")
        self.bins[min(math.ceil(value_ms), 1001)] += 1
        self.count += 1
        self.maximum = max(self.maximum, value_ms)

    def summary(self):
        upper = None
        if self.count:
            rank = .95 * (self.count - 1)
            lower_rank, upper_rank = math.floor(rank), math.ceil(rank)
            values, cumulative = [], 0
            for wanted in (lower_rank, upper_rank):
                cumulative = 0
                for value, number in enumerate(self.bins):
                    cumulative += number
                    if cumulative > wanted:
                        values.append(value)
                        break
            if max(values) <= 1000:
                upper = values[0] + (rank - lower_rank) * (values[1] - values[0])
        return {"count": self.count, "maximum_ms": self.maximum, "p95_upper_bound_ms": upper,
                "over_1000ms": self.bins[-1], "over_500ms": sum(self.bins[501:]),
                "scope": "entire stream; linear p95 upper bound from 1ms ceil bins; >1s quantile returns null",
                "retained_bin_count": len(self.bins)}


class LatestCapture:
    """Publish file frames at their PTS, or live frames at acquisition time."""
    def __init__(self, source, kind="paced-file", capture_options=None):
        import cv2
        options = capture_options or {}
        self.buffer_frames = options.get('buffer_frames', 1)
        if isinstance(self.buffer_frames, bool) or self.buffer_frames not in (1, 2) or not isinstance(self.buffer_frames, int):
            raise ValueError('buffer_frames must be integer1 or2')
        if kind not in ("paced-file", "live"):
            raise ValueError("Unknown realtime capture kind")
        if kind == "live" and Path(str(source)).is_file():
            raise ValueError("A local video file must use paced-file capture")
        self.kind = kind
        self.cap = cv2.VideoCapture(int(source) if kind == "live" and str(source).isdigit() else str(source))
        if not self.cap.isOpened():
            raise ValueError("Cannot open capture source")
        if kind == "live":
            if "fourcc" in options:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*options["fourcc"]))
            for name, prop in (("width", cv2.CAP_PROP_FRAME_WIDTH), ("height", cv2.CAP_PROP_FRAME_HEIGHT), ("fps", cv2.CAP_PROP_FPS)):
                if name in options:
                    self.cap.set(prop, options[name])
        self.width, self.height = int(self.cap.get(3)), int(self.cap.get(4))
        if self.width <= 0 or self.height <= 0:
            self.cap.release()
            raise ValueError("Capture did not report valid source dimensions")
        rate = float(self.cap.get(cv2.CAP_PROP_FPS))
        self.nominal_fps = rate if math.isfinite(rate) and rate > 0 else None
        if kind == "paced-file" and self.nominal_fps is None:
            self.cap.release()
            raise ValueError("Paced files require a declared constant frame rate")
        self.condition, self.stop_event = threading.Condition(), threading.Event()
        self.latest, self.last_taken, self.thread = None, -1, None
        self.pending = deque(maxlen=self.buffer_frames)
        self.last_take_history, self.history_reads = False, 0
        self.done, self.error, self.started = False, None, None
        self.frames, self.overwritten = 0, 0
        self.last_pts, self.first_input_pts = None, None
        self.lateness = Timing()

    def start(self):
        self.thread = threading.Thread(target=self._produce, name="latest-video-capture", daemon=True)
        self.thread.start()

    def _produce(self):
        import cv2
        try:
            self.started = time.monotonic()
            while not self.stop_event.is_set():
                request_time = time.monotonic()
                due = self.started + self.frames / self.nominal_fps if self.kind == "paced-file" else request_time
                remaining = due - time.monotonic()
                while remaining > 0 and not self.stop_event.is_set():
                    self.stop_event.wait(remaining)
                    remaining = due - time.monotonic()
                if self.stop_event.is_set():
                    break
                ok, image = self.cap.read()
                if not ok:
                    break
                now = time.monotonic()
                if self.kind == "paced-file":
                    source_pts = float(self.cap.get(cv2.CAP_PROP_POS_MSEC)) / 1000
                    if not math.isfinite(source_pts):
                        raise ValueError("Capture has no finite source PTS")
                    if self.first_input_pts is None:
                        self.first_input_pts = source_pts
                    pts = source_pts - self.first_input_pts
                    if self.last_pts is not None and pts <= self.last_pts:
                        raise ValueError("File PTS are not strictly increasing")
                    if abs(pts - self.frames / self.nominal_fps) > .0001:
                        raise ValueError("Paced input is not CFR; prepare the selected camera format first")
                else:
                    pts = request_time - self.started
                published = time.monotonic()
                with self.condition:
                    if len(self.pending) == self.buffer_frames:
                        self.overwritten += 1
                    self.latest = (self.frames, pts, due, image)
                    self.pending.append(self.latest)
                    self.frames += 1
                    self.last_pts = pts
                    self.lateness.add((published - due) * 1000)
                    self.condition.notify_all()
        except BaseException as error:
            self.error = repr(error)
        finally:
            with self.condition:
                self.done = True
                self.condition.notify_all()

    def take_after(self, sequence, prefer_history=False):
        with self.condition:
            while True:
                while self.pending and self.pending[0][0] <= sequence:
                    self.pending.popleft()
                if self.done or self.error or self.pending:
                    break
                self.condition.wait(.25)
            if self.error:
                raise RuntimeError(self.error)
            if not self.pending:
                return None
            if prefer_history:
                packet = self.pending.popleft()
            else:
                packet = self.pending.pop()
                self.overwritten += len(self.pending)
                self.pending.clear()
            self.last_taken = packet[0]
            self.last_take_history = packet[0] < self.latest[0]
            self.history_reads += int(self.last_take_history)
            return packet

    def snapshot(self):
        with self.condition:
            return {"captured_frames": self.frames, "overwritten_before_read": self.overwritten,
                    "maximum_application_queue_frames": self.buffer_frames, "history_frames_processed": self.history_reads,
                    "last_source_time_s": self.last_pts,
                    "source_time_origin_s": self.first_input_pts,
                    "capture_lateness_ms": self.lateness.summary(), "capture_done": self.done,
                    "capture_error": self.error}

    def close(self):
        self.stop_event.set()
        with self.condition:
            self.condition.notify_all()
        if self.thread is not None:
            self.thread.join(timeout=3)
            if self.thread.is_alive():
                raise RuntimeError("Capture read did not stop within 3 seconds")
        self.cap.release()


def fast_history_needed(tracking, axis, threshold):
    """Select only already-arrived history when measured motion is fast."""
    if threshold is None:
        return False
    coordinate = 1 if axis == 'y' else 0
    extent = tracking.height if axis == 'y' else tracking.width
    for track in tracking.tracker.tracked_stracks:
        observations = getattr(track, 'observations', [])
        if not track.is_activated or len(observations) != 2:
            continue
        (t0,b0),(t1,b1) = observations
        if not 0 < t1-t0 <= 1.5 or t1 != tracking.last_time:
            continue
        distance = ((b1[coordinate]+b1[coordinate+2])-(b0[coordinate]+b0[coordinate+2]))/2
        if abs(distance) / (extent * (t1-t0)) >= threshold:
            return True
    return False


def run(source, config, output, source_kind="paced-file", detector_factory=None):
    import cv2
    started = time.monotonic()
    validate_config(config)
    history_velocity = config.get('fast_history_velocity')
    if history_velocity is not None and (isinstance(history_velocity,bool) or not math.isfinite(history_velocity) or history_velocity <= 0
        or config.get('tracker',{}).get('motion_box') != 'observed_velocity' or config.get('capture',{}).get('buffer_frames') != 2):
        raise ValueError('Fast history needs positive finite velocity, observed motion and buffer_frames2')
    target_hz = float(config.get("sample_hz", 5.))
    preprocess_mode = config.get("preprocess_mode", "legacy")
    if preprocess_mode not in ("legacy", "resize_first_v1"):
        raise ValueError("Unknown realtime preprocessing version")
    detector_input = config.get("detector_input", "rgb_float32")
    if detector_input not in ("rgb_float32", "native_bgr"):
        raise ValueError("Unknown detector input representation")
    prepare_method = {("rgb_float32", "legacy"): "preprocess", ("rgb_float32", "resize_first_v1"): "preprocess_resize_first",
                      ("native_bgr", "legacy"): "prepare_bgr", ("native_bgr", "resize_first_v1"): "prepare_bgr_resize_first"}[(detector_input, preprocess_mode)]
    warmups = config.get("warmup_model_forwards", 0)
    if isinstance(warmups, bool) or not isinstance(warmups, int) or not 0 <= warmups <= 3:
        raise ValueError("Warmup model calls must be an explicit integer in 0..3")
    if not math.isfinite(target_hz) or target_hz <= 0:
        raise ValueError("Realtime mode requires a positive sample_hz")
    if config.get("decode_start_frame0", 0) or config.get("scope_start_frame0", 0):
        raise ValueError("Realtime input must already be the complete selected stream")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cv2.setNumThreads(1)
    capture = LatestCapture(source, source_kind, config.get("capture"))
    if config.get("expected_capture_size") is not None and [capture.width, capture.height] != config["expected_capture_size"]:
        capture.close()
        raise ValueError("Actual capture size differs from the configured physical geometry")
    session_id = config.get("session_id") or str(uuid.uuid4())
    tracking = TrackingSession(config, capture.width, capture.height, target_hz, session_id)
    recovery = EndpointRecovery(config, capture.width, capture.height)
    sampler = SourceSampler(target_hz)
    summary = {"status": "STARTING", "session_id": session_id, "run_id": str(uuid.uuid4()),
               "video_id": config.get("video_id", Path(str(source)).stem),
               "source": str(source), "source_kind": source_kind, "config": config,
               "source_size": [capture.width, capture.height], "nominal_fps": capture.nominal_fps,
               "target_detector_hz": target_hz, "effective_nominal_sample_hz": target_hz,
               "model_forwards": 0, "base_model_forwards": 0,
               "warmup_model_forwards": 0,
               "endpoint_recovery_forwards": 0, "processed_frames": 0, "sampler_rejected_frames": 0,
               "future_frame_violations": 0, "counts": {"IN": 0, "OUT": 0, "NET": 0},
               "uncertain_records": 0, "accuracy_verified": False, "software_fixture_only": detector_factory is not None,
               "clock_contract": "CFR read/decode starts at arrival with verified PTS; bounded latest capture buffer; causal fast history selection; predictions never count",
               "startup_scope": "startup_s includes source open/hash and model initialization inside run; Python imports excluded",
               "latency_boundary": "Expected source-frame arrival through detector/recovery/tracking/event log; source camera transport before decoder excluded",
               "memory_before_model": memory_snapshot()}
    if source_kind == "paced-file":
        summary["video_sha256"] = sha(source)
    timings = {name: Timing() for name in ("preprocess", "base_inference", "recovery", "tracking", "event_publication", "observation_age")}
    global_latency = EntireStreamLatency()
    detector = None
    files = [(output / name).open("w", encoding="utf-8", buffering=1) for name in ("frames.jsonl", "events.jsonl", "uncertain.jsonl")]
    frames_file, events_file, uncertain_file = files
    write = lambda file, row: file.write(json.dumps(row, allow_nan=False) + "\n")
    last_progress, sequence = -1e30, -1
    try:
        model = config["detector"]
        if detector_factory is not None:
            detector = detector_factory(model)
        elif model["backend"] == "o8":
            detector = O8Detector(**{k: model[k] for k in ("root", "program", "plan", "size")})
            summary.update(model_sha256=sha(Path(model["program"]) / "graph.bin"), resident_plan_sha256=sha(model["plan"]),
                           device_initialization=detector.initialization)
            root = Path(model["root"])
            summary["runtime_asset_sha256"] = {str(path.relative_to(root)): sha(path) for path in (
                root / "native_sources/native_queue.so", root / "hardware/accepted/firmware_manifest.json",
                root / "hardware/accepted/optimization_8_resident.bit")}
        elif model["backend"] == "onnx":
            detector = OnnxDetector(model["model"], model.get("threads", 1))
            summary["model_sha256"] = sha(model["model"])
        else:
            raise ValueError("Unsupported realtime detector")
        if detector_input == "native_bgr" and not hasattr(detector, "infer_bgr"):
            raise ValueError("Selected detector does not implement native BGR input")
        infer = detector.infer_bgr if detector_input == "native_bgr" else detector.infer
        if warmups:
            warm_input = (np.full((detector.size, detector.size, 3), 114, np.uint8) if detector_input == "native_bgr" else
                          np.full((1, 3, detector.size, detector.size), np.float32(114) / np.float32(255), np.float32))
            for _ in range(warmups):
                infer(warm_input)
                summary["model_forwards"] += 1
                summary["warmup_model_forwards"] += 1
        transform = Transform.create(capture.width, capture.height, config.get("detection_roi_xyxy"),
                                     config.get("rotation_clockwise", 0), detector.size)
        save(output / "transform.json", asdict(transform))
        summary.update(status="RUNNING", startup_s=time.monotonic() - started)
        save(output / "progress.json", summary)
        capture.start()
        while True:
            preserve_history = fast_history_needed(tracking, config.get('axis','y'), history_velocity)
            packet = capture.take_after(sequence, prefer_history=preserve_history)
            if packet is None:
                break
            sequence, pts, due, image = packet
            if not sampler.select(pts):
                summary["sampler_rejected_frames"] += 1
                continue
            tick = time.monotonic()
            summary["future_frame_violations"] += int(tick + .000001 < due)
            tensor = getattr(transform, prepare_method)(image)
            prepared = time.monotonic()
            raw = infer(tensor)
            inferred = time.monotonic()
            summary["model_forwards"] += 1
            summary["base_model_forwards"] += 1
            detections = decode(raw, transform, config.get("confidence", .2), config.get("cow_class_ids", [0]))
            base_detections, refinements = detections, []
            for proposal in recovery.proposals(pts, detections, tracking.counter.states, tracking.counter.stable_samples):
                local = Transform.create(capture.width, capture.height, proposal["roi"], transform.rotation, detector.size)
                local_tensor = getattr(local, prepare_method)(image)
                local_raw = infer(local_tensor)
                summary["model_forwards"] += 1
                summary["endpoint_recovery_forwards"] += 1
                candidates = decode(local_raw, local, config.get("confidence", .2), config.get("cow_class_ids", [0]))
                selected = recovery.select(proposal, candidates, detections)
                refinements.append({**proposal, "transform": asdict(local), "candidates": candidates.tolist(),
                                    "accepted_detection": None if selected is None else selected.tolist()})
                if selected is not None:
                    detections = np.concatenate((detections, selected[None]))
            recovered = time.monotonic()
            tracks, events, uncertain = tracking.update(sequence, pts, detections)
            if recovery.enabled:
                recovery.record(pts, tracks, tracking.counter.states)
            tracked = time.monotonic()
            event_publication_age = None
            for event in events:
                summary["counts"][event["kind"]] += 1
                write(events_file, {**event, "run_id": summary["run_id"], "wall_decision_s": tracked - capture.started,
                                    "decision_age_ms": (tracked - due) * 1000})
                events_file.flush()
                event_publication_age = (time.monotonic() - due) * 1000
                timings["event_publication"].add(event_publication_age)
            for row in uncertain:
                write(uncertain_file, row)
                summary["uncertain_records"] += 1
            summary["counts"]["NET"] = summary["counts"]["IN"] - summary["counts"]["OUT"]
            before_frame_log = time.monotonic()
            write(frames_file, {"run_id": summary["run_id"], "frame0": sequence, "time_s": pts,
                                "wall_since_stream_start_s": before_frame_log - capture.started,
                                "age_before_frame_log_ms": (before_frame_log - due) * 1000, "event_publication_age_ms": event_publication_age,
                                "fast_history_requested": preserve_history, "history_frame_selected": capture.last_take_history,
                                "base_detections": base_detections.tolist(), "detections": detections.tolist(),
                                "endpoint_recovery": refinements, "tracks": tracks, "counts": summary["counts"].copy()})
            summary["processed_frames"] += 1
            for name, seconds in (("preprocess", prepared - tick), ("base_inference", inferred - prepared),
                                  ("recovery", recovered - inferred), ("tracking", tracked - recovered)):
                timings[name].add(seconds * 1000)
            summary.update(capture=capture.snapshot(), last_source_time_s=pts, last_frame0=sequence)
            if events or tracked - last_progress >= 1:
                save(output / "progress.json", summary)
                last_progress = tracked
            age_ms = (time.monotonic() - due) * 1000
            timings["observation_age"].add(age_ms)
            global_latency.add(age_ms)
        for row in tracking.finish():
            write(uncertain_file, row)
            summary["uncertain_records"] += 1
        expected = config.get("expected_capture_frames")
        if expected is not None and capture.frames != expected:
            raise ValueError("Capture EOF does not cover the declared input")
        if not summary["processed_frames"]:
            raise ValueError("No frame reached the detector")
        summary["status"] = "COMPLETED_UNSCORED"
    except BaseException as error:
        summary.update(status="FAILED", error=repr(error), traceback=traceback.format_exc())
        raise
    finally:
        cleanup_errors = []
        try:
            capture.close()
        except Exception as error:
            cleanup_errors.append({"component": "capture", "error": repr(error)})
        for file in files:
            try:
                file.close()
            except Exception as error:
                cleanup_errors.append({"component": str(file.name), "error": repr(error)})
        if detector is not None:
            closing, detector = detector, None
            try:
                closing.close()
            except Exception as error:
                cleanup_errors.append({"component": "detector", "error": repr(error)})
        if cleanup_errors:
            summary["cleanup_errors"] = cleanup_errors
            if summary["status"] == "COMPLETED_UNSCORED":
                summary["status"] = "CLEANUP_FAILED"
        ended = time.monotonic()
        snapshot = capture.snapshot()
        entire_latency = global_latency.summary()
        summary.update(capture=snapshot, elapsed_s=ended - started, timings={key: value.summary() for key, value in timings.items()},
                       unavailable_source_sample_slots=sampler.unavailable_slots, memory_after_close=memory_snapshot(),
                       maximum_state_count=tracking.maximum_state_count, latency_entire_stream=entire_latency)
        if capture.started is not None and capture.last_pts is not None:
            summary.update(stream_wall_elapsed_s=ended - capture.started, source_duration_s=capture.last_pts,
                           drain_after_last_source_frame_s=ended - capture.started - capture.last_pts)
            summary["realtime_clock_pass"] = (summary["status"] == "COMPLETED_UNSCORED" and
                summary["future_frame_violations"] == 0 and snapshot["capture_lateness_ms"]["maximum_ms"] <= 250 and
                entire_latency["maximum_ms"] <= 1000 and entire_latency["p95_upper_bound_ms"] is not None and
                entire_latency["p95_upper_bound_ms"] <= 500 and
                summary["drain_after_last_source_frame_s"] <= 1.)
        else:
            summary["realtime_clock_pass"] = False
        save(output / "summary.json", summary)
    if summary["status"] != "COMPLETED_UNSCORED":
        raise RuntimeError(summary["status"])
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-kind", choices=("paced-file", "live"), default="paced-file")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source, json.loads(args.config.read_text(encoding="utf-8-sig")), args.output, args.source_kind)
    print(json.dumps({key: result.get(key) for key in ("status", "counts", "model_forwards", "realtime_clock_pass", "stream_wall_elapsed_s")}))


if __name__ == "__main__":
    main()
