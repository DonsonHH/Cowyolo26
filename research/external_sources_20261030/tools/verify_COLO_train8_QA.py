"""Read-only independent binding of admitted JPEGs and the four viewed sheets."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zlib
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


plan = read(ROOT / "protocol/COLO_train8_pixel_admission_v1.json")
acquired = read(ROOT / "results/COLO_train8_acquisition.json")
manifest = read(ROOT / "results/COLO_train8_visual_manifest.json")
audit = read(ROOT / "results/COLO_annotation_audit.json")
assert len(plan["selected_rows"]) == len(acquired["records"]) == 8
test_names = {row["file_name"] for row in audit["official_test_rows"]}
checks = []
for index, (planned, actual) in enumerate(zip(plan["selected_rows"], acquired["records"])):
    path = Path(actual["file"])
    payload = path.read_bytes()
    assert actual["index"] == index
    assert path.name == planned["file_name"] and path.name not in test_names
    assert actual["archive_member"] == planned["archive_member"]
    assert actual["annotations"] == planned["annotations"]
    assert len(payload) == planned["zip_entry"]["uncompressed_bytes"] == actual["bytes"]
    assert zlib.crc32(payload) & 0xffffffff == planned["zip_entry"]["CRC32"]
    assert sha(path) == actual["sha256"]
    with Image.open(path) as source:
        rgb = source.convert("RGB")
    assert list(rgb.size) == actual["WH"] == [640, 640]
    assert hashlib.sha256(rgb.tobytes()).hexdigest() == actual["decoded_RGB_sha256"]
    checks.append({"index": index, "file": str(path), "sha256": sha(path),
                   "publisher_boxes": len(planned["annotations"]), "CRC32_verified": True,
                   "metadata_and_RGB_verified": True, "publisher_test_overlap": False})

panel_count = 0
for sheet in manifest["files"]:
    assert sha(Path(sheet["file"])) == sheet["sha256"]
    with Image.open(sheet["file"]) as image:
        rendered = image.convert("RGB")
    for panel in sheet["panels"]:
        row = acquired["records"][panel["index"]]
        assert panel["source_sha256"] == row["sha256"] == sha(Path(panel["source_file"]))
        with Image.open(panel["source_file"]) as image:
            expected = image.convert("RGB")
        if panel["overlay_mode"] == "publisher_GT":
            draw = ImageDraw.Draw(expected)
            for annotation in plan["selected_rows"][panel["index"]]["annotations"]:
                x, y, width, height = annotation["bbox"]
                color = "#ffbc42" if min(width, height) > 0 else "#ff4040"
                draw.rectangle((x, y, x + width, y + height), outline=color, width=2)
        else:
            assert panel["overlay_mode"] == "raw"
        expected = expected.resize((480, 480), Image.Resampling.BILINEAR)
        x, y, width, height = panel["rect"]
        assert [width, height] == [480, 480]
        assert rendered.crop((x, y, x + width, y + height)).tobytes() == expected.tobytes()
        panel_count += 1
assert panel_count == 16 and len(manifest["files"]) == 4
assert len(list((ROOT / "input/COLO_train8_QA").glob("*.jpg"))) == 8

result = {
    "status": "EIGHT_TRAIN_JPEGS_CRC_RGB_AND16_RAW_GT_SHEET_PANELS_INDEPENDENTLY_VERIFIED",
    "created_UTC": datetime.now(timezone.utc).isoformat(),
    "source_images": 8, "publisher_boxes": sum(row["publisher_boxes"] for row in checks),
    "sheets": 4, "panels": panel_count, "checks": checks,
    "actually_viewed": True,
    "viewing_evidence": "Four local view_image calls after acquisition: raw_page1, publisher_GT_page1, raw_page2, publisher_GT_page2; assistant visual review, not independent human relabeling.",
    "visual_findings": [
        "High-mounted overhead feeding alley, substantial wide-angle distortion and peripheral oblique views; not an exact match for a strictly vertical gate camera.",
        "Eight train images cover daylight, indoor light and infrared; black-white and brown cows, partial border cows, rail occlusion and low infrared contrast are visible.",
        "Raw panels contain no publisher boxes; orange overlays belong only to the separate publisher-GT sheets.",
        "GT is author detection annotation, including inferred hidden extents; visual viewing does not certify all labels or add permanent identities or passage events."
    ],
    "files": [{"file": row["file"], "sha256": row["sha256"], "actually_viewed": True} for row in manifest["files"]],
    "test50_pixels_requested": False, "new_model_forwards": 0,
    "new_training_updates": 0, "independent_human_review": False, "whole_goal_complete": False,
    "evidence_hashes": {relative: sha(ROOT / relative) for relative in [
        "protocol/COLO_train8_pixel_admission_v1.json", "results/COLO_train8_acquisition.json",
        "results/COLO_train8_visual_manifest.json", "results/COLO_annotation_audit.json"]}
}
output = ROOT / "results/COLO_train8_visual_review.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "source_images", "publisher_boxes", "panels", "actually_viewed", "new_model_forwards"]}))
