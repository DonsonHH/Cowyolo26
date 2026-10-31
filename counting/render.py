"""Render recorded tracks and events over the scoped original video, no inference."""
import argparse
import json
import subprocess
from pathlib import Path


def rows(path):
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


def render(video, run, output, width=960):
    import cv2
    run, output = Path(run), Path(output)
    if output.exists():
        raise FileExistsError(output)
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    if summary["status"] != "COMPLETED_UNSCORED":
        raise ValueError("Completed run required")
    config = summary["config"]
    cap = cv2.VideoCapture(str(video))
    W, H = int(cap.get(3)), int(cap.get(4))
    height = round(H * width / W / 2) * 2
    start = config.get("scope_start_frame0", 0)
    end = config.get("end_frame0_exclusive", int(cap.get(7)))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
               "-pixel_format", "bgr24", "-video_size", f"{width}x{height}", "-framerate",
               str(summary["nominal_fps"]), "-i", "pipe:0", "-an", "-c:v", "libx264",
               "-threads", "2", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(output)]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    frame_rows, event_rows = iter(rows(run / "frames.jsonl")), iter(rows(run / "events.jsonl"))
    next_row, next_event, observation = next(frame_rows, None), next(event_rows, None), None
    counts = {"IN": 0, "OUT": 0}
    decoded = 0
    try:
        for frame in range(start, end):
            ok, image = cap.read()
            if not ok:
                break
            while next_row is not None and next_row["frame0"] <= frame:
                observation = next_row
                next_row = next(frame_rows, None)
            while next_event is not None and next_event["frame0"] <= frame:
                counts[next_event["kind"]] += 1
                next_event = next(event_rows, None)
            tile = cv2.resize(image, (width, height))
            lo, hi = config.get("perpendicular_roi", [0, 1])
            axis = config.get("axis", "y")
            lower, upper = config.get("counter", {}).get("lower", .4), config.get("counter", {}).get("upper", .6)
            if axis == "y":
                for x in (lo, hi):
                    cv2.line(tile, (round(x * width), 0), (round(x * width), height - 1), (0, 170, 255), 2)
                for y in (lower, upper):
                    cv2.line(tile, (round(lo * width), round(y * height)), (round(hi * width), round(y * height)), (0, 170, 255), 1)
            else:
                for y in (lo, hi):
                    cv2.line(tile, (0, round(y * height)), (width - 1, round(y * height)), (0, 170, 255), 2)
                for x in (lower, upper):
                    cv2.line(tile, (round(x * width), round(lo * height)), (round(x * width), round(hi * height)), (0, 170, 255), 1)
            if observation and frame - observation["frame0"] <= summary["source_stride"]:
                for track in observation["tracks"]:
                    x1, y1, x2, y2 = track["xyxy"]
                    a, b = (round(x1 / W * width), round(y1 / H * height)), (round(x2 / W * width), round(y2 / H * height))
                    cv2.rectangle(tile, a, b, (90, 235, 120), 2)
                    cv2.putText(tile, "temp " + str(track["track_id"]), (a[0], max(45, a[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, .5, (90, 235, 120), 1)
            cv2.rectangle(tile, (0, 0), (width, 37), (20, 29, 40), -1)
            observed = observation["frame0"] if observation else "none"
            label = f"source f{frame} | observed f{observed} (held for display) | IN {counts['IN']} OUT {counts['OUT']}"
            cv2.putText(tile, label, (8, 25), cv2.FONT_HERSHEY_SIMPLEX, .52, (240, 240, 240), 1, cv2.LINE_AA)
            encoder.stdin.write(tile.tobytes())
            decoded += 1
    finally:
        cap.release()
        encoder.stdin.close()
    if encoder.wait() != 0 or decoded != end - start:
        raise RuntimeError("Review rendering failed or source ended early")
    return {"rendered_frames": decoded, "counts_from_event_log": counts,
            "source_interval_frame0": [start, end - 1], "new_model_forwards": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.video, args.run, args.output)))
