from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


previous_path = ROOT / "results/overview_review_20261030_v10.json"
previous = load(previous_path)
updates = load(ROOT / "results/full_archive_external_entrypoint_updates_20261030.json")
for row in updates["records"]:
    assert sha(Path(row["before_snapshot"])) == row["before_sha256"]
    assert sha(Path(row["target"])) == row["after_sha256"]
assert updates["records"][0]["before_sha256"] == previous["document"]["sha256"]
bindings = previous["current_numeric_record_files"].copy()
for relative in ["backend_service_20261030/results/full_archive_followup_review_v2.json",
                 "external_sources_20261030/results/final_review.json", "colo_eval_20261030/results/final_review.json"]:
    path = PROJECT / relative
    assert all(row["path"] != str(path) for row in bindings)
    bindings.append({"path": str(path), "sha256": sha(path)})
for row in bindings:
    assert sha(Path(row["path"])) == row["sha256"]
overview = PROJECT / "研究阶段总结_20261030.md"
text = overview.read_text(encoding="utf-8")
assert "\ufffd" not in text and "原完整包仍待下载" not in text and "原20MB完整包尚未本机下载" not in text
assert all(word in text for word in ["19.11%", "20.44%", "235.55", "370.93", "mosaic", "10／人工12", "72组", "66面板", "没有新训练或板端推理"])
links = []
for match in re.finditer(r"\]\((?:<([^>]+)>|([^\s)]+))\)", text):
    target = match[1] or match[2]
    if re.match(r"^[A-Za-z]:[/\\]", target):
        assert Path(target).exists(), target
        links.append(target)
recovery = load(PROJECT / "backend_service_20261030/results/full_archive_followup_review_v2.json")
colo = load(PROJECT / "colo_eval_20261030/results/final_review.json")
assert recovery["full_original_archive_locally_downloaded"] and recovery["loaded_O8_rechecked_after_network_loss"]
assert colo["actual_source_image_forwards"] == 450 and colo["new_board_forwards"] == 0
topics = previous["manual_review_topics"] + [
    "full_original20MB179member178manifest_archive_now_received_not_pending;old_frozen_phase_scope_preserved",
    "1466_original_raw39_original_PNG_NPZ_locally_checked_and_prior_recovery_byte_exact;existing_index_collision_disclosed",
    "guarded_privileged_UART_current_loaded_O8_rechecked;Ethernet_NO_CARRIER_not_recovered_network",
    "three_source_intake_status;COLO_top504_3950_and22_config_duplicates;AutoCattlogger404_CattleEyeView_no_data",
    "COLO_test50_451_original_and450_valid_GT;zero_width127_and15_small_OOB_preidentified_before_pixels_predictions",
    "frozen_models_sizes_and_labels_before_first_COLO_test_pixel;450_direct_Torch_CPU_images45_calls_zero_warmup_not_board",
    "old19292_21_358_vs_new19286_5_364;AP11_99_vs11_97_not_general_improvement;all9conditions_reported",
    "COCO72_groups_full_raw_local_rerun_exact;900_fixed_image_match_records;66_fixed_panels_actual_view",
    "same192trained_weights_tested_at256320_not_previous_separately_trained_size_weights_or_quantized_O8",
    "partial_download42plus8_source_CRC_recovery_and_CRLF_code_hash_failure_preserved_no_numeric_gate_relaxation",
    "body_vs_author_inferred_hidden_extents_wideangle_partial_border_scope_not_assumed_single_cause",
    "COLO_fixed_external_detection_evaluation_not_new_passage_or_identity_GT;future_method_selection_requires_new_final_data",
    "new_stage450_CPU_forwards0_board0_training;prior_backend1594_not_recounted",
    "Defra_primary_page_live_refreshed_2026_10_30_England_newborn2027;EU_primary_live_bot_gate_not_claimed_refreshed"
]
result = {"status": "WHOLE_OVERVIEW_MANUAL_CLAIMS_AND_CURRENT_PHASE_NUMBERS_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(),
          "document": {"path": str(overview), "sha256": sha(overview)},
          "reviewer_kind": "assistant_self_review_with_separate_raw_evidence_recomputation_not_independent_human_review",
          "entire_current_overview_read_in_full": True, "manual_review_topics": topics,
          "current_numeric_record_files": bindings, "local_overview_links_checked": len(links),
          "previous_review_preserved": {"path": str(previous_path), "sha256": sha(previous_path)},
          "previous_overview_snapshot": {"path": updates["records"][0]["before_snapshot"], "sha256": updates["records"][0]["before_sha256"]},
          "entrypoint_update_evidence": {"path": str(ROOT / "results/full_archive_external_entrypoint_updates_20261030.json"),
                                         "sha256": sha(ROOT / "results/full_archive_external_entrypoint_updates_20261030.json")},
          "new_model_forwards": 450, "new_model_forward_breakdown": {"CPU_Torch_COLO_images": 450, "PYNQ": 0, "warmups": 0},
          "new_training_updates": 0, "new_board_inference": False, "new_board_actions_performed": True,
          "new_board_action_scope": "UART original archive recovery and guarded privileged final loaded-PL read; no reprogramming or experiment rerun",
          "current_stage_recovery_new_forwards": 0, "current_stage_CPU_reference_rerun_new_model_forwards": 0,
          "new_periodic_counter_or_identity_run": False, "full_periodic_5FPS_target_fixed": False,
          "original_full_archive_downloaded": True, "current_loaded_O8_rechecked": True,
          "external_board_services_recovered": False, "new_fixed_external_detection_evaluation": True,
          "independent_event_JSON_received": False, "permanent_identity_accuracy_proven": False,
          "live_camera_RFID_proven": False, "same_board_execution_on_replayed_public_source_verified": True,
          "same_board_execution_scope": "Existing actual O8/ARM public replay evidence preserved; current stage adds no device inference. Full original backend evidence is now local.",
          "main_paper_contribution_verified": False, "whole_goal_complete": False}
target = ROOT / "results/overview_review_20261030_v11.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "local_overview_links_checked", "new_model_forwards", "original_full_archive_downloaded", "whole_goal_complete"]}))
