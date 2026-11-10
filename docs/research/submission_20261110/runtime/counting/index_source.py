"""Build a source-only ordinal/PTS index and validate optional seek landmarks."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path


def build_index(video, output, end_frame=None, anchors=()):
    import cv2
    if end_frame is not None and end_frame < 0 or any(frame < 0 for frame in anchors):
        raise ValueError("Frame ordinals must be nonnegative")
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    requested = {0, *map(int, anchors)}
    if end_frame is not None:
        requested.add(end_frame)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError("Cannot open source")
    times, points = [], {}
    try:
        frame = 0
        while end_frame is None or frame <= end_frame:
            ok, image = cap.read()
            if not ok:
                if end_frame is not None:
                    raise ValueError("Source ended before requested index interval")
                break
            pts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if not math.isfinite(pts) or times and pts <= times[-1]:
                raise ValueError("Source needs unique increasing PTS")
            times.append(pts)
            if frame in requested:
                points[str(frame)] = {"time_s": pts, "bgr_sha256": hashlib.sha256(image.tobytes()).hexdigest()}
            frame += 1
    finally:
        cap.release()
    cap = cv2.VideoCapture(str(video))
    try:
        for frame, expected in points.items():
            ok = cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame))
            ok, image = cap.read() if ok else (False, None)
            expected["seek_hash_matches"] = bool(ok and hashlib.sha256(image.tobytes()).hexdigest() == expected["bgr_sha256"])
            expected["seek_pts_matches"] = bool(ok and abs(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 - expected["time_s"]) < 1e-7)
    finally:
        cap.release()
    digest = hashlib.sha256()
    with Path(video).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    value = {"source_video_sha256": digest.hexdigest(), "source_frame_times_s": times,
             "source_seek_index": points, "decoder": "OpenCV " + cv2.__version__,
             "contains_model_results": False}
    data = json.dumps(value, indent=2).encode()
    output.write_bytes(gzip.compress(data, mtime=0) if output.suffix == ".gz" else data)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--end-frame0", type=int)
    parser.add_argument("--anchors", type=int, nargs="*", default=[])
    args = parser.parse_args()
    result = build_index(args.video, args.output, args.end_frame0, args.anchors)
    print(json.dumps({"indexed_frames": len(result["source_frame_times_s"]), "contains_model_results": False}))
