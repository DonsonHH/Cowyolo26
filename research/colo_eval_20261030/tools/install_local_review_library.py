from pathlib import Path, PurePosixPath
import hashlib
import json
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
metadata = json.loads((ROOT / "evidence/pycocotools_PyPI.json").read_text(encoding="utf-8"))
row = next(row for row in metadata["urls"] if row["filename"] == "pycocotools-2.0.11-cp312-abi3-win_amd64.whl")
wheel = ROOT / "evidence" / row["filename"]
assert not wheel.exists()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
with opener.open(row["url"], timeout=20) as response:
    raw = response.read()
assert len(raw) == row["size"] and hashlib.sha256(raw).hexdigest() == row["digests"]["sha256"]
wheel.write_bytes(raw)
vendor = ROOT / "vendor_local_review"
vendor.mkdir(exist_ok=False)
with zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        path = PurePosixPath(name)
        assert not path.is_absolute() and ".." not in path.parts
        if name.endswith("/"):
            continue
        target = (vendor / name).resolve()
        assert target.is_relative_to(vendor.resolve()) and not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(name))
record = {"package": "pycocotools", "version": "2.0.11", "wheel": wheel.name,
          "wheel_SHA256": hashlib.sha256(raw).hexdigest(), "destination": str(vendor),
          "global_environment_changed": False, "new_model_forwards": 0}
(ROOT / "evidence/local_review_library.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record))
