from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from collections import Counter, defaultdict
import hashlib, json, re, urllib.request, zlib

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


test = load(ROOT / "results/test8670_members.json")
train = load(ROOT / "results/train23350_members.json")
metadata = load(ROOT / "results/metadata_audit_v2.json")
split_file = ROOT / "evidence/primary_texts/identity_train_split.response"
raw = split_file.read_bytes()
entry = metadata["text_members"][0]
assert len(raw) == entry["uncompressed_size"] and zlib.crc32(raw) & 0xffffffff == entry["CRC32"]
split = json.loads(raw)
split_rows = []
for video_index, tracklets in split.items():
    for tracklet, roles in tracklets.items():
        for role, files in roles.items():
            assert role in ["train", "valid", "test"]
            for name in files:
                split_rows.append({"video_index_directory": video_index, "tracklet_directory": tracklet, "split_role": role, "file_name": name})
split_keys = [(row["video_index_directory"], row["tracklet_directory"], row["file_name"]) for row in split_rows]
train_keys = [(PurePosixPath(row["archive_member"]).parts[-3], PurePosixPath(row["archive_member"]).parts[-2], row["file_name"]) for row in train]
assert len(set(split_keys)) == len(split_keys) and len(set(train_keys)) == len(train_keys)
assert set(split_keys) == set(train_keys)
source = load(PROJECT / "cows2021_labels_20261027/results/source_metadata_all.json")
roles = load(PROJECT / "cows2021_labels_20261027/results/date_roles_v1/manifest.json")
assert len(source) == len(roles) == 10402
source_by_original = defaultdict(list)
source_by_timestamp = defaultdict(list)
role_by_name = {row["file_name"]: row["candidate_date_role"] for row in roles}
for row in source:
    source_by_original[row["original_filename"]].append(row)
    source_by_timestamp[row["capture_timestamp"]].append(row)
links = []
for row in test:
    name = row["file_name"]
    if row["image_index_string"] is not None:
        original = name.rsplit("_roi_", 1)[0]
        candidates = source_by_original[original]
        method = "exact_original_frame_filename"
    else:
        hour, minute, second = row["source_session_filename_key"].split("_", 1)[1].split("-")
        timestamp = f"{row['date']}T{int(hour):02}:{int(minute):02}:{int(second):02}"
        candidates = source_by_timestamp[timestamp]
        method = "timestamp_only_original_frame_unresolved"
    links.append({"identity_test_member": row["archive_member"], "publisher_identity": row["publisher_identity"],
                  "method": method, "source_candidates": [{"detection_file": candidate["file_name"], "published_detection_role": candidate["role"],
                                                             "current_project_date_role": role_by_name[candidate["file_name"]],
                                                             "original_filename": candidate["original_filename"]} for candidate in candidates]})
live = set(re.findall(r'href="(\d{3})/"', (ROOT / "evidence/primary_texts/identity_test_root.response").read_text()))
zip_ids = {row["publisher_identity"] for row in test}
assert live - zip_ids == {"179"} and not zip_ids - live
url = "https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/Test/179/"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
with opener.open(url, timeout=20) as response:
    directory_raw = response.read()
dest = ROOT / "evidence/primary_texts/identity_test179.response"
assert not dest.exists()
dest.write_bytes(directory_raw)
jpegs179 = re.findall(r'href="([^"<>]+\.(?:jpg|jpeg))"', directory_raw.decode(), re.I)
assert not jpegs179
paper_raw = (ROOT / "evidence/primary_texts/author_paper_HTML.response").read_text()
assert "8,670" in paper_raw and "13,784" in paper_raw
report = {"status": "AUTHOR_PAPER_RESOLVES8670_TEST_SCOPE_TRAIN_TRACKLET_SPLIT_AND_DETECTION_SOURCE_LINKS_AUDITED",
          "created_UTC": datetime.now(timezone.utc).isoformat(),
          "paper_scope": "13784 total detected identity-assigned crops,8670 cross-day test instances; README test13784 is broader than actual test release",
          "paper_test_count": 8670, "actual_test_JPEGs": len(test), "live_test_ID_directories": len(live),
          "nonempty_ZIP_test_IDs": len(zip_ids), "empty_test179_directory_independently_fetched": True, "test179_JPEG_links": jpegs179,
          "paper182IDs_vs181_nonempty_is_directory179_without_released_JPEG": True,
          "train_split_rows": len(split_rows), "train_split_counts": dict(Counter(row["split_role"] for row in split_rows)),
          "train_video_index_directories": len(split), "train_tracklet_directories": sum(len(value) for value in split.values()),
          "train_folder_numbers_are_not_verified_permanent_cow_IDs": True,
          "exact_original_frame_test_crop_links": sum(row["method"] == "exact_original_frame_filename" and len(row["source_candidates"]) == 1 for row in links),
          "timestamp_only_rows_with_candidate_originals": sum(row["method"] != "exact_original_frame_filename" and bool(row["source_candidates"]) for row in links),
          "test_crop_rows_with_no_candidate_detection_original": sum(not row["source_candidates"] for row in links),
          "exact_links_to_project_date_roles": dict(Counter(row["source_candidates"][0]["current_project_date_role"] for row in links if row["method"] == "exact_original_frame_filename" and len(row["source_candidates"]) == 1)),
          "identity_crop_study_does_not_establish_independent_detector_or_full_pipeline_test": True,
          "current_encoder_training_source": "MultiCam2023 photos; no Cows2021 gradients in frozen encoder provenance, no verified physical cross-dataset ID map",
          "cross_dataset_physical_identity_disjointness_claimed": False,
          "all8670_test_filename_dates_before_2020_03_08": all(row["date"] < "2020-03-08" for row in test),
          "new_image_pixels_read": 0, "new_model_forwards": 0, "final_reserved_date_pixels_opened": False,
          "evidence_hashes": {"split_text": sha(split_file), "paper_HTML": sha(ROOT / "evidence/primary_texts/author_paper_HTML.response"),
                              "live179_directory": sha(dest), "detection_source_XML_metadata": sha(PROJECT / "cows2021_labels_20261027/results/source_metadata_all.json"),
                              "detection_date_roles": sha(PROJECT / "cows2021_labels_20261027/results/date_roles_v1/manifest.json")},
          "whole_goal_complete": False}
for name, value in [("source_relationship_audit.json", report), ("train_split23350_rows.json", split_rows), ("test_crop_detection_source_links.json", links)]:
    output = ROOT / "results" / name
    assert not output.exists()
    output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key not in ["evidence_hashes"]}))
