from pathlib import Path
import hashlib, json, math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
rows = json.loads((ROOT / "results/actual_job_rows.json").read_text())
assert len(rows) == 80
unique = {}
for row in rows:
    key = row["photo_sha256"]
    assert hashlib.sha256(Path(row["photo_file"]).read_bytes()).hexdigest() == key
    unique.setdefault(key, row)
assert len(unique) == 10
photos = sorted(unique.values(), key=lambda row: row["fixed_job_index"])
assert [row["fixed_job_index"] for row in photos] == list(range(10))
dest = ROOT / "results/unique_photo_panels"
dest.mkdir(exist_ok=False)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
files = []
for page in range(math.ceil(len(photos) / 4)):
    canvas = Image.new("RGB", (1000, 1120), "#f4f6f7")
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 12), "Fixed workload | 10 unique photos, 8 repeats each | page" + str(page+1), font=font, fill="#19383d")
    draw.text((16, 40), "Original actual PNGs; source frames from the8912-10873 clip. No permanent identity ground truth.", font=small, fill="#41575b")
    panels = []
    for j, row in enumerate(photos[page*4:page*4+4]):
        path = Path(row["photo_file"])
        with Image.open(path) as image:
            rgb = image.convert("RGB")
        rgb.thumbnail((480, 480), Image.Resampling.BILINEAR)
        x = 15 + (j % 2) * 495 + (480 - rgb.width) // 2
        y = 83 + (j // 2) * 510 + (480 - rgb.height) // 2
        canvas.paste(rgb, (x, y))
        label_x, label_y = 15 + (j % 2) * 495, 83 + (j // 2) * 510 + 484
        draw.text((label_x, label_y), f"fixed job{row['fixed_job_index']} | source f{row['source_frame0']} | repeated8", font=small, fill="#19383d")
        panels.append({"fixed_job_index": row["fixed_job_index"], "source_frame0": row["source_frame0"], "source_file": str(path),
                       "source_sha256": row["photo_sha256"], "rect": [x, y, rgb.width, rgb.height],
                       "all8_occurrences": [{"stage": item["stage"], "run": item["run"], "file": item["photo_file"]} for item in rows if item["photo_sha256"] == row["photo_sha256"]]})
    output = dest / ("page" + str(page+1) + ".png")
    canvas.save(output)
    files.append({"file": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "panels": panels})
manifest = {"files": files, "unique_actual_photos": 10, "all_original_photo_occurrences": 80, "panels": 10,
            "actually_viewed": False, "new_model_forwards": 0}
output = ROOT / "results/visual_manifest.json"
assert not output.exists()
output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in manifest.items() if key != "files"}))
