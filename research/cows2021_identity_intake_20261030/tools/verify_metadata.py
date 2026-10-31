from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from collections import Counter, defaultdict
import hashlib, json, re, zlib

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


entries_file = PROJECT / "cows2021_adaptation_20261027/delivery/results/archive_index_probe/entries.json"
entries = load(entries_file)
report = load(ROOT / "results/metadata_audit_v2.json")
rows = load(ROOT / "results/test8670_members.json")
catalog = {row["name"]: row for row in entries}
by_id, dates, formats = Counter(), Counter(), Counter()
for row in rows:
    member = row["archive_member"]
    assert catalog[member] == row["zip_entry"]
    parts = PurePosixPath(member).parts
    assert parts[-2] == row["publisher_identity"] and parts[-1] == row["file_name"]
    tokens = row["file_name"].removesuffix(".jpg").split("_")
    if tokens[0] == "image":
        assert tokens[4] == "roi" and len(tokens) == 6 and tokens[1].isdigit()
        date, atime, style = tokens[2], tokens[3], "image_index_date_time_roi"
    else:
        assert tokens[2:4] == ["image", "roi"] and len(tokens) == 5
        date, atime, style = tokens[0], tokens[1], "date_time_image_roi"
    datetime.strptime(date, "%Y-%m-%d")
    hour, minute, second = map(int, atime.split("-"))
    assert 0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60
    assert row["date"] == date and row["source_session_filename_key"] == date + "_" + atime
    by_id[row["publisher_identity"]] += 1
    dates[date] += 1
    formats[style] += 1
assert len(rows) == len({row["archive_member"] for row in rows}) == 8670
assert len(by_id) == 181 and dict(dates) == report["test_date_counts"] and dict(formats) == report["test_filename_style_counts"]
for identity, count in by_id.items():
    assert report["test_by_identity"][identity]["images"] == count
split_file = ROOT / "evidence/primary_texts/identity_train_split.response"
split_raw = split_file.read_bytes()
entry = report["text_members"][0]
assert zlib.crc32(split_raw) & 0xffffffff == entry["CRC32"] and len(split_raw) == entry["uncompressed_size"]
primary = load(ROOT / "results/primary_source_capture.json")
for row in primary["records"]:
    assert row["status"] == "PRIMARY_TEXT_CAPTURED"
    assert hashlib.sha256(Path(row["file"]).read_bytes()).hexdigest() == row["sha256"]
relationships = load(ROOT / "results/source_relationship_audit.json")
links = load(ROOT / "results/test_crop_detection_source_links.json")
assert len(links) == 8670
assert sum(row["method"] == "exact_original_frame_filename" and len(row["source_candidates"]) == 1 for row in links) == 7931
assert relationships["train_tracklet_directories"] == 435 and relationships["train_video_index_directories"] == 301
result = {"status": "BOTH_TEST_FILENAME_FORMATS8670_MEMBERS181_IDS27_DATES_AND_AUTHOR_TEXTS_INDEPENDENTLY_VERIFIED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "test_members": 8670, "nonempty_test_IDs": 181,
          "test_dates": len(dates), "exact_detection_source_links": 7931,
          "author_train_tracklets": 435, "author_train_video_directories": 301,
          "new_image_pixels_read": 0, "new_model_forwards": 0, "whole_goal_complete": False}
output = ROOT / "results/independent_verification.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
