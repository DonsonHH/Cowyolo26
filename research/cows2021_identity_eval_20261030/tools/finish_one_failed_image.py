from pathlib import Path
from datetime import datetime, timezone
import copy, hashlib, io, json, urllib.request, zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
original = json.loads((ROOT / "results/acquisition.json").read_text())
plan = json.loads((ROOT / "protocol/run_v1.json").read_text())
failed = [row for row in original["records"] if row["status"] == "ACQUISITION_FAILED"]
assert len(failed) == 1 and failed[0]["index"] == 499 and "SSLEOFError" in failed[0]["error"]
for row in original["records"]:
    if row["index"] == 499:
        continue
    assert hashlib.sha256((ROOT / row["local_relative_file"]).read_bytes()).hexdigest() == row["sha256"]
row = plan["selected_images"][499]
path = ROOT / row["local_relative_file"]
assert not path.exists()
url = plan["source_base_URL"] + row["publisher_identity"] + "/" + row["file_name"]
opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
with opener.open(urllib.request.Request(url, headers={"User-Agent": "cow-research-same-frozen-identity-retry"}), timeout=25) as response:
    raw = response.read()
    assert response.status == 200
    record = {"URL": url, "HTTP_status": response.status, "resolved_URL": response.url, "content_type": response.headers.get("Content-Type")}
assert len(raw) == row["zip_entry"]["uncompressed_size"] and zlib.crc32(raw) & 0xffffffff == row["zip_entry"]["CRC32"]
with Image.open(io.BytesIO(raw)) as image:
    rgb = image.convert("RGB")
path.parent.mkdir(exist_ok=True)
path.write_bytes(raw)
replacement = {key: value for key, value in failed[0].items() if key not in ["error", "status"]}
replacement.update({**record, "status": "AUTHOR_JPEG_CRC_AND_RGB_VERIFIED", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                    "WH": list(rgb.size), "RGB_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(), "same_frozen_image_retry_after_TLS_EOF": True})
result = copy.deepcopy(original)
result["records"][499] = replacement
result.update({"status": "ALL540_FROZEN_JPEGS_COMPLETE539_REUSED_ONE_TLS_EOF_RETRIED",
               "created_UTC": datetime.now(timezone.utc).isoformat(), "previous_incomplete_acquisition_sha256": hashlib.sha256((ROOT / "results/acquisition.json").read_bytes()).hexdigest(),
               "previous539_images_reused_without_redownload": True, "image_members_or_selection_replaced": False})
output = ROOT / "results/acquisition_v2.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "total_JPEG_bytes": sum(row["bytes"] for row in result["records"]), "new_model_forwards": 0}))
