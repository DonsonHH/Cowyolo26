"""Four prior fixed tensors: formal native BGR-vs-FP32 raw parity and timings."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
try:
    from .prepare_o8_boot import durable_json
except ImportError:
    from prepare_o8_boot import durable_json


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def same_finite_bits(first, second):
    import numpy as np
    return (first.shape == second.shape and first.dtype == second.dtype and
            bool(np.isfinite(first).all()) and bool(np.isfinite(second).all()) and
            first.tobytes(order="C") == second.tobytes(order="C"))


def evaluate(protocol_path, output):
    protocol = json.loads(protocol_path.read_text())
    if len(protocol["input_keys"]) != 4 or len(set(protocol["input_keys"])) != 4:
        raise ValueError("Native BGR qualification requires four distinct fixed inputs")
    output.mkdir(parents=True, exist_ok=False)
    record = {"status": "RUNNING", "started_UTC": datetime.now(timezone.utc).isoformat(),
              "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
              "model_forwards_completed": 0, "video_decodes": 0, "counting_performed": False,
              "planned_warmup_forwards": 2, "planned_formal_forward_calls": 8,
              "completed_warmup_forwards": 0, "completed_formal_forward_calls": 0,
              "rows": [], "calls": [], "inflight_call": None, "protocol_sha256": sha(protocol_path)}
    detector = None
    def mark(phase):
        record["phase"] = phase
        durable_json(output / "parity.json", record)
        print(phase, flush=True)
    def invoke(kind, function, value):
        ordinal = record["model_forwards_completed"] + 1
        record["inflight_call"] = {"ordinal": ordinal, "kind": kind, "state": "ABOUT_TO_CALL"}
        mark("BEFORE_" + kind.upper() + "_" + str(ordinal))
        started = time.perf_counter()
        raw = function(value)
        elapsed_ms = (time.perf_counter() - started) * 1000
        record["model_forwards_completed"] += 1
        field = "completed_warmup_forwards" if kind.startswith("warmup") else "completed_formal_forward_calls"
        record[field] += 1
        record["calls"].append({"ordinal": ordinal, "kind": kind, "elapsed_ms": elapsed_ms})
        record["inflight_call"] = None
        mark("AFTER_" + kind.upper() + "_" + str(ordinal))
        return raw, elapsed_ms
    try:
        mark("VERIFY_FROZEN_FILES")
        if record["boot_id"] != protocol["expected_boot_id"]:
            raise ValueError("Board rebooted before native input qualification")
        for path, digest in protocol["expected_file_sha256"].items():
            if sha(path) != digest:
                raise ValueError("Frozen BGR parity dependency mismatch: " + path)
        import numpy as np
        from bgr_backend import O8Detector
        mark("INITIALIZE_REGISTERED_MODEL")
        detector = O8Detector(**protocol["detector"])
        with np.load(protocol["inputs"], allow_pickle=False) as arrays:
            for index, key in enumerate(protocol["input_keys"]):
                tensor = np.ascontiguousarray(arrays[key], dtype=np.float32)
                if tensor.shape != (1, 3, detector.size, detector.size):
                    raise ValueError("Fixed parity tensor size differs from the registered graph")
                rgb = np.rint(tensor[0].transpose(1, 2, 0) * np.float32(255)).astype(np.uint8)
                canvas = np.ascontiguousarray(rgb[..., ::-1])
                reconstructed = np.ascontiguousarray(canvas[..., ::-1].transpose(2, 0, 1)[None], np.float32) / np.float32(255)
                if not same_finite_bits(reconstructed, tensor):
                    raise ValueError("Prior tensor is not exactly reconstructible from BGR bytes")
                if index == 0:
                    invoke("warmup_float32", detector.infer, tensor)
                    invoke("warmup_bgr", detector.infer_bgr, canvas)
                mark("FORMAL_PAIR_" + str(index))
                reference, f32_ms = invoke("formal_float32", detector.infer, tensor)
                actual, bgr_ms = invoke("formal_bgr", detector.infer_bgr, canvas)
                equal = same_finite_bits(actual, reference)
                if not np.isfinite(actual).all() or not np.isfinite(reference).all() or actual.shape != reference.shape:
                    raise ValueError("Native input parity returned nonfinite or mismatched output")
                record["rows"].append({"key": key, "input_tensor_sha256": hashlib.sha256(tensor.tobytes()).hexdigest(),
                                       "complete_raw_bitwise_equal": bool(equal), "max_absolute_difference": float(np.max(np.abs(actual - reference))),
                                       "tensor_to_raw_ms": f32_ms, "bgr_canvas_to_raw_ms": bgr_ms})
                if not equal:
                    raise ValueError("Native BGR entry raw differs from registered tensor entry")
        mark("CLOSE_ONCE")
        closing, detector = detector, None
        closing.close()
        record["status"] = "PASS_FOUR_FIXED_PAIRS_NOT_VIDEO_COUNT_ACCURACY"
        mark("COMPLETE")
    except BaseException as error:
        record.update(status="FAILED", failed_phase=record.get("phase"), error=repr(error))
        mark("FAILED")
        raise
    finally:
        if detector is not None:
            closing, detector = detector, None
            try:
                closing.close()
            except Exception as error:
                record.update(status="CLOSE_FAILED", close_error=repr(error))
                mark("CLOSE_FAILED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.protocol, args.output)
