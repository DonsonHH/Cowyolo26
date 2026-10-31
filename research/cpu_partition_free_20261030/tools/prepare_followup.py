from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / "cpu_partition_20261030"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


first = json.loads((OLD / "protocol/run_v1.json").read_text())
observed = json.loads((OLD / "evidence/status03_cases.json").read_text())
record = [json.loads(line.strip()) for line in observed["output"].splitlines() if line.strip().startswith('{"task":')][-1]
assert record["proc_exists"] is False and record["terminal"]["actual_O8_forwards"] == 1423
assert [row["source_down_count"] for row in record["cases"]] == [9, 10, 9, 8]
collection = json.loads((OLD / "evidence/collection_status01.json").read_text())
status = [json.loads(line.strip()) for line in collection["output"].splitlines() if line.strip().startswith('{"task":')][-1]
assert status["proc_exists"] is False and status["terminal"]["status"] == "FULL_ORIGINAL_FIXED_JOB_ARCHIVE_COMPLETE"
for row in first["payload_files"]:
    source = OLD / "tools" / row["file"]
    assert sha(source) == row["sha256"]
    text = source.read_text(encoding="utf-8")
    if row["file"] == "board_partition_repeats.py":
        assert text.count("os.sched_setaffinity(0, {0})") == 1
        assert text.count("assert sorted(os.sched_getaffinity(0)) == [0]") == 1
        text = text.replace("os.sched_setaffinity(0, {0})", "os.sched_setaffinity(0, set(protocol['foreground_affinity']))")
        text = text.replace("assert sorted(os.sched_getaffinity(0)) == [0]", "assert sorted(os.sched_getaffinity(0)) == protocol['foreground_affinity']")
    ast.parse(text)
    output = ROOT / "tools" / row["file"]
    assert not output.exists()
    output.write_text(text, encoding="utf-8")
protocol = dict(first)
protocol.update({"status": "FOLLOWUP_FOREGROUND_AFFINITY_CONTROL_FROZEN_AFTER_FIRST4_BEFORE_NEW4",
                 "created_UTC": datetime.now(timezone.utc).isoformat(), "foreground_affinity": [0, 1],
                 "first_stage_protocol_sha256": sha(OLD / "protocol/run_v1.json"),
                 "first_stage_record_sha256": record["terminal"]["record_sha256"],
                 "first_stage_counts_seen": [9, 10, 9, 8], "first_stage_O8_timed_forwards_seen": 1423,
                 "posthoc_development_followup_not_unseen_confirmatory": True,
                 "cross_stage_time_order_and_cache_swap_drift_not_excluded": True,
                 "plan_sha256": sha(ROOT / "计划与验收.md"),
                 "payload_files": [{"file": row["file"], "sha256": sha(ROOT / "tools" / row["file"])} for row in first["payload_files"]]})
target = ROOT / "protocol/run_v1.json"
target.parent.mkdir(exist_ok=False)
target.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
archive = ROOT / "cpu_partition_input_v1.tar.gz"
assert not archive.exists()
with tarfile.open(archive, "w:gz") as stream:
    for row in protocol["payload_files"]:
        stream.add(ROOT / "tools" / row["file"], arcname=row["file"], recursive=False)
    stream.add(target, arcname="run_protocol.json", recursive=False)
for name in ["stage_input_uart.py", "serial_sudo_command.py"]:
    text = (OLD / "tools" / name).read_text(encoding="utf-8")
    text = text.replace("cow_research_cpu_partition_20261030", "cow_research_cpu_partition_free_20261030")
    if name == "stage_input_uart.py":
        # The original receiver readiness can follow a bare carriage return from the terminal.
        text = text.replace('ready = ("\\r\\nUART_INPUT_READY_" + token + "\\r\\n").encode()', 'ready = ("UART_INPUT_READY_" + token + "\\r\\n").encode()')
    destination = ROOT / "tools" / name
    assert not destination.exists()
    destination.write_text(text, encoding="utf-8")
(ROOT / "evidence").mkdir(exist_ok=False)
bundle = {"bytes": archive.stat().st_size, "sha256": sha(archive), "members": 6,
          "protocol_sha256": sha(target), "new_model_forwards": 0}
(ROOT / "evidence/input_bundle.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
print(json.dumps(bundle))
