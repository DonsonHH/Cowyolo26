from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, tarfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


verified = load(ROOT / "results/independent_verification.json")
assert verified["actual_timed_O8_forwards"] == 2963 and verified["all_new_actual_model_forwards"] == 3083
assert verified["actual_photos_inputs_and_features_verified"] == 80 and verified["counter_observation_ticks"] == 17227
assert verified["counter_paths"] == 16 and verified["fixed_job_pair_comparisons"] == 40
assert [row["source_down_count"] for row in verified["cases"]] == [9, 10, 9, 8, 10, 10, 8, 10]
assert [row["processed_frames"] for row in verified["cases"]] == [356, 357, 353, 357, 391, 383, 374, 392]
assert [row["deadline_misses"] for row in verified["cases"]] == [356, 357, 353, 357, 58, 67, 64, 68]
visual = load(ROOT / "results/visual_review.json")
assert visual["actually_viewed"] and visual["unique_actual_photos"] == 10 and visual["all80_original_occurrences_verified"]
for row in visual["files"]:
    assert row["actually_viewed"] and sha(Path(row["file"])) == row["sha256"]
transfer = load(ROOT / "results/transfer_verification.json")
assert transfer["manifest_files"] == 337 and transfer["members"] == 338
uart = load(ROOT / "evidence/all8_binary_terminal.json")
assert uart["tty_restored_verified"] and uart["blocks_verified"] == 195 and uart["retries"] == 0
final_read = load(ROOT / "evidence/final_board_read.json")
assert final_read["status"] == "PRIVILEGED_UART_COMMAND_FINISHED" and final_read["exit_code"] == 0 and final_read["password_recorded"] is False
board = [json.loads(line.strip()) for line in final_read["output"].splitlines() if line.strip().startswith('{"status":')][-1]
assert board["all_checked_PIDs_absent"] and board["shared_lock_available"] and all(board["local_services"].values())
assert board["eth0_carrier"] == "0" and board["PL_bit_sha256"] == "5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8"
assert load(PROJECT / "cpu_partition_free_20261030/evidence/serial_launch.json")["exit_code"] == 1
assert "SyntaxError" in load(PROJECT / "cpu_partition_free_20261030/evidence/serial_launch.json")["output"]
assert load(PROJECT / "cpu_partition_free_20261030/evidence/serial_launch_v2.json")["exit_code"] == 0
for stage, folder in [("foregroundCPU0", "cpu_partition_20261030"), ("foregroundCPU01", "cpu_partition_free_20261030")]:
    protocol = load(ROOT / "delivery" / stage / "run_protocol.json")
    assert sha(ROOT / "delivery" / stage / "run_protocol.json") == sha(PROJECT / folder / "protocol/run_v1.json")
    for row in protocol["payload_files"]:
        assert sha(ROOT / "delivery" / stage / row["file"]) == sha(PROJECT / folder / "tools" / row["file"]) == row["sha256"]
documents = [PROJECT / "cpu_partition_20261030/计划与验收.md", PROJECT / "cpu_partition_free_20261030/计划与验收.md",
             ROOT / "固定照片负载八次实机与CPU分配取舍.md"]
links = []
for path in documents:
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        target = target.strip("<>")
        if not target.startswith(("http:", "https:")):
            linked = (path.parent / unquote(target)).resolve()
            assert linked.exists()
            links.append(str(linked))
evidence = []
for folder in [PROJECT / "cpu_partition_20261030", PROJECT / "cpu_partition_free_20261030", ROOT]:
    for subfolder in ["tools", "protocol", "results", "evidence"]:
        evidence += [path for path in (folder / subfolder).rglob("*") if path.is_file() and path.suffix in [".py", ".txt", ".json", ".jsonl"]]
sources = [PROJECT / "pynq_mosaic192_eval_20261030/board_delivery/results/original/all_raw.npy",
           PROJECT / "pynq_mosaic192_eval_20261030/board_delivery/results/original/stride5_counter_trace.json.gz",
           PROJECT / "backend_service_20261030/delivery/results/r1_idle_gate/background/record.json",
           PROJECT / "pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py",
           PROJECT / "long_video_fixed_replay_20261029/tools/verify_delivery.py"]
with tarfile.open(ROOT / "cpu_partition_input_v1.tar.gz") as archive:
    assert len(archive.getmembers()) == load(ROOT / "evidence/input_bundle.json")["members"] == 2
result = {"status": "EIGHT_REAL_FIXED_JOB_O8_ARM_RUNS2963_RAW80_ORIGINAL_PHOTOS_COMPLETE_ARCHIVE_AND_NONADOPTION_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "actual_timed_O8_forwards": 2963,
          "actual_O8_qualification_forwards": 16, "actual_O8_warmups": 16, "actual_ARM_identity_queries": 80, "actual_ARM_identity_warmups": 8,
          "new_Torch_reference_forwards": 0, "all_new_actual_model_forwards": 3083,
          "case_processed_frames": [356, 357, 353, 357, 391, 383, 374, 392],
          "case_source_down_counts": [9, 10, 9, 8, 10, 10, 8, 10],
          "case_deadline_misses": [356, 357, 353, 357, 58, 67, 64, 68],
          "fixed_identity_jobs_per_case": 10, "counter_observation_ticks": 17227, "counter_paths": 16,
          "all80_photo_pixels_inputs_and_four_vector_arrays_verified": True, "unique_photos_actually_viewed": 10,
          "all80_occurrences_hash_bound": True, "same_fixed_job_pair_comparisons": 40,
          "accepted_predictions": 8, "all8_accepts_same_f9790_not8_verified_cows": True,
          "foreground_affinity_main_thread_and_publisher_scope_only_disclosed": True,
          "background_all_observed_threads_mask_checked": True, "posthoc_followup_and_cross_stage_drift_disclosed": True,
          "PNG_NPZ_evidence_IO_and_progress_overhead_scope_disclosed": True,
          "every_frame_highres_ring_not_in_this_control": True, "fixed_jobs_not_current_event_triggers": True,
          "small_input_receiver_readiness_framing_failure_preserved_and_same_receiver_continued": True,
          "additional_launch_quote_compile_failure_zero_model_forwards_preserved": True,
          "generic_collection_staging_status_contains_literal6_but_actual_member_count2_independently_checked": True,
          "full_original_archive_received_and337_files_verified": True, "UART195_blocks_and_full_SHA_verified": True,
          "UART_settings_restored_no_baud_or_reset": True, "all_experiment_workers_collectors_terminal_absent": True,
          "current_loaded_O8_rechecked": True, "shared_lock_available": True, "board_local_services_active": True,
          "ethernet_carrier": 0, "external_board_network_recovered": False,
          "new_global_default_adopted": False, "fixed_background_CPU1_or_foreground_main_CPU0_adopted": False,
          "new_training_updates": 0, "new_independent_test_or_identity_GT": False,
          "live_camera_or_RFID": False, "stable5FPS_and_count12_proven": False, "permanent_identity_accuracy_proven": False,
          "documents": [{"path": str(path), "sha256": sha(path)} for path in documents],
          "evidence_hashes": {path.relative_to(PROJECT).as_posix(): sha(path) for path in evidence},
          "source_bindings": [{"path": str(path), "sha256": sha(path)} for path in sources],
          "local_links_checked": len(links), "assistant_self_review_not_independent_human": True, "whole_goal_complete": False}
target = ROOT / "results/final_review.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key not in ["documents", "evidence_hashes", "source_bindings"]}))
