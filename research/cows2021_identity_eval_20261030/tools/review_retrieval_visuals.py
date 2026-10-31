from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
plan = json.loads((ROOT / "protocol/run_v1.json").read_text())
manifest = json.loads((ROOT / "results/retrieval_visual_manifest.json").read_text())
rows = plan["selected_images"]
evaluation_indices = [index for index, row in enumerate(rows) if row["phase"] == "evaluation"]
with np.load(ROOT / "delivery/results/evaluation/evaluation/C_trained_seed26/all_features.npz") as archive:
    features = archive["normalized"].astype(float)
position = {index: number for number, index in enumerate(evaluation_indices)}
panels = 0
for sheet, case in zip(manifest["files"], manifest["cases"]):
    path = Path(sheet["file"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sheet["sha256"]
    with Image.open(path) as image:
        rendered = image.convert("RGB")
    query = case["query"]
    predicted_ref = case["best_predicted_gallery_source_index"]
    assert rows[predicted_ref]["identity_namespace"] == query["predicted_id"] and rows[predicted_ref]["purpose"] == "gallery"
    gallery_indices = [index for index in evaluation_indices if rows[index]["purpose"] == "gallery" and rows[index]["identity_namespace"] == query["predicted_id"]]
    similarities = [float(features[position[query["source_index"]]] @ features[position[index]]) for index in gallery_indices]
    assert abs(float(features[position[query["source_index"]]] @ features[position[predicted_ref]])-max(similarities)) < 1e-12
    if case["publisher_truth_gallery_source_index"] is not None:
        assert rows[case["publisher_truth_gallery_source_index"]]["identity_namespace"] == query["identity"]
    else:
        assert not query["is_known"]
    for panel in sheet["panels"]:
        source = Path(panel["source_file"])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == panel["source_sha256"]
        with Image.open(source) as image:
            expected = image.convert("RGB")
        expected.thumbnail((464, 350), Image.Resampling.BILINEAR)
        x, y, width, height = panel["rect"]
        assert expected.size == (width, height) and rendered.crop((x,y,x+width,y+height)).tobytes() == expected.tobytes()
        panels += 1
assert panels == 11 and len(manifest["files"]) == 4
result = {"status": "FOUR_POSTHOC_QUERY_CASES11_SOURCE_PANELS_AND_PREDICTED_GALLERY_BINDINGS_ACTUALLY_VIEWED_VERIFIED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "cases": 4, "panels": 11, "actually_viewed": True,
          "files": [{"file": row["file"], "sha256": row["sha256"], "actually_viewed": True} for row in manifest["files"]],
          "posthoc_examples_not_independent_performance_sample": True,
          "visual_findings": "Retained known correct acceptance, wrong-ID acceptance, rejection and unknown false acceptance. Publisher labels remain source GT; similar visual coat coverage is not relabeled as same animal. Blur and crop changes present.",
          "new_model_forwards": 0, "whole_goal_complete": False}
output = ROOT / "results/retrieval_visual_review.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "cases", "panels", "actually_viewed"]}))
