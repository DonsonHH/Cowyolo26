from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
import hashlib, json, zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


plan = load(ROOT / "protocol/run_v1.json")
acquisition = load(ROOT / "results/acquisition_v2.json")
assert acquisition["protocol_sha256"] == hashlib.sha256((ROOT / "protocol/run_v1.json").read_bytes()).hexdigest()
assert len(acquisition["records"]) == 540
old_manifest = load(PROJECT / "identity_training_20261026/delivery/results/input_audit/manifest.json")
old_pixels = {row["pixel_sha256"] for row in old_manifest}
pixels = defaultdict(list)
prior_overlap = []
verified = []
for index, (row, source) in enumerate(zip(plan["selected_images"], acquisition["records"])):
    assert source["index"] == index and source["status"] == "AUTHOR_JPEG_CRC_AND_RGB_VERIFIED"
    path = ROOT / row["local_relative_file"]
    raw = path.read_bytes()
    assert len(raw) == row["zip_entry"]["uncompressed_size"] == source["bytes"]
    assert zlib.crc32(raw) & 0xffffffff == row["zip_entry"]["CRC32"]
    assert hashlib.sha256(raw).hexdigest() == source["sha256"]
    with Image.open(path) as image:
        image.load()
        rgb = image.convert("RGB")
    assert list(rgb.size) == source["WH"] and hashlib.sha256(rgb.tobytes()).hexdigest() == source["RGB_sha256"]
    canonical = hashlib.sha256(rgb.width.to_bytes(4, "big") + rgb.height.to_bytes(4, "big") + rgb.tobytes()).hexdigest()
    if canonical in old_pixels:
        prior_overlap.append(index)
    pixels[canonical].append({"index": index, "identity_namespace": row["identity_namespace"], "phase": row["phase"], "purpose": row["purpose"]})
    verified.append({"index": index, "canonical_pixel_sha256": canonical, "width": rgb.width, "height": rgb.height,
                     "CRC32_verified": True, "phase": row["phase"], "purpose": row["purpose"], "identity_namespace": row["identity_namespace"]})
duplicates = [{"canonical_pixel_sha256": key, "members": rows} for key, rows in pixels.items() if len(rows) > 1]
cross = [row for row in duplicates if len({item["identity_namespace"] for item in row["members"]}) > 1 or len({(item["phase"], item["purpose"]) for item in row["members"]}) > 1]
assert not prior_overlap and not cross
roles = plan["roles"]
assert len(set(sum(roles.values(), []))) == 120
assert all(row["date"] <= "2020-03-04" and row["day_gap"] >= 7 for row in plan["selected_images"])
result = {"status": "ALL540_FROZEN_CROPS_CRC_PIXELS_AND_ROLE_DUPLICATE_CHECKS_PASS",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "admitted_for_fixed_feature_study": True,
          "images": len(verified), "images_by_phase": dict(Counter(row["phase"] for row in verified)),
          "images_by_purpose": dict(Counter(row["purpose"] for row in verified)),
          "cross_identity_or_gallery_query_exact_pixel_duplicate_groups": cross,
          "within_same_ID_role_exact_pixel_duplicate_groups": duplicates,
          "exact_pixel_overlap_with_previous750_identity_inputs": prior_overlap,
          "previous_identity_input_manifest_sha256": hashlib.sha256((PROJECT / "identity_training_20261026/delivery/results/input_audit/manifest.json").read_bytes()).hexdigest(),
          "width_range": [min(row["width"] for row in verified), max(row["width"] for row in verified)],
          "height_range": [min(row["height"] for row in verified), max(row["height"] for row in verified)],
          "rows": verified, "new_model_forwards": 0, "new_training_updates": 0, "reserved_date_pixels_opened": False,
          "does_not_prove_physical_cross_dataset_identity_or_detector_independence": True, "whole_goal_complete": False}
output = ROOT / "results/pixel_admission.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key != "rows"}))
