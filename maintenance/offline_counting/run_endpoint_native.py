"""Run only fixed diagnostic tensors through the registered board detector."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from counting.backends import O8Detector, decode
from counting.geometry import Transform


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(args):
    meta = json.loads(args.manifest.read_text())
    config = json.loads(args.config.read_text())
    assert sha(args.inputs) == meta["inputs_npz_sha256"]
    assert sha(args.config) == meta["config_sha256"]
    assert len(meta["frames"]) == meta.get("expected_input_count", 20)
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"status": "RUNNING", "PID": os.getpid(), "started_UTC": datetime.now(timezone.utc).isoformat(),
              "boot_id": Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              "new_NPU_model_forwards": 0, "video_decodes_on_board": 0, "counting_performed": False,
              "inputs_npz_sha256": sha(args.inputs), "inputs_manifest_sha256": sha(args.manifest),
              "config_sha256": sha(args.config), "rows": []}
    save = lambda: (args.output / "native_probe.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    save()
    detector = None
    try:
        detector = O8Detector(**{k: config["detector"][k] for k in ("root", "program", "plan", "size")})
        with np.load(args.inputs, allow_pickle=False) as tensors:
            for row in meta["frames"]:
                transform_values = row.get("transform", meta.get("transform")).copy()
                transform_values["roi"] = tuple(transform_values["roi"])
                transform = Transform(**transform_values)
                tensor = np.ascontiguousarray(tensors[row["key"]], dtype=np.float32)
                assert hashlib.sha256(tensor.tobytes()).hexdigest() == row["input_tensor_sha256"]
                raw = detector.infer(tensor)
                report["new_NPU_model_forwards"] += 1
                report["rows"].append({**row, "candidates_original_xyxy_conf_class": decode(raw, transform, .05, [0]).tolist()})
                save()
        report["status"] = "COMPLETED_SPARSE_NATIVE_DIAGNOSTIC"
    except BaseException as error:
        report.update(status="FAILED", error=repr(error))
        raise
    finally:
        if detector is not None:
            try:
                detector.close()
            except Exception as error:
                report.update(status="CLOSE_FAILED", close_error=repr(error))
        report["ended_UTC"] = datetime.now(timezone.utc).isoformat()
        save()
    if report["status"] != "COMPLETED_SPARSE_NATIVE_DIAGNOSTIC":
        raise RuntimeError(report["status"])
    print(json.dumps({"status": report["status"], "new_NPU_forwards": report["new_NPU_model_forwards"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "manifest", "config", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    execute(parser.parse_args())
