from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json, tarfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


admission = json.loads((ROOT / "results/pixel_admission.json").read_text())
assert admission["admitted_for_fixed_feature_study"]
for source, name in [("pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py", "frozen_body_tensor.py"),
                     ("identity_training_20261026/tools/identity_metrics.py", "frozen_identity_metrics.py"),
                     ("identity_training_20261026/tools/training_primitives.py", "frozen_training_primitives.py")]:
    destination = ROOT / "tools" / name
    assert not destination.exists()
    destination.write_bytes((PROJECT / source).read_bytes())
for path in (ROOT / "tools").glob("*.py"):
    ast.parse(path.read_text(encoding="utf-8"))
plan = json.loads((ROOT / "protocol/run_v1.json").read_text())
assert sha(ROOT / "tools/frozen_body_tensor.py") == plan["body_tensor_module_sha256"]
assert sha(ROOT / "tools/frozen_identity_metrics.py") == plan["metrics_module_sha256"]
paths = sorted([path for directory in ["input", "tools", "protocol"] for path in (ROOT / directory).rglob("*") if path.is_file()]
               + [ROOT / "results/acquisition.json", ROOT / "results/acquisition_v2.json", ROOT / "results/pixel_admission.json", ROOT / "计划与验收.md"])
execution = {"created_UTC": datetime.now(timezone.utc).isoformat(), "protocol_sha256": sha(ROOT / "protocol/run_v1.json"),
             "files_sha256": {path.relative_to(ROOT).as_posix(): sha(path) for path in paths},
             "new_feature_forwards_before_execution_freeze": 0}
target = ROOT / "protocol/execution_v1.json"
assert not target.exists()
target.write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")
paths.append(target)
archive = ROOT / "identity_input_v1.tar.gz"
assert not archive.exists()
with tarfile.open(archive, "w:gz") as stream:
    for path in paths:
        stream.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
record = {"bytes": archive.stat().st_size, "sha256": sha(archive), "members": len(paths), "protocol_sha256": execution["protocol_sha256"], "new_model_forwards": 0}
output = ROOT / "evidence/input_bundle.json"
assert not output.exists()
output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record))
