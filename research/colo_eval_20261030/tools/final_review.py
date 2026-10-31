from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


plan = load(ROOT / "protocol/run_v1.json")
summary = load(ROOT / "delivery/results/evaluation/summary.json")
verification = load(ROOT / "results/independent_verification.json")
assert verification["raw_model_image_forwards_checked"] == 450
assert verification["COCO_metric_groups_rerun"] == 72 and verification["maximum_COCO_array_difference"] == 0
assert summary["actual_source_image_forwards"] == 450 and summary["actual_network_forward_calls"] == 45
assert summary["Slurm_job_id"] == "130734" and summary["new_training_updates"] == 0 and summary["new_board_forwards"] == 0
assert "130734|cow-colo-fixed9|COMPLETED|0:0|" in (ROOT / "delivery/logs/sacct-130734.txt").read_text(encoding="utf-8")
assert not (ROOT / "delivery/logs/evaluation-130734.err").read_text(encoding="utf-8").strip()
transfer = load(ROOT / "evidence/result_transfer.json")
archive = ROOT / "colo_delivery_130734.tar.gz"
assert archive.stat().st_size == transfer["bytes"] == 3485997 and sha(archive) == transfer["sha256"]
for row in load(ROOT / "delivery/result_manifest.json"):
    assert sha(ROOT / "delivery" / row["file"]) == row["sha256"]
visual = load(ROOT / "results/visual_review.json")
assert visual["actually_viewed"] and visual["panels"] == 66
for row in visual["files"]:
    assert row["actually_viewed"] and sha(Path(row["file"])) == row["sha256"]
main = [row for row in summary["metrics"] if row["lighting"] == "all" and row["GT_policy"] == "clipped"]
assert len(main) == 9 and all(row["references"] == 450 and row["images"] == 50 for row in main)
assert [[row["fixed_all_images"][key] for key in ["TP", "FP", "FN"]] for row in main] == [
    [7, 2, 443], [31, 9, 419], [63, 10, 387], [92, 21, 358], [116, 38, 334], [136, 45, 314],
    [86, 5, 364], [102, 12, 348], [137, 31, 313]]
sensitivity = []
for row in summary["metrics"]:
    if row["GT_policy"] == "clipped":
        other = next(item for item in summary["metrics"] if item["condition"] == row["condition"] and item["lighting"] == row["lighting"] and item["GT_policy"] == "unclipped")
        sensitivity.extend(abs(left - right) for left, right in zip(row["all12_COCO_stats"], other["all12_COCO_stats"]))
assert max(sensitivity) == 0
documents = [ROOT / "计划与验收.md", ROOT / "COLO三模型三尺寸外来源检测与下一步.md"]
links = []
for document in documents:
    for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
        target = target.strip("<>")
        if not target.startswith(("http:", "https:")):
            path = (document.parent / unquote(target)).resolve()
            assert path.exists(), path
            links.append(str(path))
evidence = [str(path.relative_to(ROOT)).replace("\\", "/") for directory in ["results", "tools", "protocol", "evidence"]
            for path in (ROOT / directory).rglob("*") if path.is_file() and path.suffix in [".py", ".sh", ".json", ".txt", ".npz"]]
result = {"status": "COLO50_TEST_IMAGES9_FIXED_CONDITIONS450_CPU_FORWARDS72_COCO_RERUNS_AND66_PANELS_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "Slurm_job130734_completed0_0": True,
          "test_images": 50, "original_GT_boxes": 451, "valid_GT_boxes": 450, "quarantined_zero_area_annotation_ID": 127,
          "fixed_model_size_conditions": 9, "actual_source_image_forwards": 450, "actual_network_calls": 45, "warmup_forwards": 0,
          "all_raw_frozen_before_scoring": True, "independent_fixed_image_rows_checked": 900,
          "locally_rerun_COCO_metric_groups": 72, "maximum_COCO_array_difference": 0,
          "clipped_unclipped_12stats_sensitivity_max": 0, "actual_visual_panels_viewed": 66,
          "main_fixed_TP_FP_FN": [[row["fixed_all_images"][key] for key in ["TP", "FP", "FN"]] for row in main],
          "main_AP": [row["AP"] for row in main], "new_training_updates": 0, "new_board_forwards": 0,
          "default_model_or_tracker_changed": False, "new_passage_or_permanent_identity_GT": False,
          "new_fixed_external_detection_evaluation": True, "existing_final_Cows_holdout_opened": False,
          "test_images_now_opened_but_not_used_for_training_or_method_selection": True,
          "download_partial_recovery_and_CRLF_source_gate_failures_preserved": True,
          "numeric_gate_not_relaxed": True, "server_runtime_not_claimed_PYNQ_FPS": True,
          "documents": [{"path": str(path), "sha256": sha(path)} for path in documents],
          "local_links_checked": len(links), "evidence_hashes": {relative: sha(ROOT / relative) for relative in evidence},
          "assistant_self_review_not_independent_human_relabeling": True, "whole_goal_complete": False}
target = ROOT / "results/final_review.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key not in ["documents", "evidence_hashes", "main_fixed_TP_FP_FN", "main_AP"]}))
