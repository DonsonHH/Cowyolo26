from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
plan = json.loads((ROOT / "protocol/run_v1.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "results/visual_manifest.json").read_text(encoding="utf-8"))
assert manifest["selected_source_indices"] == [0, 10, 20, 30, 40, 49]
panels = 0
for sheet in manifest["files"]:
    path = Path(sheet["file"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sheet["sha256"]
    with Image.open(path) as image:
        rendered = image.convert("RGB")
    assert [row["index"] for row in sheet["panels"]] == plan["qualitative_image_indices_preselected"]
    for row in sheet["panels"]:
        source = Path(row["source_file"])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == row["source_sha256"]
        with Image.open(source) as image:
            expected = image.convert("RGB")
        draw = ImageDraw.Draw(expected)
        for annotation in row["annotations"]:
            color = "#ffbc42" if annotation["kind"] == "publisher_GT" else "#00e4ef"
            draw.rectangle(annotation["xyxy"], outline=color, width=3)
        x, y, width, height = row["rect"]
        expected = expected.resize((width, height), Image.Resampling.BILINEAR)
        assert rendered.crop((x, y, x + width, y + height)).tobytes() == expected.tobytes()
        if row["overlay_mode"] not in ["raw", "publisher_GT"]:
            predictions = json.loads((ROOT / "delivery/results/evaluation" / row["overlay_mode"] / "all_decoded_predictions.json").read_text(encoding="utf-8"))
            assert [{key: value for key, value in annotation.items() if key != "kind"} for annotation in row["annotations"]] == [prediction for prediction in predictions[str(row["image_id"])] if prediction["score"] >= .20]
        panels += 1
assert panels == 66 and len(manifest["files"]) == 11
result = {"status": "ELEVEN_FIXED_SHEETS66_PANELS_PIXEL_BOUND_AND_ACTUALLY_VIEWED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "sheets": 11, "panels": panels,
          "actually_viewed": True, "selected_indices_frozen_before_test_pixels": [0, 10, 20, 30, 40, 49],
          "files": [{"file": row["file"], "sha256": row["sha256"], "actually_viewed": True} for row in manifest["files"]],
          "viewing_evidence": "Eleven separate local view_image calls: raw, publisher_GT, official192/256/320, old192/256/320, new192/256/320; assistant viewing, not independent relabeling.",
          "visual_findings": [
              "Many partial feeding cows at the upper border and rail occlusion are present; GT covers author-defined detection objects, not completed passages.",
              "Fixed0.20 examples show extensive omissions in all models; larger inputs do not recover every feeding cow.",
              "Old320 also predicts some rails/background; new192/256 often has fewer displayed false candidates, with omissions retained.",
              "Body-trained boxes can be smaller than author reference boxes; this is a visible possible domain mismatch, not a proven sole cause of low AP."
          ], "new_model_forwards": 0, "independent_human_review": False, "whole_goal_complete": False}
target = ROOT / "results/visual_review.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "sheets", "panels", "actually_viewed"]}))
