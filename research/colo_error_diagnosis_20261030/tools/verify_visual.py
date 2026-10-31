from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "results/visual_manifest_final.json").read_text())
cases = json.loads((ROOT / "results/selected_192_cases.json").read_text())
assert len(cases) == 13 and len(manifest["files"]) == 3
panels = 0
for sheet in manifest["files"]:
    path = Path(sheet["file"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sheet["sha256"]
    with Image.open(path) as image:
        rendered = image.convert("RGB")
    for panel in sheet["panels"]:
        source = Path(panel["source_file"])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == panel["source_sha256"]
        row = cases[panel["case_index"]]
        assert source.name == row["file_name"]
        with Image.open(source) as image:
            expected = image.convert("RGB")
        draw = ImageDraw.Draw(expected)
        for mark in panel["marks"]:
            draw.rectangle(mark["xyxy"], outline=mark["color"], width=mark["width"])
        x, y, width, height = panel["rect"]
        expected = expected.resize((width, height), Image.Resampling.BILINEAR)
        assert rendered.crop((x, y, x+width, y+height)).tobytes() == expected.tobytes()
        witness = panel["category_witness"]
        if row["kind"] == "GT_FN" and row["category"] != "no_geometry_in_retained300":
            assert witness is not None and witness["IoU"] >= .50
            if row["category"] == "cow_score_0_001_to_0_20":
                assert .001 <= witness["score"] < .20
            elif row["category"] == "cow_score_below_0_001":
                assert witness["score"] < .001
            assert any(mark["xyxy"] == witness["xyxy"] and mark["color"] == "#ef44eb" for mark in panel["marks"])
        panels += 1
assert panels == 13
result = {"status": "ALL13_NATIVE_SOURCE_CASE_PANELS_PIXEL_BOUND_WITH_SCORE_BAND_WITNESSES_ACTUALLY_VIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "panels": panels, "actually_viewed": True,
          "files": [{"file": row["file"], "sha256": row["sha256"], "actually_viewed": True} for row in manifest["files"]],
          "viewing_evidence": "Three separate view_image calls on final page1/page2/page3; previous v1 and unwrapped sheets retained but not counted as final review.",
          "findings": ["Highest-IoU cow candidate and score-band witness can differ; both are now separately marked and captioned.",
                       "Some formal IoU false positives cover the visible torso within a larger author cow box; viewing does not relabel them as TP.",
                       "Partial border cows and interior objects both occur; no independent physical-cow or identity labels added."],
          "new_model_forwards": 0, "whole_goal_complete": False}
target = ROOT / "results/visual_review.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "panels": panels}))
