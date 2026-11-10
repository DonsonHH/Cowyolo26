"""Offline evidence for this immutable failed case and the user's14–95s window.

Historical10/ID4 assertions identify recorded evidence, never alter production
counts. This script contains no model inference and creates no human event GT.
"""
from pathlib import Path
from datetime import datetime, timezone
import collections
import hashlib
import json
import subprocess
import sys
import cv2
import numpy as np

ROOT = Path(__file__).parent
REPO = Path(r"C:\Users\Donson\Documents\Codex\exports\Cowyolo26-20261031\repo")
sys.path.insert(0, str(REPO))
from counting.channel import ChannelPolygon
from counting.protocol import gate_from_config
from counting.render import draw_channel

M = REPO / "maintenance/offline_counting"
RUN = ROOT / "camera2_v4_board_result"
SOURCE = ROOT / "camera2_inputs/camera2_aug19_120s_native.mp4"
summary = json.loads((RUN / "summary.json").read_text())
freeze = json.loads((M / "CAMERA2_V4_FREEZE.json").read_text())
reference = json.loads((M / "results/camera2_v4_user_reference.json").read_text())
assert summary["status"] == "COMPLETED_UNSCORED"
assert summary["video_sha256"] == hashlib.sha256(SOURCE.read_bytes()).hexdigest() == reference["video_sha256"]
assert summary["config"] == freeze["config"]
assert gate_from_config(summary["config"]) == reference["review_gate"]
assert summary["decoded_frames"] == 2993 and summary["model_forwards"] == summary["processed_frames"] == 599
assert summary["wall_clock_skipped_frames"] == 0
rows = [json.loads(x) for x in (RUN / "frames.jsonl").read_text().splitlines()]
events = [json.loads(x) for x in (RUN / "events.jsonl").read_text().splitlines() if x.strip()]
uncertain = [json.loads(x) for x in (RUN / "uncertain.jsonl").read_text().splitlines() if x.strip()]
assert len(rows) == 599 and len(events) == 10
assert all(r["run_id"] == summary["run_id"] for r in rows + events + uncertain)
assert all(b["time_s"] > a["time_s"] and b["frame0"] > a["frame0"] for a, b in zip(rows, rows[1:]))
selected = [e for e in events if e["entry_time_s"] >= 14 and e["time_s"] < 95]
assert len(selected) == len(events)
polygon = ChannelPolygon(summary["config"]["channel_polygon"])
by_frame = {row["frame0"]: row for row in rows}
for event in events:
    assert event["direction"] == "B->A"
    for frame0 in (event["entry_frame0"], event["frame0"]):
        track = next(t for t in by_frame[frame0]["tracks"] if t["track_id"] == event["track_id"])
        box = track["xyxy"]
        assert polygon.contains((box[0] + box[2]) / 5120, (box[1] + box[3]) / 2880)
missed = next(x for x in uncertain if x["track_id"] == "0:4")
trace = []
streak, maximum_A_streak = 0, 0
for row in rows:
    track = next((t for t in row["tracks"] if t["track_id"] == "0:4"), None)
    if track is None:
        streak = 0
        continue
    box = track["xyxy"]
    y = (box[1] + box[3]) / 2880
    zone = "A" if y < .4 else "B" if y > .6 else "middle"
    streak = streak + 1 if zone == "A" else 0
    maximum_A_streak = max(maximum_A_streak, streak)
    trace.append({"frame0": row["frame0"], "source_time_s": row["time_s"], "xyxy": box,
                  "confidence": track["confidence"], "zone": zone, "center_y": y})
