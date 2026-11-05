"""Prepare fixed shared tensors and a same-checkpoint FP32 diagnostic, not event GT."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from counting.backends import OnnxDetector, decode
from counting.geometry import Transform


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(args):
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    assert protocol["status"] == "PLANNED_NOT_EXECUTED"
    assert sha(args.video) == protocol["source_video_sha256"]
    assert sha(args.config) == protocol["unmodified_config_sha256"]
    assert sha(args.model) == "b7dd0db3c9fb80f0249c4821634c4ff9c65d95a503e609ef50ef3617fa512799"
    wanted = protocol["frame0_indices"]
    assert len(wanted) == len(set(wanted)) == 20 and wanted == sorted(wanted)
    args.output.mkdir(parents=True, exist_ok=False)
    cap = cv2.VideoCapture(str(args.video))
    width, height = int(cap.get(3)), int(cap.get(4))
    transform = Transform.create(width, height, config["detection_roi_xyxy"], config["rotation_clockwise"], config["detector"]["size"])
    tensors, metadata = {}, []
    frame0 = 0
    try:
        while frame0 <= wanted[-1]:
            ok, image = cap.read()
            assert ok, f"Source ended before frame {frame0}"
            if frame0 in wanted:
                tensor = transform.preprocess(image)
                key = f"frame_{frame0:06d}"
                tensors[key] = tensor
                metadata.append({"frame0": frame0, "source_time_s": cap.get(cv2.CAP_PROP_POS_MSEC) / 1000,
                                 "key": key, "input_tensor_sha256": hashlib.sha256(tensor.tobytes()).hexdigest()})
            frame0 += 1
    finally:
        cap.release()
    assert len(metadata) == 20
    np.savez_compressed(args.output / "inputs.npz", **tensors)
    meta = {"status": "FIXED_SHARED_INPUTS_PREPARED", "source_video_sha256": sha(args.video),
            "config_sha256": sha(args.config), "protocol_sha256": sha(args.protocol),
            "inputs_npz_sha256": sha(args.output / "inputs.npz"), "transform": asdict(transform),
            "frames": metadata, "source_decoder_versions": {"cv2": cv2.__version__, "numpy": np.__version__},
            "scope": "Sparse model diagnostic using identical PC-prepared tensors for FP32 and board INT8. Not whole-video board decoding or independent count accuracy.",
            "reporting_confidence_floor": .05, "new_video_decodes": frame0,
            "created_UTC": datetime.now(timezone.utc).isoformat()}
    (args.output / "inputs_manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    detector = OnnxDetector(args.model)
    results = []
    try:
        for row in metadata:
            raw = detector.infer(tensors[row["key"]])
            candidates = decode(raw, transform, .05, [0]).tolist()
            results.append({**row, "candidates_original_xyxy_conf_class": candidates})
    finally:
        detector.close()
    report = {"status": "COMPLETED_SPARSE_FP32_REFERENCE", "model_sha256": sha(args.model),
              "source_checkpoint_sha256": "5b739e5a59f3aed9dc56018c05d5a2604f0051d8c76d41c97039a2cd253cdd52",
              "inputs_manifest_sha256": sha(args.output / "inputs_manifest.json"),
              "new_CPU_model_forwards": len(results), "counting_performed": False, "rows": results}
    (args.output / "fp32_reference.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"inputs": len(metadata), "CPU_reference_forwards": len(results), "tensor_archive_bytes": (args.output / "inputs.npz").stat().st_size,
                      "output": str(args.output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "config", "protocol", "model", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    prepare(parser.parse_args())
