"""Parse both Test filename formats and Train's separate RGBDCows namespace."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from collections import Counter, defaultdict
import hashlib, json, re, zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
source = PROJECT / "cows2021_adaptation_20261027/delivery/results/archive_index_probe/entries.json"
assert hashlib.sha256(source.read_bytes()).hexdigest() == "ca182ffdfb8aaaa84207e976515ccc0d5cd351ed76004492fa97ba2e8a0cbe26"
entries = json.loads(source.read_text(encoding="utf-8"))
prefix = "4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/"
indexed = re.compile(r"image_(\d+)_(\d{4}-\d{2}-\d{2})_(\d+-\d+-\d+)_roi_(\d+)\.jpg$")
manual = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d+-\d+-\d+)_image_roi_(\d+)\.jpg$")
test, train, unknown = [], [], []
for entry in entries:
    member = entry["name"]
    if not member.startswith(prefix) or not member.endswith(".jpg"):
        continue
    relative = member[len(prefix):]
    parts = relative.split("/")
    name = parts[-1]
    if parts[0] == "Test":
        first, second = indexed.fullmatch(name), manual.fullmatch(name)
        if first:
            image_index, date, atime, roi = first.groups()
            style = "image_index_date_time_roi"
        elif second:
            date, atime, roi = second.groups()
            image_index = None
            style = "date_time_image_roi"
        else:
            unknown.append(entry)
            continue
        identity = parts[1]
        assert len(parts) == 3 and identity.isdigit()
        test.append({"publisher_identity": identity, "identity_namespace": "Cows2021_IdentificationTest:" + identity,
                     "date": date, "source_session_filename_key": date + "_" + atime,
                     "image_index_string": image_index, "ROI_string": roi, "filename_style": style,
                     "file_name": name, "archive_member": member, "zip_entry": entry})
    elif relative.startswith("Train/RGBDCows2020/Identification/RGB/"):
        assert len(parts) == 7 and parts[-3].isdigit()
        train.append({"publisher_identity": parts[-3], "identity_namespace": "RGBDCows2020_Train:" + parts[-3],
                      "publisher_subdirectory": parts[-2], "file_name": name, "archive_member": member,
                      "filename_date_unknown": True, "zip_entry": entry})
    else:
        unknown.append(entry)
assert not unknown and len(test) == 8670 and len(train) == 23350
ids = defaultdict(list)
for row in test:
    ids[row["publisher_identity"]].append(row)
by_id = {}
eligible = []
for identity, rows in sorted(ids.items()):
    dates = Counter(row["date"] for row in rows)
    sessions = defaultdict(list)
    for row in rows:
        sessions[row["source_session_filename_key"]].append(row["file_name"])
    by_id[identity] = {"images": len(rows), "dates": dict(sorted(dates.items())), "sessions": {key: len(value) for key, value in sessions.items()}}
    permitted_dates = sorted(date for date in dates if date < "2020-03-11")
    if len(permitted_dates) >= 2:
        eligible.append({"publisher_identity": identity, "dates": permitted_dates,
                         "earliest_date": permitted_dates[0], "latest_date": permitted_dates[-1],
                         "images_before_reserved_final_date": sum(dates[date] for date in permitted_dates)})
hash_groups = defaultdict(list)
for role, rows in [("Test", test), ("Train", train)]:
    for row in rows:
        hash_groups[(row["zip_entry"]["uncompressed_size"], row["zip_entry"]["CRC32"])].append({"role": role, "member": row["archive_member"], "identity_namespace": row["identity_namespace"]})
repeated = [{"bytes": key[0], "CRC32": key[1], "members": rows} for key, rows in hash_groups.items() if len(rows) > 1]
# Original local ZIP is only indexed, never decoded or unpickled here.
opencows_zip = Path(r"C:\Users\Donson\Downloads\10m32xl88x2b61zlkkgz3fml17.zip\10m32xl88x2b61zlkkgz3fml17.zip")
cross_crc = []
cross_names = []
local_entries = 0
local_images = 0
if opencows_zip.is_file():
    with zipfile.ZipFile(opencows_zip) as archive:
        infos = archive.infolist()
    local_entries = len(infos)
    signatures = defaultdict(list)
    by_name = defaultdict(list)
    for info in infos:
        if info.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            local_images += 1
            signatures[(info.file_size, info.CRC)].append(info.filename)
            by_name[PurePosixPath(info.filename).name].append(info.filename)
    for row in test:
        signature = (row["zip_entry"]["uncompressed_size"], row["zip_entry"]["CRC32"])
        if signature in signatures:
            cross_crc.append({"Cows2021_member": row["archive_member"], "OpenCows2020_members": signatures[signature]})
        if row["file_name"] in by_name:
            cross_names.append({"Cows2021_member": row["archive_member"], "OpenCows2020_members": by_name[row["file_name"]]})
text_members = [row for row in entries if row["name"].startswith(prefix) and row["name"].endswith((".json", ".csv", ".txt"))]
report = {"status": "ALL8670_TEST_AND23350_TRAIN_IDENTITY_JPEG_METADATA_PARSED_TWO_TEST_NAME_FORMATS",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "source_entries_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "test_images": len(test), "test_publisher_identities": len(ids),
          "test_filename_style_counts": dict(Counter(row["filename_style"] for row in test)),
          "test_date_counts": dict(sorted(Counter(row["date"] for row in test).items())),
          "test_by_identity": by_id, "eligible_cross_date_test_IDs": eligible,
          "train_images": len(train), "train_publisher_identities": len({row["publisher_identity"] for row in train}),
          "train_subdirectory_counts": dict(Counter(row["publisher_subdirectory"] for row in train)),
          "train_camera_dates_not_inferred_from_filename": True, "unparsed_JPEGs": len(unknown),
          "within_Train_Test_equal_size_CRC_candidates": repeated, "text_members": text_members,
          "local_OpenCows_ZIP_metadata_read": opencows_zip.is_file(), "local_OpenCows_ZIP": str(opencows_zip),
          "local_OpenCows_members": local_entries, "local_OpenCows_image_members": local_images,
          "Test_OpenCows_equal_size_CRC_candidates": cross_crc, "Test_OpenCows_same_filename_candidates": cross_names,
          "README_claimed_test_images": 13784, "actual_ZIP_test_JPEGs": 8670,
          "README_vs_actual_difference": 13784-len(test), "discrepancy_cause_not_assumed": True,
          "new_image_pixels_read": 0, "new_model_forwards": 0, "existing_final_holdout_opened": False,
          "physical_cross_dataset_ID_disjointness_proven": False, "whole_goal_complete": False}
for name, value in [("metadata_audit_v2.json", report), ("test8670_members.json", test), ("train23350_members.json", train)]:
    output = ROOT / "results" / name
    assert not output.exists()
    output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key in ["status", "test_images", "test_publisher_identities", "test_filename_style_counts", "test_date_counts", "train_images", "train_publisher_identities", "train_subdirectory_counts", "unparsed_JPEGs", "local_OpenCows_members", "local_OpenCows_image_members", "README_vs_actual_difference", "new_image_pixels_read"]}))
print(json.dumps({"eligible_cross_date_IDs": len(eligible), "within_train_test_CRC_candidates": len(repeated), "cross_OpenCows_CRC_candidates": len(cross_crc), "cross_OpenCows_filename_candidates": len(cross_names)}))
