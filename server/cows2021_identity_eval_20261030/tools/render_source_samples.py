from pathlib import Path
import hashlib, json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
plan = json.loads((ROOT / "protocol/run_v1.json").read_text())
dest = ROOT / "results/source_panels"
dest.mkdir(exist_ok=False)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
indices = plan["qualitative_source_indices"]
assert len(indices) == 12
files = []
for page in range(3):
    canvas = Image.new("RGB", (1000, 1120), "#f4f6f7")
    draw = ImageDraw.Draw(canvas)
    draw.text((15, 12), "Cows2021 frozen source QA | publisher crops | page" + str(page+1), font=font, fill="#19383d")
    draw.text((15, 40), "Indices fixed before JPEG acquisition; no predictions, no quality-based exclusions.", font=small, fill="#41575b")
    panels = []
    for j, index in enumerate(indices[page*4:page*4+4]):
        row = plan["selected_images"][index]
        path = ROOT / row["local_relative_file"]
        with Image.open(path) as image:
            rgb = image.convert("RGB")
        rgb.thumbnail((480, 465), Image.Resampling.BILINEAR)
        x = 15 + (j % 2) * 495 + (480 - rgb.width)//2
        y = 83 + (j // 2) * 510 + (465 - rgb.height)//2
        canvas.paste(rgb, (x, y))
        left = 15 + (j % 2) * 495
        label_y = 83 + (j // 2) * 510 + 469
        draw.text((left, label_y), f"index{index} | Cows2021 ID{row['publisher_identity']} | {row['date']}", font=small, fill="#19383d")
        draw.text((left, label_y+17), row["phase"] + " / " + row["purpose"], font=small, fill="#19383d")
        panels.append({"source_index": index, "source_file": str(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rect": [x, y, rgb.width, rgb.height]})
    output = dest / ("page" + str(page+1) + ".png")
    canvas.save(output)
    files.append({"file": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "panels": panels})
output = ROOT / "results/source_visual_manifest.json"
assert not output.exists()
output.write_text(json.dumps({"files": files, "panels": 12, "actually_viewed": False, "new_model_forwards": 0}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"sheets": 3, "panels": 12, "new_model_forwards": 0}))
