"""Bounded preprocessing-only measurements; no detector or model initialization."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import cv2
import numpy as np
from counting.geometry import Transform


def benchmark(args):
    if args.repeats < 3 or args.repeats > 30:
        raise ValueError("Use 3..30 bounded preprocessing repetitions")
    if args.output.exists():
        raise FileExistsError(args.output)
    cv2.setNumThreads(1)
    config = json.loads(args.config.read_text())
    cap = cv2.VideoCapture(str(args.video))
    try:
        if not cap.set(cv2.CAP_PROP_POS_FRAMES, args.frame0):
            raise ValueError("Cannot seek the fixed input frame")
        ok, image = cap.read()
        if not ok:
            raise ValueError("Fixed input frame unavailable")
        pts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
    finally:
        cap.release()
    height, width = image.shape[:2]
    rows = []
    for size in (192, 320):
        transform = Transform.create(width, height, config["detection_roi_xyxy"], config["rotation_clockwise"], size)
        legacy = transform.preprocess(image)
        fast = transform.preprocess_resize_first(image)
        difference = float(np.max(np.abs(legacy - fast)))
        for name, method in (("legacy", transform.preprocess), ("resize_first_v1", transform.preprocess_resize_first)):
            for _ in range(2):
                method(image)
            times = []
            for _ in range(args.repeats):
                started = time.perf_counter()
                tensor = method(image)
                times.append((time.perf_counter() - started) * 1000)
                if tensor.shape != (1, 3, size, size):
                    raise ValueError("Preprocess output shape mismatch")
            rows.append({"size": size, "mode": name, "samples_ms": times, "mean_ms": float(np.mean(times)),
                         "p95_ms": float(np.percentile(times, 95)), "legacy_vs_fast_max_tensor_difference": difference})
    result = {"status": "PREPROCESS_ONLY_MEASURED", "video_sha256": hashlib.sha256(args.video.read_bytes()).hexdigest(),
              "frame0": args.frame0, "source_PTS_s": pts, "source_size": [width, height], "opencv": cv2.__version__,
              "numpy": np.__version__, "warmups_each_mode": 2, "new_model_forwards": 0, "rows": rows}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frame0", type=int, default=200)
    parser.add_argument("--repeats", type=int, default=8)
    benchmark(parser.parse_args())
