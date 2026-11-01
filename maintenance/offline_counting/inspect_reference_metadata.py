"""Inspect a publisher ZIP-member manifest without reading images or running models."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def inspect_members(path):
    data = path.read_bytes()
    entries = json.loads(data.decode("utf-8"))
    names = [row["name"] for row in entries]
    prefixes = [name[:name.index("/Sub-levels/")] for name in names if "/Sub-levels/" in name]
    if not prefixes or len(set(prefixes)) != 1:
        raise ValueError("Expected one Cows2021 publisher archive root")
    prefix = prefixes[0] + "/Sub-levels/Identification/"
    videos = [name for name in names if name.startswith(prefix + "Videos/") and name.lower().endswith(".avi")]
    crops = [name for name in names if name.startswith(prefix + "Train/") and name.lower().endswith(".jpg")]
    traces = [name for name in names if Path(name).suffix.lower() in (".csv", ".json", ".txt", ".pkl", ".pickle", ".npy", ".npz")]
    pattern = re.compile(r"/RGB/(?P<video>\d+)/(?P<track>\d+)/r_(?P<sample>\d+)_(?P<instance>\d+)_"
                         r"(?P<augment>[0-4])(?P<kind>[A-Za-z]+)_(?P<x>\d+)_(?P<y>\d+)_"
                         r"(?P<angle>-?\d+(?:\.\d+)?)\.jpg$")
    parsed = [pattern.search(name) for name in crops]
    if not all(parsed):
        raise ValueError("Unknown crop filename format; do not silently infer a video mapping")
    groups = {(m['video'], m['track']) for m in parsed}
    unique_centers = {(m['video'], m['track'], m['sample'], m['x'], m['y']) for m in parsed}
    date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}")
    dates = [date_pattern.search(name) for name in videos]
    if not all(dates):
        raise ValueError("A raw video date could not be parsed")
    return {
        "status": "METADATA_ONLY_REFERENCE_READINESS_CHECK",
        "source_manifest_sha256": hashlib.sha256(data).hexdigest(),
        "archive_entries": len(names), "raw_videos": len(videos),
        "raw_video_dates": dict(sorted(Counter(m[0] for m in dates).items())),
        "identity_crop_JPEGs": len(crops), "numeric_video_folders": len({m['video'] for m in parsed}),
        "crop_tracklet_folders": len(groups), "unique_sample_frame_and_center_records": len(unique_centers),
        "crop_filename_augmentation_ids": sorted({m['augment'] for m in parsed}),
        "crop_filename_kind_counts": dict(sorted(Counter(m['kind'] for m in parsed).items())),
        "numeric_video_folder_range": [min(int(m['video']) for m in parsed), max(int(m['video']) for m in parsed)],
        "CSV_members": [name for name in names if name.lower().endswith(".csv")],
        "inspected_text_or_array_metadata_members": traces,
        "sample_raw_members": videos[:2], "sample_crop_members": crops[:2],
        "crop_numeric_index_to_raw_video_mapping_supplied_by_this_audit": False,
        "crop_sample_index_to_source_frame_or_PTS_verified": False,
        "complete_passage_reference_created": False,
        "publisher_identity_tracklet_integrity_is_not_full_passage_coverage_proof": True,
        "new_video_or_image_pixels_read": 0, "new_model_forwards": 0,
        "training_or_development_overlap_verified": False,
        "limitation": "A numeric crop-folder ID cannot be assigned to a dated raw video by assuming matching directory order. Retained crop centers do not prove every full passage is included.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = inspect_members(args.entries)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("archive_entries", "raw_videos", "raw_video_dates",
                      "identity_crop_JPEGs", "crop_tracklet_folders", "unique_sample_frame_and_center_records", "CSV_members")}))
