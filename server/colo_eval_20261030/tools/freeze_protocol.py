from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
SOURCE = PROJECT / "external_sources_20261030"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


intake = load(SOURCE / "results/final_review.json")
assert intake["test50_pixels_requested"] is False
metadata = load(SOURCE / "results/COLO_zip_metadata_recovered_v2.json")
gt_record = next(row for row in metadata["json_files"] if row["archive_member"] == "COLO_COCO/1_top/test/data.json")
original = load(Path(gt_record["file"]))
assert sha(Path(gt_record["file"])) == gt_record["sha256"]
audit = load(SOURCE / "results/COLO_annotation_audit.json")
lighting = {row["file_name"]: row["lighting"] for row in audit["official_test_rows"]}
raw_entries = json.loads((SOURCE / "evidence/COLO_zip_metadata_v2/entries.json").read_text(encoding="utf-8"))
entries = {row["name"]: row for row in raw_entries}
images = []
for image in sorted(original["images"], key=lambda row: Path(row["file_name"]).name):
    name = Path(image["file_name"]).name
    member = "COLO_COCO/1_top/test/" + name
    images.append({"image": image, "file_name": name, "lighting": lighting[name],
                   "archive_member": member, "zip_entry": entries[member]})
assert len(images) == 50 and all(row["image"]["width"] == row["image"]["height"] == 640 for row in images)
quarantine = [row for row in original["annotations"] if min(row["bbox"][2:]) <= 0]
assert [row["id"] for row in quarantine] == [127]
valid = [row for row in original["annotations"] if row["id"] != 127]
unclipped = copy.deepcopy(original)
unclipped["annotations"] = copy.deepcopy(valid)
clipped = copy.deepcopy(unclipped)
changes = []
for row in clipped["annotations"]:
    x, y, width, height = row["bbox"]
    x1, y1 = max(0., min(640., x)), max(0., min(640., y))
    x2, y2 = max(0., min(640., x + width)), max(0., min(640., y + height))
    box = [x1, y1, x2 - x1, y2 - y1]
    assert min(box[2:]) > 0
    changes.append({"annotation_id": row["id"], "original_bbox": row["bbox"], "clipped_bbox": box,
                    "changed": box != row["bbox"]})
    row["bbox"] = box
    row["area"] = box[2] * box[3]

package_data = load(ROOT / "evidence/pycocotools_PyPI.json")
wheel = next(row for row in package_data["urls"] if "-cp312-abi3-" in row["filename"] and "manylinux2014_x86_64" in row["filename"])
dest = ROOT / "input"
dest.mkdir(exist_ok=False)
wheel_path = dest / wheel["filename"]
opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
with opener.open(wheel["url"], timeout=25) as response:
    payload = response.read()
assert len(payload) == wheel["size"] and hashlib.sha256(payload).hexdigest() == wheel["digests"]["sha256"]
wheel_path.write_bytes(payload)
for name, value in [("GT_original451.json", original), ("GT_valid450_unclipped.json", unclipped),
                    ("GT_valid450_clipped.json", clipped), ("GT_quarantine_and_transform.json", {"quarantined": quarantine, "valid450_transforms": changes})]:
    (dest / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
models = [{"name": "official", "relative_checkpoint": "models/yolo26n.pt",
           "sha256": "9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef", "cow_class": 19},
          {"name": "old_rot192", "relative_checkpoint": "detector_factorial_20261029/results/training/S192_rot90_seed26/weights/last.pt",
           "sha256": "7b01cead4841f17d561f2a6bd768f9b229f1b3bd142818d8302135d3c69ffd45", "cow_class": 0},
          {"name": "new_mosaic050", "relative_checkpoint": "mosaic_pair_20261030/results/training/mosaic050_seed26/weights/last.pt",
           "sha256": "628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb", "cow_class": 0}]
protocol = {"status": "FROZEN_BEFORE_FIRST_COLO_TEST50_IMAGE_REQUEST_OR_MODEL_FORWARD",
            "created_UTC": datetime.now(timezone.utc).isoformat(), "models": models, "sizes": [192, 256, 320],
            "source_release_asset": {"URL": metadata["requested_public_URL"], "bytes": metadata["asset_bytes"], "asset_id": metadata["asset_id"]},
            "source_intake_review_sha256": sha(SOURCE / "results/final_review.json"),
            "source_GT_sha256": gt_record["sha256"], "images": images,
            "test_images": 50, "original_annotations": 451, "valid_annotations": 450,
            "quarantined_annotation_ids": [127], "GT_policy": "positive450 clipped to640 with recomputed area; keep original451 and unmodified-positive450 sensitivity", 
            "preprocessing": "PIL RGB decode, cv2.INTER_LINEAR resize square, CHW float32 divided by255; no crop rotate enhancement or TTA",
            "inference": "Torch CPU eval direct network end-to-end300x6 raw, no fuse call, no NMS, no warmup; batch10",
            "expected_source_image_forwards": 450, "expected_network_forward_calls": 45, "warmup_forwards": 0,
            "COCO_score_threshold": .001, "COCO_iou_thresholds": [.5, .55, .6, .65, .7, .75, .8, .85, .9, .95],
            "COCO_maxDets": [1, 10, 100], "COCO_recall_points": 101,
            "fixed_score_threshold": .20, "fixed_IoU_threshold": .50,
            "fixed_matching": "per image confidence-descending stable raw order; highest IoU unmatched GT, tie lower annotationID; all up to300 cow predictions",
            "qualitative_image_indices_preselected": [0, 10, 20, 30, 40, 49],
            "evaluation_library": {"name": "pycocotools", "version": package_data["info"]["version"], "wheel": wheel_path.name,
                                   "sha256": sha(wheel_path), "ABI": "cp312-abi3 valid for conventional CPython3.13; not cp313t"},
            "input_file_hashes": {path.name: sha(path) for path in dest.iterdir() if path.is_file()},
            "plan_sha256": sha(ROOT / "计划与验收.md"),
            "training_or_threshold_search_allowed": False, "existing_final_holdout_opened": False,
            "new_board_forwards": 0, "whole_goal_complete": False}
output = ROOT / "protocol/run_v1.json"
output.parent.mkdir(exist_ok=False)
output.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"protocol_sha256": sha(output), "images": 50, "valid_GT": 450, "models": 3, "sizes": 3,
                  "planned_source_forwards": 450, "package_wheel": wheel_path.name, "test_pixels_opened_at_freeze": 0}))
