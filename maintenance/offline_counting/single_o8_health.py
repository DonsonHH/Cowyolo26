"""One fixed, prior diagnostic tensor through the frozen detector; no counting."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from prepare_o8_boot import durable_json


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def health(protocol_path, output):
    protocol = json.loads(protocol_path.read_text())
    output.mkdir(parents=True, exist_ok=False)
    record = {"status": "RUNNING", "PID": os.getpid(), "started_UTC": datetime.now(timezone.utc).isoformat(),
              "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
              "model_forwards_completed": 0, "forward_call_about_to_start": False,
              "new_video_decodes": 0, "counting_performed": False, "overlay_downloaded": False,
              "protocol_sha256": sha(protocol_path)}
    started, detector = time.monotonic(), None

    def mark(phase):
        record.update(phase=phase, elapsed_s=time.monotonic() - started)
        durable_json(output / "health.json", record)
        print(phase, flush=True)

    try:
        mark("VERIFY_FROZEN_INPUTS_AND_RUNTIME")
        if record["boot_id"] != protocol["expected_boot_id"]:
            raise ValueError("Board rebooted after registered-overlay preparation")
        for path, digest in protocol["expected_file_sha256"].items():
            if sha(path) != digest:
                raise ValueError("Health input/runtime hash mismatch: " + path)
        mark("IMPORT_NUMPY_AND_DETECTOR")
        import numpy as np
        from counting.backends import O8Detector, decode
        from counting.geometry import Transform
        metadata = json.loads(Path(protocol["input_manifest"]).read_text())
        row, = [item for item in metadata["frames"] if item["key"] == protocol["input_key"]]
        with np.load(protocol["inputs"], allow_pickle=False) as arrays:
            tensor = np.ascontiguousarray(arrays[row["key"]], dtype=np.float32)
        if hashlib.sha256(tensor.tobytes()).hexdigest() != row["input_tensor_sha256"] or tensor.shape != (1, 3, 320, 320):
            raise ValueError("Fixed health tensor differs from its prior measurement")
        values = row["transform"].copy()
        values["roi"] = tuple(values["roi"])
        transform = Transform(**values)
        rebuilt = Transform.create(transform.source_width, transform.source_height, transform.roi,
                                   transform.rotation, transform.size)
        if rebuilt != transform or transform.size != protocol["detector"]["size"] or transform.size != tensor.shape[-1]:
            raise ValueError("Fixed tensor, detector size and full transform do not agree")
        record.update(input_tensor_sha256=row["input_tensor_sha256"], transform=row["transform"])
        mark("INITIALIZE_FROZEN_DETECTOR")
        detector = O8Detector(**protocol["detector"])
        record["device_initialization"] = detector.initialization
        record["forward_call_about_to_start"] = True
        mark("INFER_ONE_FIXED_TENSOR")
        raw = detector.infer(tensor)
        record["model_forwards_completed"] = 1
        candidates = decode(raw, transform, .05, [0])
        record["candidates_original_xyxy_conf_class"] = candidates.astype(float).tolist()
        expected = np.asarray(protocol["expected_candidates"], dtype=float).reshape(-1, 6)
        difference = float(np.max(np.abs(candidates - expected))) if candidates.shape == expected.shape and candidates.size else None
        record["maximum_candidate_difference"] = difference
        if candidates.shape != expected.shape or not np.allclose(candidates, expected, rtol=0, atol=.001):
            raise ValueError("Frozen detector health differs from the prior same-tensor result")
        mark("CLOSE_DETECTOR")
        closing, detector = detector, None
        try:
            closing.close()
        except BaseException as error:
            record.update(status="CLOSE_FAILED", close_error=repr(error))
            raise
        record["status"] = "PASS_ONE_REAL_MODEL_FORWARD_NO_COUNTING"
        mark("COMPLETE")
    except BaseException as error:
        status = "CLOSE_FAILED" if record["status"] == "CLOSE_FAILED" else "FAILED"
        record.update(status=status, failed_phase=record.get("phase"), error=repr(error))
        mark(status)
        raise
    finally:
        if detector is not None:
            closing, detector = detector, None
            try:
                closing.close()
            except Exception as error:
                record.update(status="CLOSE_FAILED", close_error=repr(error))
                mark("CLOSE_FAILED")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    health(args.protocol, args.output)
