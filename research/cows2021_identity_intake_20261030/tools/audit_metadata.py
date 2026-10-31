from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from collections import Counter, defaultdict
import hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
source = PROJECT / "cows2021_adaptation_20261027/delivery/results/archive_index_probe/entries.json"
assert hashlib.sha256(source.read_bytes()).hexdigest() == "ca182ffdfb8aaaa84207e976515ccc0d5cd351ed76004492fa97ba2e8a0cbe26"
entries = json.loads(source.read_text(encoding="utf-8"))
assert len(entries) == 56858
prefix = "4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/"
rows, unmatched = [], []
pattern = re.compile(r"image_(\d+)_(\d{4}-\d{2}-\d{2})_(\d+-\d+-\d+)_roi_(\d+)\.jpg$")
for entry in entries:
    name = entry["name"]
    if name.startswith(prefix) and name.lower().endswith(".jpg"):
        relative = name[len(prefix):]
        match = pattern.fullmatch(PurePosixPath(name).name)
        parts = relative.split("/")
        if match is None:
            unmatched.append({"relative_file": relative, "zip_entry": entry})
            continue
        dataset_role = parts[0]
        identity = parts[-2]
        assert identity.isdigit()
        image_index, date, camera_time, roi = match.groups()
        rows.append({"dataset_role": dataset_role, "publisher_identity": identity,
                     "identity_namespace": "Cows2021_2020:" + identity, "date": date,
                     "source_session_filename_key": date + "_" + camera_time,
                     "image_index_string": image_index, "ROI_string": roi,
                     "archive_member": name, "file_name": PurePosixPath(name).name, "zip_entry": entry})
grouped = defaultdict(list)
for row in rows:
    grouped[row["dataset_role"]].append(row)
groups = {}
for role, group in grouped.items():
    ids = sorted({row["publisher_identity"] for row in group})
    by_id = {}
    for identity in ids:
        subset = [row for row in group if row["publisher_identity"] == identity]
        by_id[identity] = {"images": len(subset), "dates": dict(sorted(Counter(row["date"] for row in subset).items())),
                           "filename_session_keys": sorted({row["source_session_filename_key"] for row in subset})}
    groups[role] = {"parsed_images": len(group), "identities": len(ids), "date_counts": dict(sorted(Counter(row["date"] for row in group).items())),
                    "filename_session_keys": len({row["source_session_filename_key"] for row in group}), "by_identity": by_id,
                    "max_images_per_identity": max(value["images"] for value in by_id.values()),
                    "min_images_per_identity": min(value["images"] for value in by_id.values())}
crc_groups = defaultdict(list)
for row in rows:
    key = (row["zip_entry"]["uncompressed_size"], row["zip_entry"]["CRC32"])
    crc_groups[key].append(row)
duplicates = [{"bytes": key[0], "CRC32": key[1], "members": [row["archive_member"] for row in group],
               "roles": sorted({row["dataset_role"] for row in group}), "IDs": sorted({row["publisher_identity"] for row in group})}
              for key, group in crc_groups.items() if len(group) > 1]
test = grouped.get("Test", [])
test_by_id = defaultdict(list)
for row in test:
    test_by_id[row["publisher_identity"]].append(row)
eligible = []
for identity, group in sorted(test_by_id.items()):
    dates = sorted({row["date"] for row in group if row["date"] < "2020-03-11"})
    if len(dates) >= 2:
        eligible.append({"publisher_identity": identity, "dates_before_final_holdout": dates,
                         "images_before_final_holdout": sum(row["date"] < "2020-03-11" for row in group)})
texts = [row for row in entries if row["name"].startswith(prefix) and row["name"].endswith((".json", ".txt", ".csv"))]
other = Counter()
for entry in entries:
    if entry["name"].startswith(prefix) and not entry["directory"]:
        other[PurePosixPath(entry["name"]).suffix] += 1
result = {"status": "EXISTING_AUTHOR_ZIP_IDENTITY_MEMBER_METADATA_PARSED_NO_NEW_PIXELS",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "source_entries_file": str(source.resolve()),
          "source_entries_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "all_archive_entries": len(entries), "parsed_identity_JPEGs": len(rows), "unparsed_JPEGs": len(unmatched),
          "groups": groups, "other_member_extension_counts": dict(other),
          "identification_text_members": texts, "equal_size_CRC_candidate_groups": duplicates,
          "test_IDs_with_two_filename_dates_before_reserved2020_03_11": eligible,
          "ZIP_modification_date_not_used_as_camera_date": True,
          "cross_dataset_numeric_IDs_not_assumed_same_or_different_physical_animal": True,
          "new_image_pixels_read": 0, "new_model_forwards": 0, "existing_final_holdout_opened": False,
          "whole_goal_complete": False}
(ROOT / "results").mkdir(exist_ok=False)
for name, value in [("metadata_audit.json", result), ("identity_image_member_rows.json", rows), ("unparsed_member_rows.json", unmatched)]:
    (ROOT / "results" / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key in ["status", "all_archive_entries", "parsed_identity_JPEGs", "unparsed_JPEGs", "other_member_extension_counts", "new_image_pixels_read", "new_model_forwards"]}))
for name, group in groups.items():
    print(json.dumps({"role": name, **{key: value for key, value in group.items() if key != "by_identity"}}))
print(json.dumps({"CRC_candidate_groups": len(duplicates), "eligible_test_IDs": len(eligible), "text_members": [row["name"] for row in texts]}))
