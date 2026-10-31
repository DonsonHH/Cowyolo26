from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import zlib
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


metadata = load(ROOT / "results/COLO_zip_metadata_recovered_v2.json")
assert metadata["entries"] == 6023 and metadata["local_image_pixels_decoded"] == 0
assert len(metadata["json_files"]) == 22
for row in metadata["json_files"]:
    assert sha(Path(row["file"])) == row["sha256"]
test_row = next(row for row in metadata["json_files"] if row["archive_member"] == "COLO_COCO/1_top/test/data.json")
test = load(Path(test_row["file"]))
assert len(test["images"]) == 50 and len(test["annotations"]) == 451
assert len({row["id"] for row in test["images"]}) == 50
by_id = {row["id"]: row for row in test["images"]}
invalid, outside, overshoots = [], [], []
for row in test["annotations"]:
    x, y, width, height = row["bbox"]
    image = by_id[row["image_id"]]
    if min(width, height) <= 0:
        invalid.append(row)
    elif min(x, y) < -.01 or x + width > image["width"] + .01 or y + height > image["height"] + .01:
        outside.append(row)
        overshoots.append(max(0, -x, -y, x + width - image["width"], y + height - image["height"]))
assert len(invalid) == 1 and invalid[0]["id"] == 127 and invalid[0]["image_id"] == 20154
assert len(outside) == 15 and max(overshoots) < .25
visual = load(ROOT / "results/COLO_train8_visual_review.json")
assert visual["actually_viewed"] and visual["source_images"] == 8 and visual["publisher_boxes"] == 66
assert visual["new_model_forwards"] == 0 and visual["test50_pixels_requested"] is False
for row in visual["files"]:
    assert row["actually_viewed"] and sha(Path(row["file"])) == row["sha256"]
for relative, digest in visual["evidence_hashes"].items():
    assert sha(ROOT / relative) == digest
audit = load(ROOT / "results/COLO_annotation_audit.json")
assert audit["canonical_top_images"] == 504 and audit["canonical_top_boxes"] == 3950
assert audit["train_test_same_filename_overlap"] == 0
assert audit["contains_track_ID_or_permanent_cow_identity_or_video_times"] is False
documents = [ROOT / "计划与验收.md", ROOT / "公开俯视数据来源与准入结论.md"]
links = []
for document in documents:
    for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
        target = target.strip("<>")
        if not target.startswith(("http:", "https:")):
            path = (document.parent / unquote(target)).resolve()
            assert path.exists(), path
            links.append(str(path))
evidence = [str(path.relative_to(ROOT)).replace("\\", "/") for directory in ["results", "tools", "protocol"]
            for path in (ROOT / directory).rglob("*") if path.is_file() and path.suffix in [".py", ".sh", ".json"]]
result = {"status": "THREE_PUBLIC_SOURCE_INTAKES22_COLO_JSON504_TOP_IMAGES_AND8_TRAIN_PIXEL_QA_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(),
          "COLO_annotation_JSONs": 22, "unique_top_images": 504, "publisher_top_test_images": 50,
          "publisher_top_test_original_boxes": 451, "zero_width_test_boxes": 1,
          "positive_area_small_outside_test_boxes": 15, "maximum_outside_px": max(overshoots),
          "train_QA_images_actually_viewed": 8, "train_QA_panels": 16,
          "test50_pixels_requested": False, "new_model_forwards": 0, "new_training_updates": 0,
          "new_independent_passage_or_identity_GT_obtained": False,
          "AutoCattlogger_sample_videos_obtained": False, "CattleEyeView_data_obtained": False,
          "forms_submitted_or_messages_sent": False, "global_proxy_or_node_configuration_changed": False,
          "quantitative_model_evaluation_not_yet_admitted": True,
          "assistant_self_review_not_independent_human_relabeling": True,
          "documents": [{"path": str(path), "sha256": sha(path)} for path in documents],
          "local_links_checked": len(links),
          "evidence_hashes": {relative: sha(ROOT / relative) for relative in evidence},
          "whole_goal_complete": False}
target = ROOT / "results/final_review.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "zero_width_test_boxes", "positive_area_small_outside_test_boxes", "maximum_outside_px", "new_model_forwards"]}))
