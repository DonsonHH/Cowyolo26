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


transfer = load(ROOT / "results/full_archive_transfer_verification_v2.json")
archive = ROOT / "backend_service_delivery_v1.tar.gz"
assert archive.stat().st_size == transfer["bytes"] == 20018871
assert sha(archive) == transfer["sha256"] == "b87a60784d7f414ae512855d3ed658613d8dc7c2e03cf6ec856d7d61856422a6"
manifest = load(ROOT / "delivery/result_manifest.json")
assert len(manifest) == 178
for row in manifest:
    path = (ROOT / "delivery" / row["file"]).resolve()
    assert path.is_relative_to((ROOT / "delivery").resolve())
    assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]
raw = load(ROOT / "results/independent_verification.json")
assert raw["actual_O8_timed_forwards"] == 1466 and raw["actual_background_identity_jobs"] == 39
assert [row["source_down_count"] for row in raw["cases"]] == [10, 9, 10, 10]
comparison = load(ROOT / "results/original_vs_recovery_verification_v2.json")
assert comparison["all_original_and_recovery_input_raw_normalized_score_arrays_byte_equal"]
assert len(comparison["checks"]) == 39
producer = load(ROOT / "results/producer_independent_verification.json")
assert producer["producer_source_frames"] == 1568 and producer["main_received_packets"] == 1466
assert producer["overlapping_model_IO_packet_cases"] == 1152 and producer["all_no_future_reads"]
cpu = load(ROOT / "results/CPU_independent_verification.json")
assert [row["windows_with_positive_child_CPU_ticks"] for row in cpu["runs"]] == [0, 48, 46, 0]
assert [row["sum_child_CPU_ticks_inside_boundary_windows"] for row in cpu["runs"]] == [0, 857, 975, 0]
privileged = load(ROOT / "evidence/serial_privileged_final_loaded_state_v2.json")
assert privileged["status"] == "PRIVILEGED_UART_READ_FINISHED" and privileged["exit_code"] == 0
assert privileged["password_recorded"] is False and privileged["guarded_echo_off_observed"]
state = [json.loads(line) for line in privileged["output"].splitlines() if line.startswith('{"status":')][-1]
assert state["all_checked_PIDs_absent"] and state["lock_available"]
assert state["PL_bitfile"].endswith("/yolo26_optimization_8/hardware/accepted/optimization_8_resident.bit")
assert state["PL_bit_sha256"] == "5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8"
assert state["eth0_carrier"] == "0" and all(state["local_services"].values())
assert state["new_model_forwards"] == 0 and state["PL_programming"] is False
prior = load(ROOT / "results/final_review.json")
assert prior["full_original_archive_locally_downloaded"] is False
for mapping in ["evidence_hashes", "code_hashes"]:
    for relative, digest in prior[mapping].items():
        assert sha(ROOT / relative) == digest
for row in prior["documents"]:
    assert sha(Path(row["path"])) == row["sha256"]
document = ROOT / "完整归档恢复与复核补充_v2.md"
links = []
for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
    target = target.strip("<>")
    if not target.startswith(("http:", "https:")):
        path = (document.parent / unquote(target)).resolve()
        assert path.exists(), path
        links.append(str(path))
evidence = ["results/final_review.json", "evidence/full_archive_UART_terminal.json",
            "results/full_archive_transfer_verification_v2.json", "results/independent_verification.json",
            "results/original_vs_recovery_verification_v2.json", "results/producer_independent_verification.json",
            "results/CPU_independent_verification.json", "evidence/serial_privileged_final_loaded_state_v2.json",
            "delivery/result_manifest.json", "tools/extract_full_UART_delivery.py",
            "tools/verify_original_vs_recovery.py", "tools/serial_sudo_readonly.py",
            "tools/serial_final_recovery_state.txt", "tools/recover_full_archive_uart.py",
            "tools/review_full_archive_followup.py"]
result = {"status": "FULL_ORIGINAL_ARCHIVE178_FILES1466_RAW39_PHOTOS_VECTORS_AND_CURRENT_LOADED_O8_FOLLOWUP_REVIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(),
          "full_original_archive_locally_downloaded": True, "manifest_files": 178,
          "actual_raw_arrays_locally_checked": 1466, "original_PNGs_and_NPZs_checked": 39,
          "prior_recovery_matches_full_original": True, "earlier_frozen_reports_preserved": True,
          "loaded_O8_rechecked_after_network_loss": True, "ethernet_carrier": 0,
          "external_board_network_recovered": False, "all_checked_task_PIDs_absent": True,
          "original_experimental_counts": [10, 9, 10, 10], "global_default_changed": False,
          "new_model_forwards": 0, "new_training_updates": 0, "new_experiment_rerun": False,
          "index_output_collision_disclosed_without_changing_numeric_gate": True,
          "documents": [{"path": str(document), "sha256": sha(document)}],
          "local_links_checked": len(links),
          "evidence_hashes": {relative: sha(ROOT / relative) for relative in evidence},
          "assistant_self_review_not_independent_human": True, "whole_goal_complete": False}
target = ROOT / "results/full_archive_followup_review_v2.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "manifest_files", "actual_raw_arrays_locally_checked", "new_model_forwards"]}))