assert maximum_A_streak == 1
source_pts = json.loads((ROOT / "camera2_inputs/camera2_aug19_source_pts.json").read_text())
out = ROOT / "camera2_v4_count10_14s95s_review.mp4"
assert not out.exists()
cap = cv2.VideoCapture(str(SOURCE))
fps = cap.get(5)
encoder = subprocess.Popen(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
    "-pixel_format", "bgr24", "-video_size", "960x540", "-framerate", str(fps), "-i", "pipe:0", "-an",
    "-c:v", "libx264", "-threads", "2", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
frame0, observation, row_index, rendered, actual_frames = 0, None, 0, 0, []
panel_targets = {780, 800, 810, 835, 840, 850, 855, 860, 875}
panels = []
try:
    while frame0 < len(source_pts):
        ok, image = cap.read()
        assert ok
        time_s = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        while row_index < len(rows) and rows[row_index]["frame0"] <= frame0:
            observation = rows[row_index]
            row_index += 1
        if time_s >= 95:
            break
        if time_s >= 14:
            tile = cv2.resize(image, (960, 540))
            draw_channel(tile, summary["config"])
            if observation and 0 <= time_s - observation["time_s"] <= .22:
                for track in observation["tracks"]:
                    x1, y1, x2, y2 = track["xyxy"]
                    a, b = (round(x1 * 960 / 2560), round(y1 * 540 / 1440)), (round(x2 * 960 / 2560), round(y2 * 540 / 1440))
                    cv2.rectangle(tile, a, b, (90, 235, 120), 2)
                    cv2.putText(tile, track["track_id"], (a[0], max(45, a[1] - 4)), cv2.FONT_HERSHEY_SIMPLEX, .45, (90, 235, 120), 1)
            up = sum(e["time_s"] <= time_s and e["direction"] == "B->A" for e in selected)
            down = sum(e["time_s"] <= time_s and e["direction"] == "A->B" for e in selected)
            cv2.rectangle(tile, (0, 0), (959, 28), (20, 29, 40), -1)
            cv2.putText(tile, f"source {time_s:.3f}s f{frame0} | UP {up} DOWN {down} | held boxes, no new inference", (7, 20), cv2.FONT_HERSHEY_SIMPLEX, .46, (245, 245, 245), 1)
            encoder.stdin.write(tile.tobytes())
            actual_frames.append(frame0)
            rendered += 1
            if frame0 in panel_targets:
                roi = image[140:1370, 400:1100].copy()
                if frame0 in by_frame:
                    for track in by_frame[frame0]["tracks"]:
                        if track["track_id"] != "0:4":
                            continue
                        x1, y1, x2, y2 = track["xyxy"]
                        cv2.rectangle(roi, (round(x1 - 400), round(y1 - 140)), (round(x2 - 400), round(y2 - 140)), (90, 235, 120), 3)
                cv2.line(roi, (200, 0), (200, roi.shape[0] - 1), (255, 200, 0), 2)
                crop = cv2.resize(roi, (240, 420))
                caption = np.full((35, 240, 3), 20, np.uint8)
                cv2.putText(caption, f"f{frame0} t{time_s:.2f}s", (5, 22), cv2.FONT_HERSHEY_SIMPLEX, .48, (245, 245, 245), 1)
                panels.append(np.concatenate([crop, caption], axis=0))
        frame0 += 1
finally:
    cap.release()
    encoder.stdin.close()
assert encoder.wait() == 0
cap = cv2.VideoCapture(str(out))
verified = 0
while True:
    ok, image = cap.read()
    if not ok:
        break
    verified += 1
cap.release()
assert verified == rendered == len(actual_frames)
assert len(panels) == 9
sheet = np.concatenate([np.concatenate(panels[i:i + 3], axis=1) for i in range(0, 9, 3)], axis=0)
ok, buffer = cv2.imencode(".jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 91])
assert ok
(M / "results/camera2_v4_left_cow_gap_panel.jpg").write_bytes(buffer.tobytes())
report = {"status": "COMPLETED_BOARD_EXECUTION_UPWARD_COUNT_MISMATCH", "user_confirmed_UP": 11,
          "actual_UP": summary["counts"]["IN"], "actual_DOWN": summary["counts"]["OUT"], "UP_absolute_count_error": 1,
          "original_board_decoded_frames": 2993, "original_board_model_forwards": 599,
          "original_full_board_elapsed_s": summary["overall_elapsed_s"],
          "user_presentation_source_time_window_s": [14, 95], "presentation_frame0_interval": [actual_frames[0], actual_frames[-1]],
          "rendered_frames": rendered, "all_rendered_frames_decoded": verified,
          "cropped_review_file": str(out), "cropped_review_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
          "new_model_forwards_for_window_and_diagnosis": 0,
          "uncertain_track": missed, "uncounted_track_observations": trace, "maximum_consecutive_A_observations": maximum_A_streak,
          "root_cause_limit": "The immediate counting reason is insufficient confirmed A observations; detector confidence, crop context, overlap and sampling remain to be distinguished.",
          "formal_timed_event_precision_recall_f1": None,
          "recorded_UTC": datetime.now(timezone.utc).isoformat()}
(M / "results/camera2_v4_verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for name in ("summary.json", "events.jsonl", "frames.jsonl", "uncertain.jsonl", "transform.json", "batch_status.json", "board_run.log"):
    source = RUN / name
    if source.exists():
        (M / "results" / ("camera2_v4_" + name)).write_bytes(source.read_bytes())
print(json.dumps({k: report[k] for k in ("actual_UP", "user_confirmed_UP", "presentation_frame0_interval", "rendered_frames", "cropped_review_file", "maximum_consecutive_A_observations")}))
