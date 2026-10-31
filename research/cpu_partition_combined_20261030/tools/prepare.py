from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, tarfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


protocol = {"status": "FULL_ORIGINAL_EIGHT_RUN_COLLECTION_PROTOCOL", "created_UTC": datetime.now(timezone.utc).isoformat(),
            "stages": [{"name": name, "directory": "/home/xilinx/jupyter_notebooks/cow_research_" + folder,
                        "protocol_sha256": sha(PROJECT / folder / "protocol/run_v1.json")}
                       for name, folder in [("foregroundCPU0", "cpu_partition_20261030"), ("foregroundCPU01", "cpu_partition_free_20261030")]],
            "previous_task_PIDs_required_absent": [11554, 12397, 12890],
            "payload_files": [{"file": "collect_eight.py", "sha256": sha(ROOT / "tools/collect_eight.py")}],
            "new_model_forwards": 0, "source_results_not_modified": True, "whole_goal_complete": False}
target = ROOT / "protocol/run_v1.json"
target.parent.mkdir(exist_ok=False)
target.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
archive = ROOT / "cpu_partition_input_v1.tar.gz"
assert not archive.exists()
with tarfile.open(archive, "w:gz") as stream:
    stream.add(ROOT / "tools/collect_eight.py", arcname="collect_eight.py", recursive=False)
    stream.add(target, arcname="run_protocol.json", recursive=False)
for name in ["stage_input_uart.py", "serial_sudo_command.py"]:
    text = (PROJECT / "cpu_partition_free_20261030/tools" / name).read_text(encoding="utf-8").replace("cow_research_cpu_partition_free_20261030", "cow_research_cpu_partition_combined_20261030")
    output = ROOT / "tools" / name
    assert not output.exists()
    output.write_text(text, encoding="utf-8")
(ROOT / "evidence").mkdir(exist_ok=False)
bundle = {"bytes": archive.stat().st_size, "sha256": sha(archive), "members": 2, "protocol_sha256": sha(target), "new_model_forwards": 0}
(ROOT / "evidence/input_bundle.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
print(json.dumps(bundle))
