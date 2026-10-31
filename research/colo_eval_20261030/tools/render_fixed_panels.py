from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
plan = json.loads((ROOT / "protocol/run_v1.json").read_text(encoding="utf-8"))
gt = json.loads((ROOT / "input/GT_valid450_clipped.json").read_text(encoding="utf-8"))
selected = [(index, plan["images"][index]) for index in plan["qualitative_image_indices_preselected"]]
dest = ROOT / "results/fixed_panels"
dest.mkdir(exist_ok=False)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
files = []
modes = ["raw", "publisher_GT"] + [model["name"] + "_s" + str(size) for model in plan["models"] for size in plan["sizes"]]
for mode in modes:
    canvas = Image.new("RGB", (1288, 1010), "#f4f6f7")
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 12), "COLO fixed test50 | " + mode, font=font, fill="#19383d")
    draw.text((18, 40), "Indices 0,10,20,30,40,49 frozen before test pixels. Predictions: conf>=0.20; not passage counts.", font=small, fill="#41575b")
    predictions = {} if mode in ["raw", "publisher_GT"] else json.loads((ROOT / "delivery/results/evaluation" / mode / "all_decoded_predictions.json").read_text(encoding="utf-8"))
    panels = []
    for j, (index, item) in enumerate(selected):
        path = ROOT / "input/test50" / item["file_name"]
        with Image.open(path) as image:
            rgb = image.convert("RGB")
        annotations = []
        overlay = ImageDraw.Draw(rgb)
        if mode == "publisher_GT":
            for row in gt["annotations"]:
                if row["image_id"] == item["image"]["id"]:
                    x, y, width, height = row["bbox"]
                    annotations.append({"kind": "publisher_GT", "annotation_id": row["id"], "xyxy": [x, y, x + width, y + height]})
                    overlay.rectangle((x, y, x + width, y + height), outline="#ffbc42", width=3)
        elif mode != "raw":
            for row in predictions[str(item["image"]["id"])]:
                if row["score"] >= .20:
                    annotations.append({"kind": "model_prediction", **row})
                    overlay.rectangle(row["xyxy"], outline="#00e4ef", width=3)
        thumb = rgb.resize((408, 408), Image.Resampling.BILINEAR)
        x, y = 18 + (j % 3) * 422, 92 + (j // 3) * 458
        canvas.paste(thumb, (x, y))
        label = f"index{index} | {item['lighting']} | " + ("raw" if mode == "raw" else f"boxes {len(annotations)}")
        draw.text((x, y + 413), label, font=small, fill="#19383d")
        panels.append({"index": index, "image_id": item["image"]["id"], "source_file": str(path),
                       "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rect": [x, y, 408, 408],
                       "annotations": annotations, "overlay_mode": mode})
    path = dest / (mode + ".png")
    canvas.save(path)
    files.append({"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "panels": panels})
record = {"files": files, "sheets": len(files), "panels": sum(len(row["panels"]) for row in files),
          "selected_source_indices": plan["qualitative_image_indices_preselected"], "actually_viewed": False,
          "new_model_forwards": 0, "contains_GT_overlays_in_model_input": False}
target = ROOT / "results/visual_manifest.json"
assert not target.exists()
target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in record.items() if key != "files"}))
