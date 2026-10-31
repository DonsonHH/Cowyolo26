from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "results/source_visual_manifest.json").read_text())
panels = 0
for row in manifest["files"]:
    path = Path(row["file"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    with Image.open(path) as image:
        rendered = image.convert("RGB")
    for panel in row["panels"]:
        path = Path(panel["source_file"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == panel["source_sha256"]
        with Image.open(path) as image:
            expected = image.convert("RGB")
        expected.thumbnail((480, 465), Image.Resampling.BILINEAR)
        x, y, width, height = panel["rect"]
        assert expected.size == (width, height) and rendered.crop((x, y, x+width, y+height)).tobytes() == expected.tobytes()
        panels += 1
assert panels == 12
result = {"status": "TWELVE_PRESELECTED_AUTHOR_CROPS_PIXEL_BOUND_AND_ACTUALLY_VIEWED_BEFORE_FEATURES",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "panels": panels, "actually_viewed": True,
          "files": [{"file": row["file"], "sha256": row["sha256"], "actually_viewed": True} for row in manifest["files"]],
          "visual_findings": "Publisher torso crops show black padding from rotation, blur and large coat variations; retained all selected files. No claim of independently reassigning publisher identity or validating all540 visually.",
          "new_model_forwards": 0, "new_training_updates": 0, "whole_goal_complete": False}
output = ROOT / "results/source_visual_review.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "panels": panels}))
