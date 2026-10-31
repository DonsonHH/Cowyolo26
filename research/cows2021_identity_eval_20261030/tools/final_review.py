from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


summary = load(ROOT / "delivery/results/evaluation/summary.json")
verified = load(ROOT / "results/independent_verification.json")
assert summary["Slurm_job_id"] == "130743" and summary["actual_model_image_forwards"] == 1080 and summary["actual_network_calls"] == 90
assert "130743|cow-cows21-id-fixed|COMPLETED|0:0|" in (ROOT / "delivery/logs/sacct-130743.txt").read_text()
assert not (ROOT / "delivery/logs/evaluation-130743.err").read_text().strip()
assert verified["registered_identity_score_cells_checked"] == 24000 and verified["evaluation_decisions_checked"] == 960
assert verified["both_thresholds_frozen_before_evaluation_feature_generation"]
counts = [[row["metrics"][key] for key in ["known_correct_accepted_C", "known_wrong_accepted_W", "known_rejected_U", "unknown_false_accepts"]] for row in summary["outcomes"]]
assert counts == [[26,6,88,9], [37,11,72,20], [30,21,69,21], [30,21,69,20]]
assert [row["metrics"]["known_closed_top1_correct"] for row in summary["outcomes"]] == [69,69,65,65]
assert [row["metrics"]["known_closed_top5_correct"] for row in summary["outcomes"]] == [106,106,100,100]
transfer = load(ROOT / "results/transfer_verification.json")
assert transfer["bytes"] == 6045293 and transfer["manifest_files"] == 35 and sha(ROOT / "identity_delivery_130743.tar.gz") == transfer["sha256"]
for row in load(ROOT / "delivery/result_manifest.json"):
    assert sha(ROOT / "delivery" / row["file"]) == row["sha256"]
for file, expected in [("source_visual_review.json", 12), ("retrieval_visual_review.json", 11)]:
    visual = load(ROOT / "results" / file)
    assert visual["actually_viewed"] and visual["panels"] == expected
    for row in visual["files"]:
        assert row["actually_viewed"] and sha(Path(row["file"])) == row["sha256"]
plan = load(ROOT / "protocol/run_v1.json")
assert len(plan["selected_images"]) == 540 and max(row["date"] for row in plan["selected_images"]) <= "2020-03-04"
assert len(set(sum(plan["roles"].values(), []))) == 120
assert load(ROOT / "results/pixel_admission.json")["admitted_for_fixed_feature_study"]
assert len([row for row in load(ROOT / "results/acquisition.json")["records"] if row["status"] == "ACQUISITION_FAILED"]) == 1
assert load(ROOT / "results/acquisition_v2.json")["previous539_images_reused_without_redownload"]
documents = [ROOT / "计划与验收.md", ROOT / "跨日期身份检索与拒识结果.md"]
links = []
for document in documents:
    for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
        target = target.strip("<>")
        if not target.startswith(("http:", "https:")):
            path = (document.parent / unquote(target)).resolve()
            assert path.exists()
            links.append(str(path))
evidence = [path for name in ["tools", "protocol", "results", "evidence"] for path in (ROOT / name).rglob("*") if path.is_file() and path.suffix in [".py", ".json", ".txt", ".jsonl", ".slurm"]]
result = {"status": "COWS2021_120_ID540_CROPS1080_CPU_FORWARDS_CROSS_DATE_OPEN_SET_AND_HIGH_ERROR_RESULTS_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "Slurm130743_completed0_0": True,
          "unique_crops": 540, "publisher_IDs": 120, "calibration_registered_unknown_IDs": [20,20], "evaluation_registered_unknown_IDs": [40,40],
          "calibration_model_image_forwards": 360, "evaluation_model_image_forwards": 720, "all_new_model_image_forwards": 1080,
          "network_calls": 90, "warmup_forwards": 0,
          "all540_input_tensors_match_original_training_preprocess": True,
          "original750_identity_input_exact_pixel_overlap": 0, "gallery_query_cross_ID_exact_pixel_duplicates": 0,
          "both_thresholds_frozen_before_any_evaluation_forward": True,
          "calibration20_vs_evaluation40_gallery_IDs_scope_disclosed": True,
          "all4_conditions_C_W_U_unknown_FA": counts, "known_query_denominator_each": 120, "unknown_query_denominator_each": 120,
          "all4_known_Top1_correct": [69,69,65,65], "all4_known_Top5_correct": [106,106,100,100],
          "identity_score_cells_independently_recomputed": 24000, "evaluation_decisions_independently_recomputed": 960,
          "bootstrap2000_by_publisher_ID_reproduced": True, "preselected_source_panels_viewed": 12, "posthoc_retrieval_panels_viewed": 11,
          "full_original35_manifest_files_received_verified": True,
          "single_TLS_EOF_only_same_image499_retried_original539_reused": True,
          "partial_transfer_extract_guard_stopped_before_any_extraction": True,
          "author_identity_crop_evaluation_now_exists": True,
          "current12_passage_permanent_ID_mapping_obtained": False, "independent_full_detector_count_ID_test": False,
          "physical_cross_dataset_identity_disjointness_claimed": False,
          "reserved2020_03_05_to2020_03_11_pixels_opened": False,
          "new_training_updates": 0, "new_board_forwards": 0, "new_deployment_threshold_or_model_adopted": False,
          "live_camera_or_RFID": False, "reliable_automatic_identity_recovery_proven": False,
          "documents": [{"path": str(path), "sha256": sha(path)} for path in documents],
          "evidence_hashes": {path.relative_to(ROOT).as_posix(): sha(path) for path in evidence},
          "local_links_checked": len(links), "assistant_self_review_not_independent_human": True, "whole_goal_complete": False}
output = ROOT / "results/final_review.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key:value for key,value in result.items() if key not in ["documents", "evidence_hashes"]}))
