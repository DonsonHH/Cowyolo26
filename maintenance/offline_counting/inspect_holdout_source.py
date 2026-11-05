"""Source-only calibration sheets and exact PTS index, before frozen predictions."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import cv2
import numpy as np


def write_image(path, image):
    # imwrite cannot open some Windows Unicode paths; encoding is path-independent.
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("Contact sheet encoding failed")
    Path(path).write_bytes(encoded.tobytes())


def inspect(video, output, step_s=2.):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cv2.setNumThreads(1)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError("Source cannot be decoded")
    W, H, fps = int(cap.get(3)), int(cap.get(4)), cap.get(5)
    tiles, pages, times, samples = [], [], [], []
    next_sample, frame = 0., 0
    crop_width = round(W * .75) - round(W * .34)
    tw, th = 200, round(H * 200 / crop_width)
    def save_page():
        if not tiles:
            return
        canvas = np.full((4 * (th + 30), 4 * tw, 3), 24, np.uint8)
        for i, tile in enumerate(tiles):
            y, x = (i // 4) * (th + 30), (i % 4) * tw
            canvas[y:y + th + 30, x:x + tw] = tile
        name = f"raw_sheet_{len(pages):03d}.jpg"
        write_image(output / name, canvas)
        pages.append(name)
        tiles.clear()
    try:
        while True:
            ok, image = cap.read()
            if not ok:
                break
            pts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if not np.isfinite(pts) or times and pts <= times[-1]:
                raise ValueError(f"Invalid source PTS at decoded ordinal {frame}")
            times.append(pts)
            if pts + 1e-9 >= next_sample:
                crop = image[:, round(W * .34):round(W * .75)]
                tile = np.full((th + 30, tw, 3), 24, np.uint8)
                tile[30:] = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_AREA)
                cv2.putText(tile, f"f{frame}  {pts:.2f}s", (4, 20), cv2.FONT_HERSHEY_SIMPLEX, .43, (240, 240, 240), 1)
                tiles.append(tile)
                samples.append({"frame0": frame, "time_s": pts, "page": len(pages), "tile": len(tiles) - 1})
                if len(tiles) == 16:
                    save_page()
                if len(samples) == 1 or len(samples) % 100 == 0:
                    overview = cv2.resize(image, (960, round(H * 960 / W)))
                    for x in (.34, .75):
                        cv2.line(overview, (round(x * 960), 0), (round(x * 960), overview.shape[0] - 1), (0, 180, 255), 2)
                    write_image(output / f"layout_{frame:06d}.jpg", overview)
                next_sample += step_s
            frame += 1
    finally:
        cap.release()
    save_page()
    digest = hashlib.sha256()
    with Path(video).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    index = {"source_video_sha256": digest.hexdigest(), "source_frame_times_s": times,
             "source_seek_index": {}, "decoder": "OpenCV " + cv2.__version__, "contains_model_results": False}
    (output / "source_index.json.gz").write_bytes(gzip.compress(json.dumps(index).encode(), mtime=0))
    summary = {"status": "SOURCE_CALIBRATION_ONLY", "source": str(video), "source_sha256": digest.hexdigest(),
               "bytes": Path(video).stat().st_size, "width": W, "height": H, "nominal_fps": fps,
               "decoded_frames": frame, "last_pts_s": times[-1] if times else None,
               "raw_contact_step_s": step_s, "channel_crop_for_inspection_only": [.34, .75],
               "pages": pages, "samples": samples, "SLURM_JOB_ID": os.environ.get("SLURM_JOB_ID"),
               "model_forwards": 0, "reference_events_created": False}
    (output / "source_info.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("status", "decoded_frames", "last_pts_s", "source_sha256", "model_forwards")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--step-s", type=float, default=2.)
    args = parser.parse_args()
    inspect(args.video, args.output, args.step_s)
