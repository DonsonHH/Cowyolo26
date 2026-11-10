"""Render recorded tracks and events over the scoped original video, no inference."""
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
from .channel import ChannelPolygon
from .protocol import gate_from_config
from .runner import sha


def draw_channel(tile, config):
    """Draw the same source-coordinate region and gates used by counting/review."""
    import cv2
    height, width = tile.shape[:2]
    gate = gate_from_config(config)
    lo, hi = gate["perpendicular_roi"]
    axis, lower, upper = gate["axis"], gate["lower"], gate["upper"]
    color = (0, 170, 255)
    if "channel_polygon" in gate:
        polygon = ChannelPolygon(gate["channel_polygon"])
        points = np.rint(np.asarray(polygon.points) * [width, height]).astype(np.int32)
        cv2.polylines(tile, [points], True, color, 2)
        for bound in (lower, upper):
            for a, b in polygon.gate_segments(axis, bound):
                cv2.line(tile, (round(a[0] * width), round(a[1] * height)),
                         (round(b[0] * width), round(b[1] * height)), color, 1)
    elif axis == "y":
        for x in (lo, hi):
            cv2.line(tile, (round(x * width), 0), (round(x * width), height - 1), color, 2)
        for y in (lower, upper):
            cv2.line(tile, (round(lo * width), round(y * height)), (round(hi * width), round(y * height)), color, 1)
    else:
        for y in (lo, hi):
            cv2.line(tile, (0, round(y * height)), (width - 1, round(y * height)), color, 2)
        for x in (lower, upper):
            cv2.line(tile, (round(x * width), round(lo * height)), (round(x * width), round(hi * height)), color, 1)


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
    if not summary.get('video_sha256') or sha(video)!=summary['video_sha256']:
        raise ValueError('Review video source SHA256 differs from the recorded run')
    provenance=output.with_suffix(output.suffix+'.provenance.json')
    if provenance.exists():raise FileExistsError(provenance)
    config = summary["config"]
    cap = cv2.VideoCapture(str(video))
    W, H = int(cap.get(3)), int(cap.get(4))
    if not cap.isOpened() or [W,H]!=summary['source_size']:
        cap.release()
        raise ValueError('Review source dimensions differ from recorded run')
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
            draw_channel(tile, config)
            source_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            hold_seconds = 1.1 / summary["effective_nominal_sample_hz"]
            if observation and 0 <= source_time - observation["time_s"] <= hold_seconds:
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
    result={"rendered_frames": decoded, "counts_from_event_log": counts,
            "source_interval_frame0": [start, end - 1], "new_model_forwards": 0,
            'source_video_sha256':summary['video_sha256'],'run_id':summary['run_id'],
            'run_evidence_sha256':{name:sha(run/name) for name in ('summary.json','frames.jsonl','events.jsonl')},
            'rendered_video_sha256':sha(output)}
    provenance.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.video, args.run, args.output)))
