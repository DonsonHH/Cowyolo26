from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib, json, tarfile

ROOT = Path(__file__).resolve().parents[1]
transfer = json.loads((ROOT / "evidence/transfer.json").read_text())
archive = ROOT / "all8_fixed_job_original_delivery_v1.tar.xz"
terminal = json.loads((ROOT / "evidence/all8_binary_terminal.json").read_text())
assert terminal["status"] == "FULL_BINARY_UART_FILE_BLOCKS_AND_FINAL_SHA_VERIFIED_TTY_RESTORED"
assert archive.stat().st_size == transfer["bytes"] == 12716988
assert hashlib.sha256(archive.read_bytes()).hexdigest() == transfer["sha256"] == "305bcce362912d1dc3918e2ddc9a122b2a50a020a494b9a810594fd65f8e258c"
out = ROOT / "delivery"
out.mkdir(exist_ok=False)
with tarfile.open(archive, "r:xz") as stream:
    members = stream.getmembers()
    assert len(members) == transfer["members"] == 338
    for member in members:
        relative = PurePosixPath(member.name)
        assert member.isfile() and not relative.is_absolute() and ".." not in relative.parts
        target = (out / member.name).resolve()
        assert target.is_relative_to(out.resolve()) and not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(stream.extractfile(member).read())
manifest = json.loads((out / "result_manifest.json").read_text())
assert len(manifest) == transfer["manifest_files"] == 337
for row in manifest:
    path = out / row["file"]
    assert path.stat().st_size == row["bytes"] and hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
for name, source in [("foregroundCPU0", "cpu_partition_20261030"), ("foregroundCPU01", "cpu_partition_free_20261030")]:
    assert (out / name / "run_protocol.json").read_bytes() == (ROOT.parent / source / "protocol/run_v1.json").read_bytes()
    plan = json.loads((out / name / "run_protocol.json").read_text())
    for row in plan["payload_files"]:
        assert hashlib.sha256((out / name / row["file"]).read_bytes()).hexdigest() == row["sha256"]
result = {"status": "ALL8_ORIGINAL338_MEMBER337_MANIFEST_FILES_LOCAL_HASH_VERIFIED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "archive_bytes": archive.stat().st_size,
          "archive_sha256": transfer["sha256"], "members": 338, "manifest_files": 337,
          "all_original_raw_PNG_NPZ_and_logs_received": True, "new_model_forwards": 0, "whole_goal_complete": False}
(ROOT / "results").mkdir(exist_ok=True)
target = ROOT / "results/transfer_verification.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
