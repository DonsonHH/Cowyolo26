from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
protocol = {"status": "POSTHOC_RETRIEVAL_EXPLANATION_SELECTION_BEFORE_RENDERING", "created_UTC": datetime.now(timezone.utc).isoformat(),
            "model": "C_trained_seed26", "threshold_policy": "Cows2021_calibrated",
            "categories": ["known_correct_accepted", "known_wrong_accepted", "known_rejected", "unknown_false_accepted"],
            "selection": "Lowest frozen source index in each nonempty category; best predicted gallery reference by frozen cosine, true gallery reference first source index",
            "not_an_unbiased_performance_sample": True, "new_model_forwards": 0}
out = ROOT / "protocol/retrieval_visual_v1.json"
assert not out.exists()
out.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
plan = json.loads((ROOT / "protocol/run_v1.json").read_text())
all_rows = plan["selected_images"]
rows = json.loads((ROOT / "delivery/results/evaluation/evaluation/C_trained_seed26/Cows2021_calibrated_decisions.json").read_text())
evaluation_indices = [index for index, row in enumerate(all_rows) if row["phase"] == "evaluation"]
with np.load(ROOT / "delivery/results/evaluation/evaluation/C_trained_seed26/all_features.npz") as archive:
    normalized = archive["normalized"].copy().astype(float)
position = {index: number for number, index in enumerate(evaluation_indices)}
categories = {
    "known_correct_accepted": lambda row: row["is_known"] and row["accepted"] and row["predicted_id"] == row["identity"],
    "known_wrong_accepted": lambda row: row["is_known"] and row["accepted"] and row["predicted_id"] != row["identity"],
    "known_rejected": lambda row: row["is_known"] and not row["accepted"],
    "unknown_false_accepted": lambda row: not row["is_known"] and row["accepted"]}
cases = []
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
dest = ROOT / "results/retrieval_case_panels"
dest.mkdir(exist_ok=False)
files = []
for category, predicate in categories.items():
    candidates = sorted([row for row in rows if predicate(row)], key=lambda row: row["source_index"])
    assert candidates
    query = candidates[0]
    refs = [index for index in evaluation_indices if all_rows[index]["purpose"] == "gallery" and all_rows[index]["identity_namespace"] == query["predicted_id"]]
    predicted_ref = sorted(refs, key=lambda index: (-float(normalized[position[query["source_index"]]] @ normalized[position[index]]), index))[0]
    truth_refs = sorted(index for index in evaluation_indices if all_rows[index]["purpose"] == "gallery" and all_rows[index]["identity_namespace"] == query["identity"])
    truth_ref = truth_refs[0] if truth_refs else None
    canvas = Image.new("RGB", (1480, 560), "#f4f6f7")
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 12), "Cows2021 cropped query | " + category + " | posthoc explanation", font=font, fill="#19383d")
    draw.text((18, 42), f"Query source{query['source_index']}, publisher ID{query['publisher_identity']}; predicted {query['predicted_id'].split(':')[-1]}, score{query['similarity']:.6f}", font=small, fill="#41575b")
    panels = []
    for column, (label, index) in enumerate([("query", query["source_index"]), ("best predicted gallery", predicted_ref), ("publisher truth gallery" if truth_ref is not None else "unknown: no registered truth gallery", truth_ref)]):
        left = 18 + column * 488
        draw.text((left, 85), label, font=small, fill="#19383d")
        if index is None:
            continue
        row = all_rows[index]
        path = ROOT / row["local_relative_file"]
        with Image.open(path) as image:
            rgb = image.convert("RGB")
        rgb.thumbnail((464, 350), Image.Resampling.BILINEAR)
        x, y = left + (464-rgb.width)//2, 112 + (350-rgb.height)//2
        canvas.paste(rgb, (x,y))
        draw.text((left, 480), f"source{index} | ID{row['publisher_identity']} | {row['date']}", font=small, fill="#19383d")
        panels.append({"source_index": index, "source_file": str(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rect": [x,y,rgb.width,rgb.height]})
    path = dest / (category + ".png")
    canvas.save(path)
    files.append({"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "category": category, "panels": panels})
    cases.append({"category": category, "query": query, "best_predicted_gallery_source_index": predicted_ref, "publisher_truth_gallery_source_index": truth_ref})
manifest = {"files": files, "cases": cases, "sheets": 4, "panels": sum(len(row["panels"]) for row in files),
            "actually_viewed": False, "posthoc_selected_cases_not_metric_sample": True, "new_model_forwards": 0}
output = ROOT / "results/retrieval_visual_manifest.json"
assert not output.exists()
output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"case_sheets": 4, "panels": manifest["panels"], "new_model_forwards": 0}))
