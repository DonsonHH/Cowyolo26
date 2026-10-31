from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


paths = sorted([path for directory in ["tools", "input", "protocol"] for path in (ROOT / directory).rglob("*") if path.is_file()]
               + [ROOT / "计划与验收.md", ROOT / "results/test50_acquisition.json"])
assert len(list((ROOT / "input/test50").glob("*.jpg"))) == 50
assert not (ROOT / "protocol/execution_v1.json").exists()
execution = {"created_UTC": datetime.now(timezone.utc).isoformat(), "protocol_sha256": sha(ROOT / "protocol/run_v1.json"),
             "files_sha256": {path.relative_to(ROOT).as_posix(): sha(path) for path in paths},
             "code_and_data_frozen_before_first_forward": True, "source_image_forwards_at_freeze": 0}
(ROOT / "protocol/execution_v1.json").write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")
paths.append(ROOT / "protocol/execution_v1.json")
archive = ROOT / "colo_input_v1.tar.gz"
assert not archive.exists()
with tarfile.open(archive, "w:gz") as output:
    for path in paths:
        output.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
record = {"path": str(archive), "bytes": archive.stat().st_size, "sha256": sha(archive), "members": len(paths),
          "protocol_sha256": execution["protocol_sha256"], "new_model_forwards": 0}
(ROOT / "evidence/input_bundle.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record))
