from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "results/visual_manifest.json").read_text())
count = occurrences = 0
for sheet in manifest["files"]:
    path = Path(sheet["file"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sheet["sha256"]
    with Image.open(path) as image:
        rendered = image.convert("RGB")
    for panel in sheet["panels"]:
        with Image.open(panel["source_file"]) as image:
            expected = image.convert("RGB")
        expected.thumbnail((480, 480), Image.Resampling.BILINEAR)
        x, y, width, height = panel["rect"]
        assert expected.size == (width, height) and rendered.crop((x, y, x+width, y+height)).tobytes() == expected.tobytes()
        assert len(panel["all8_occurrences"]) == 8
        for source in panel["all8_occurrences"]:
            assert hashlib.sha256(Path(source["file"]).read_bytes()).hexdigest() == panel["source_sha256"]
            occurrences += 1
        count += 1
assert count == 10 and occurrences == 80
result = {"status": "TEN_UNIQUE_ORIGINAL_PHOTOS_ACTUALLY_VIEWED_AND_ALL80_OCCURRENCES_PIXEL_HASH_BOUND",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "unique_actual_photos": 10, "all80_original_occurrences_verified": True,
          "panels": count, "actually_viewed": True,
          "files": [{"file": row["file"], "sha256": row["sha256"], "actually_viewed": True} for row in manifest["files"]],
          "viewing_evidence": "Three separate local view_image calls on the final unique_photo_panels page1/page2/page3; 10 distinct original PNGs, each mapped to all8 exact repeated occurrences.",
          "visual_findings": "Some photos show body clipping, neighbouring cows or blur; no new quality labels, identity truth or image exclusions are inferred from this viewing.",
          "new_identity_ground_truth": False, "new_model_forwards": 0, "whole_goal_complete": False}
target = ROOT / "results/visual_review.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "unique_actual_photos", "all80_original_occurrences_verified", "actually_viewed"]}))
