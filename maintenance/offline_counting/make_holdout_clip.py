"""Native-resolution stream-copy excerpt with full decode validation; no inference."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
import cv2


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def create(source, output, start, end, tool_runtime=None):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    if not 0 <= start < end:
        raise ValueError("Invalid requested source interval")
    runtime = json.loads(Path(tool_runtime).read_text()) if tool_runtime else {}
    encoder = runtime.get("exe") or shutil.which("ffmpeg")
    if not encoder:
        raise FileNotFoundError("Existing ffmpeg command required")
    clip = output / "input.mp4"
    command = [encoder, "-nostdin", "-hide_banner", "-loglevel", "warning", "-ss", str(start),
               "-i", str(source), "-t", str(end - start), "-map", "0:v:0", "-c:v", "copy", "-an",
               "-avoid_negative_ts", "make_zero", "-movflags", "+faststart", str(clip)]
    child_environment = os.environ.copy()
    if runtime.get("library_dirs"):
        child_environment["LD_LIBRARY_PATH"] = ":".join(runtime["library_dirs"])
    result = subprocess.run(command, capture_output=True, env=child_environment)
    (output / "remux.log").write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Stream copy failed")
    capture = cv2.VideoCapture(str(clip))
    if not capture.isOpened():
        raise ValueError("Excerpt cannot be decoded")
    width, height, fps = int(capture.get(3)), int(capture.get(4)), capture.get(5)
    count, times = 0, []
    try:
        while True:
            ok, image = capture.read()
            if not ok:
                break
            time_s = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if times and time_s <= times[-1]:
                raise ValueError("Excerpt PTS is not strictly increasing")
            times.append(time_s)
            if count == 0:
                cv2.imwrite(str(output / "first_frame.jpg"), image)
            count += 1
    finally:
        capture.release()
    if count < 2:
        raise ValueError("No usable excerpt")
    value = {"status": "REMUX_EXCERPT_DECODED", "source": str(source), "source_sha256": sha(source),
             "requested_source_time_window_s": [start, end], "clip_sha256": sha(clip),
             "clip_bytes": clip.stat().st_size, "width": width, "height": height,
             "nominal_fps": fps, "decoded_frames": count, "first_clip_pts_s": times[0],
             "last_clip_pts_s": times[-1], "stream_copy_command": command,
             "spatial_resize_or_pixel_reencoding": False,
             "source_frame_offset_claimed_exact": False,
             "boundary_policy": "stream copy may align to nearby codec keyframes; evaluate complete passages in this actual clip, log censored fragments",
             "model_forwards": 0, "SLURM_JOB_ID": os.environ.get("SLURM_JOB_ID")}
    value["ffmpeg_version"] = runtime.get("version")
    (output / "clip_info.json").write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-s", type=float, required=True)
    parser.add_argument("--end-s", type=float, required=True)
    parser.add_argument("--tool-runtime", type=Path)
    args = parser.parse_args()
    create(args.video, args.output, args.start_s, args.end_s, args.tool_runtime)
