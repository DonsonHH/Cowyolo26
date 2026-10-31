from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
source = Path(json.loads((ROOT / "protocol/run_v1.json").read_text())["source_directory"])
rows = json.loads((ROOT / "results/selected_192_cases.json").read_text())
gt = json.loads((source / "input/GT_valid450_clipped.json").read_text())
dest = ROOT / "results/case_panels"
dest.mkdir(exist_ok=False)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)
files = []
for page in range(math.ceil(len(rows) / 6)):
    canvas = Image.new("RGB", (1288, 1050), "#f4f6f7")
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 12), f"COLO retained-output diagnosis | cases {page*6+1}-{min(len(rows),(page+1)*6)} of{len(rows)}", font=font, fill="#19383d")
    draw.text((18, 40), "Orange GT, cyan best retained cow, magenta best any-class. GT-based diagnostic choices; not a deployment result.", font=small, fill="#41575b")
    panels = []
    for j, row in enumerate(rows[page*6:page*6+6]):
        path = source / "input/test50" / row["file_name"]
        with Image.open(path) as image:
            rgb = image.convert("RGB")
        overlay = ImageDraw.Draw(rgb)
        marks = []
        if row["kind"] == "GT_FN":
            marks.append({"xyxy": row["GT_xyxy"], "color": "#ffbc42", "width": 4})
            if row["best_anyclass_geometry"] is not None:
                marks.append({"xyxy": row["best_anyclass_geometry"]["xyxy"], "color": "#ef44eb", "width": 2})
            if row["best_cow_geometry"] is not None:
                marks.append({"xyxy": row["best_cow_geometry"]["xyxy"], "color": "#00e4ef", "width": 2})
            label = f"ann{row['annotation_id']} | {row['category']}"
            candidate = row["best_cow_geometry"]
            detail = "no retained cow box" if candidate is None else f"cow IoU{candidate['IoU']:.3f}, score{candidate['score']:.3g}"
        else:
            for annotation in gt["annotations"]:
                if annotation["image_id"] == row["image_id"]:
                    x, y, width, height = annotation["bbox"]
                    marks.append({"xyxy": [x, y, x + width, y + height], "color": "#ffbc42", "width": 2})
            marks.append({"xyxy": row["xyxy"], "color": "#00e4ef", "width": 4})
            label = f"FP raw{row['raw_index']} | maxGTIoU{row['maximum_GT_IoU']:.3f}"
            detail = f"score{row['score']:.3g} | {row['FP_category']}"
        for mark in marks:
            overlay.rectangle(mark["xyxy"], outline=mark["color"], width=mark["width"])
        thumb = rgb.resize((408, 408), Image.Resampling.BILINEAR)
        x, y = 18 + (j % 3) * 422, 104 + (j // 3) * 470
        canvas.paste(thumb, (x, y))
        draw.text((x, y - 22), row["condition"], font=small, fill="#19383d")
        draw.text((x, y + 413), label, font=small, fill="#19383d")
        draw.text((x, y + 431), detail, font=small, fill="#19383d")
        panels.append({"case_index": page*6+j, "source_file": str(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rect": [x, y, 408, 408], "marks": marks})
    path = dest / ("page" + str(page+1) + ".png")
    canvas.save(path)
    files.append({"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "panels": panels})
manifest = {"created_UTC": datetime.now(timezone.utc).isoformat(), "files": files, "panels": len(rows), "actually_viewed": False, "new_model_forwards": 0}
target = ROOT / "results/visual_manifest.json"
assert not target.exists()
target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"sheets": len(files), "panels": len(rows)}))
