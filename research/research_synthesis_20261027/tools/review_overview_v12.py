from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


previous_file = ROOT / "results/overview_review_20261030_v11.json"
previous = load(previous_file)
updates_file = ROOT / "results/affinity_diagnosis_entrypoint_updates_20261030.json"
updates = load(updates_file)
clarification_file = ROOT / "results/overview_scope_clarifications_v12.json"
clarification = load(clarification_file)
assert sha(Path(clarification["before_snapshot"])) == clarification["before_sha256"]
for index, record in enumerate(updates["records"]):
    assert sha(Path(record["before_snapshot"])) == record["before_sha256"]
    if index == 0:
        assert record["before_sha256"] == previous["document"]["sha256"]
        assert record["after_sha256"] == clarification["before_sha256"]
        assert sha(Path(record["target"])) == clarification["after_sha256"]
    else:
        assert sha(Path(record["target"])) == record["after_sha256"]
bindings = previous["current_numeric_record_files"].copy()
for relative in ["colo_error_diagnosis_20261030/results/final_review.json", "cpu_partition_combined_20261030/results/final_review.json"]:
    path = PROJECT / relative
    assert all(row["path"] != str(path) for row in bindings)
    bindings.append({"path": str(path), "sha256": sha(path)})
for row in bindings:
    assert sha(Path(row["path"])) == row["sha256"]
overview = PROJECT / "研究阶段总结_20261030.md"
text = overview.read_text(encoding="utf-8")
assert "\ufffd" not in text and "本轮为450次Torch CPU前向" not in text
assert all(value in text for value in ["3083", "2963", "17227", "19.11%", "conf0.20", "固定任务", "每帧", "主线程", "严格核心隔离", "104个", "196个", "64个", "没有永久身份真值"])
links = []
for match in re.finditer(r"\]\((?:<([^>]+)>|([^\s)]+))\)", text):
    target = match[1] or match[2]
    if re.match(r"^[A-Za-z]:[/\\]", target):
        assert Path(target).exists(), target
        links.append(target)
topics = previous["manual_review_topics"] + [
    "new9_condition4050_GT173_FP5400_oracle_graph_error_diagnosis_is_development_not_unseen_test",
    "new192104_low001_to020_196_below001_64_geometry_missing_FNs_not_all_boundary;interior28of186",
    "GT_oracle190_or386_not_deployable_recall;all9_fixed_score_matching_upper_bounds_already_equal_TP",
    "body_vs_author_amodal_cow_contract_written_without_auto_relabeling_or_hiding_full450_results",
    "two4_run_ABBA_phases_same10_frozen_photo_jobs_each_not_current_counter_triggers_or_highres_ring",
    "main_thread_CPU0_9_10_9_8_all1423late_results_preserved;posthoc_followup_temporal_drift_disclosed",
    "main_thread_two_core_shared391_392vsbackground_CPU1_383_374_with_count10_10_8_10_no_adoption",
    "foreground_main_and_publisher_affinity_only_not_strict_every_library_thread_isolation;Linux_primary_source_checked",
    "complete_backend_latencies_include_PNG_NPZ_evidence_IO_not_pure168_to206ms_network",
    "2963_new_O8_timed16qualification16warmup80_ARM_queries8warmup_total3083;new_Torch0;newtraining0",
    "17227_observations16_counter_paths80_original_PNG_input_raw_normalized_score_arrays_locally_recomputed",
    "10_unique_photo_panels_viewed_all80_occurrences_bound;8_accepts_same_f9790_not8_verified_animals",
    "all8_full_original338member337manifest_archive_local195_binary_blocks_and_fullSHA_TTY_restored",
    "12_task_PIDs_absent_current_loaded_O8_lock_services_rechecked;Ethernet_carrier0;no_reboot_or_IP_change",
    "same_waiting_input_receiver_resumed_on_readiness_framing_error;separate_launch_quote_compile_failure_model0_preserved",
    "generic2member_collection_stage_label6_is_not_used_as_a_numerical_count",
    "public_ID_dataset_candidate_is_not_claimed_downloaded_or_pixel_admitted;reserved_detection_holdout_still_closed",
    "whole_current_overview_read_and_three_historical_stage_scope_phrases_clarified_without_experiment_changes"
]
result = {"status": "WHOLE_OVERVIEW_MANUAL_CLAIMS_AND_CURRENT_PHASE_NUMBERS_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "document": {"path": str(overview), "sha256": sha(overview)},
          "reviewer_kind": "assistant_self_review_with_independent_raw_and_counter_recomputation_not_independent_human",
          "entire_current_overview_read_in_full": True, "manual_review_topics": topics,
          "current_numeric_record_files": bindings, "local_overview_links_checked": len(links),
          "previous_review_preserved": {"path": str(previous_file), "sha256": sha(previous_file)},
          "previous_overview_snapshot": {"path": updates["records"][0]["before_snapshot"], "sha256": updates["records"][0]["before_sha256"]},
          "entrypoint_update_evidence": {"path": str(updates_file), "sha256": sha(updates_file)},
          "manual_scope_clarifications": {"path": str(clarification_file), "sha256": sha(clarification_file)},
          "new_model_forwards": 3083,
          "new_model_forward_breakdown": {"O8_timed": 2963, "O8_qualification": 16, "O8_warmups": 16, "ARM_identity_queries": 80, "ARM_warmups": 8, "CPU_Torch_reference": 0},
          "new_training_updates": 0, "new_periodic_counter_or_identity_run": True, "new_board_actions_performed": True,
          "new_stage_diagnostic_model_forwards": 0, "actual_new_same_board_cases": 8,
          "fixed_jobs_not_current_event_triggers": True, "strict_every_thread_core_isolation_proven": False,
          "independent_event_JSON_received": False, "permanent_identity_accuracy_proven": False, "live_camera_RFID_proven": False,
          "full_periodic_5FPS_target_fixed": False, "original_full_archive_downloaded": True,
          "current_loaded_O8_rechecked": True, "external_board_services_recovered": False,
          "same_board_execution_on_replayed_public_source_verified": True,
          "same_board_execution_scope": "Eight real O8/ARM fixed10-job stress runs plus prior actual-trigger public replay. No live camera/RFID or permanent identity accuracy claim; foreground masks sampled for main/publisher only.",
          "default_model_tracker_or_reject_threshold_changed": False,
          "main_paper_contribution_verified": False, "whole_goal_complete": False}
assert sum(result["new_model_forward_breakdown"].values()) == 3083
target = ROOT / "results/overview_review_20261030_v12.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "local_overview_links_checked", "new_model_forwards", "actual_new_same_board_cases", "whole_goal_complete"]}))
