from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


previous_file = ROOT / "results/overview_review_20261030_v12.json"
previous = load(previous_file)
updates_file = ROOT / "results/Cows2021_identity_entrypoint_updates_20261030.json"
updates = load(updates_file)
clarifications_file = ROOT / "results/overview_scope_clarifications_v13.json"
clarifications = load(clarifications_file)
assert sha(Path(clarifications["before_snapshot"])) == clarifications["before_sha256"]
for index, row in enumerate(updates["records"]):
    assert sha(Path(row["before_snapshot"])) == row["before_sha256"]
    if index == 0:
        assert row["before_sha256"] == previous["document"]["sha256"]
        assert row["after_sha256"] == clarifications["before_sha256"]
        assert sha(Path(row["target"])) == clarifications["after_sha256"]
    else:
        assert sha(Path(row["target"])) == row["after_sha256"]
bindings = previous["current_numeric_record_files"].copy()
for relative in ["cows2021_identity_intake_20261030/results/final_review.json", "cows2021_identity_eval_20261030/results/final_review.json", "cows2021_identity_gallery_control_20261030/results/final_review.json"]:
    path = PROJECT / relative
    assert all(row["path"] != str(path) for row in bindings)
    bindings.append({"path": str(path), "sha256": sha(path)})
for row in bindings:
    assert sha(Path(row["path"])) == row["sha256"]
overview = PROJECT / "研究阶段总结_20261030.md"
text = overview.read_text(encoding="utf-8")
assert "\ufffd" not in text
assert all(value in text for value in ["540", "1080", "54.17%", "21／120", "20／120", "20ID", "40ID", "作者", "不在评价集调阈值", "03-05至03-11", "本轮未重新排查", "新的最终身份评价"])
links = []
for match in re.finditer(r"\]\((?:<([^>]+)>|([^\s)]+))\)", text):
    target = match[1] or match[2]
    if re.match(r"^[A-Za-z]:[/\\]", target):
        assert Path(target).exists(), target
        links.append(target)
topics = previous["manual_review_topics"] + [
    "Cows2021_identityREADME13784_total_vs_paper8670_test_resolved;181_nonempty_IDs_with_empty179of182_directories",
    "301_train_video_directories435_tracklets_not_permanent_IDs;two_Test_filename_formats_audited_no_silent739_exclusions",
    "7931_exact_detection_source_crop_links_scope_not_independent_full_pipeline;physical_crossyear_ID_mapping_unknown",
    "120_SHA_selected_IDs540_public_crops_cal20known20unknown_eval40known40unknown_role_disjoint_galleries_7days_earlier",
    "all_new_pixels_dates_no_later_Mar04;reservedMar05_toMar11_unopened;CRC_and_canonical_pixelhash_all540_no_previous750_exact_overlap",
    "two_fixed_encoders_no_seed_or_method_selection;1080_CPU_images90_calls_zero_warmup;0training0board",
    "thresholds_joint_frozen_after360calibration_before_any720evaluation_forward_not_tuned_on240evalqueries",
    "all4_main_C_W_U_FA_counts26_6_88_9;37_11_72_20;30_21_69_21;30_21_69_20;known_andunknown_denoms120_each",
    "currentC_Top1_65of120_and_Top5_100of120;baseline69and106;not_claim_statistical_winner_from4correct_difference",
    "cal20_vs_eval40_gallery_cardinality_confound_explicit_not_wholly_attributed_network_or_unknown_distribution",
    "posthoc_same_query16_registrycontrols2880decisions86400scores_and720monotonicpairs;C_unknown12or16to20of120",
    "20ID_eval_still10or13_33percent_unknownFA_vs_empiricalcal5percent_not_a_population_risk_bound",
    "540_tensors1080_features24000scores720retrievalrows960decisions_and2000_ID_bootstrap_locally_recomputed",
    "source12_preselected_and11_posthoc_retrieval_panels_actually_viewed_no_quality_or_GT_relabeling",
    "TLS_EOF_onlysameimage499_retried539reused;partial_download_extract_guard_then_same_handle_terminal_no_experiment_rerun",
    "public_author_identity_accuracy_evaluation_now_exists_but_current12events_permanent_ID_and_reliable_recovery_unproven",
    "existing8_real_board_cases_preserved_but_this_stage_no_board_inference_or_carrier_refresh;CPU_time_not_Z2",
    "whole_overview_read_scope_tightened_current192_count_and_missing_current_event_ID_vs_existing_public_author_GT"
]
result = {"status": "WHOLE_OVERVIEW_MANUAL_CLAIMS_AND_CURRENT_PHASE_NUMBERS_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "document": {"path": str(overview), "sha256": sha(overview)},
          "reviewer_kind": "assistant_self_review_with_independent_feature_score_and_metric_recomputation_not_independent_human",
          "entire_current_overview_read_in_full": True, "manual_review_topics": topics, "current_numeric_record_files": bindings,
          "local_overview_links_checked": len(links), "previous_review_preserved": {"path": str(previous_file), "sha256": sha(previous_file)},
          "previous_overview_snapshot": {"path": updates["records"][0]["before_snapshot"], "sha256": updates["records"][0]["before_sha256"]},
          "entrypoint_update_evidence": {"path": str(updates_file), "sha256": sha(updates_file)},
          "manual_scope_clarifications": {"path": str(clarifications_file), "sha256": sha(clarifications_file)},
          "new_model_forwards": 1080, "new_model_forward_breakdown": {"CPU_body_calibration":360,"CPU_body_evaluation":720,"PYNQ":0,"warmups":0},
          "new_training_updates":0, "new_board_actions_performed":False, "new_periodic_counter_or_identity_run":False,
          "new_public_curated_identity_evaluation":True, "new_public_identity_source_IDs":120,
          "public_cropped_identity_evaluation_model_image_forwards":1080,
          "current_event_permanent_ID_mapping_received":False, "independent_event_JSON_received":False,
          "reliable_automatic_identity_recovery_proven":False, "live_camera_RFID_proven":False,
          "full_periodic_5FPS_target_fixed":False, "current_board_carrier_live_rechecked":False,
          "same_board_execution_on_replayed_public_source_verified":True,
          "same_board_execution_scope":"Existing actual O8/ARM public replay evidence retained, no new board inference this stage. New author-crop identity accuracy is CPU only and has high wrong/unknown acceptance.",
          "default_model_tracker_or_reject_threshold_changed":False,
          "main_paper_contribution_verified":False, "whole_goal_complete":False}
assert sum(result["new_model_forward_breakdown"].values()) == 1080
target = ROOT / "results/overview_review_20261030_v13.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps({key:result[key] for key in ["status","local_overview_links_checked","new_model_forwards","new_public_curated_identity_evaluation","whole_goal_complete"]}))
