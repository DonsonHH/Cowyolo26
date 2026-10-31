from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


meta = load(ROOT / "results/metadata_audit_v2.json")
links = load(ROOT / "results/source_relationship_audit.json")
verified = load(ROOT / "results/independent_verification.json")
assert meta["test_images"] == 8670 and meta["test_publisher_identities"] == 181 and meta["unparsed_JPEGs"] == 0
assert meta["train_images"] == 23350 and links["train_video_index_directories"] == 301 and links["train_tracklet_directories"] == 435
assert links["paper_test_count"] == 8670 and links["exact_original_frame_test_crop_links"] == 7931
assert links["test_crop_rows_with_no_candidate_detection_original"] == 723
assert verified["new_image_pixels_read"] == verified["new_model_forwards"] == 0
for row in load(ROOT / "results/primary_source_capture.json")["records"]:
    assert row["status"] == "PRIMARY_TEXT_CAPTURED" and sha(Path(row["file"])) == row["sha256"]
documents = [ROOT / "计划与验收.md", ROOT / "身份来源核查与跨日期评价准入.md"]
local = []
for document in documents:
    content = document.read_text(encoding="utf-8")
    assert "\ufffd" not in content
    for target in re.findall(r"\]\(([^)]+)\)", content):
        target = target.strip("<>")
        if not target.startswith(("http:", "https:")):
            path = (document.parent / unquote(target)).resolve()
            assert path.exists()
            local.append(str(path))
evidence = [path for name in ["tools", "results", "evidence"] for path in (ROOT / name).rglob("*") if path.is_file()]
result = {"status": "COWS2021_IDENTITY8670_TEST181_NONEMPTY_IDS301_TRAIN_VIDEO435_TRACKLET_METADATA_AND_SCOPE_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "test_JPEG_members": 8670, "nonempty_test_IDs": 181,
          "live_test_ID_directories": 182, "empty_publisher_ID179_JPEG_count": 0,
          "README13784_vs_paper8670_test_scope_resolved": True, "Test_filename_formats": 2,
          "train_JPEGs": 23350, "train_video_directories": 301, "train_tracklet_directories": 435,
          "train_directory_numbers_claimed_permanent_identity": False, "exact_crop_detection_source_links": 7931,
          "timestamp_only_candidate_links": 16, "unresolved_crop_original_links": 723,
          "cross_OpenCows_exact_filename_or_size_CRC_candidates": 0,
          "physical_cross_dataset_ID_disjointness_proven": False,
          "new_image_pixels_read": 0, "new_model_forwards": 0, "new_training_updates": 0,
          "reserved_date_pixels_opened": False, "current12_events_permanent_identity_GT_obtained": False,
          "next_cropped_identity_source_is_independent_full_pipeline_test": False,
          "documents": [{"path": str(path), "sha256": sha(path)} for path in documents],
          "evidence_hashes": {path.relative_to(ROOT).as_posix(): sha(path) for path in evidence},
          "local_links_checked": len(local), "assistant_self_review_not_independent_human": True, "whole_goal_complete": False}
output = ROOT / "results/final_review.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key not in ["evidence_hashes", "documents"]}))
