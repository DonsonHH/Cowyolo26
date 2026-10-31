from pathlib import Path
from datetime import datetime, timezone
import concurrent.futures
import hashlib
import json
import struct
import urllib.request
import zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "protocol/run_v1.json"
plan = json.loads(PROTOCOL.read_text(encoding="utf-8"))
dest = ROOT / "input/test50"
dest.mkdir(exist_ok=False)


def download_range(start, end):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
    request = urllib.request.Request(plan["source_release_asset"]["URL"], headers={"Range": f"bytes={start}-{end}", "User-Agent": "cow-research-frozen-COLO-eval"})
    with opener.open(request, timeout=25) as response:
        expected = f"bytes {start}-{end}/{plan['source_release_asset']['bytes']}"
        assert response.status == 206 and response.headers.get("Content-Range") == expected
        payload = response.read(end - start + 2)
        assert len(payload) == end - start + 1
        return payload, {"Range": f"bytes={start}-{end}", "status": 206, "Content-Range": expected, "bytes": len(payload), "SHA256": hashlib.sha256(payload).hexdigest()}


def acquire(item):
    index, row = item
    record = {"index": index, "file_name": row["file_name"], "image_id": row["image"]["id"], "lighting": row["lighting"]}
    try:
        entry = row["zip_entry"]
        header, hrec = download_range(entry["local_header_offset"], entry["local_header_offset"] + 29)
        fields = struct.unpack("<4s5H3I2H", header)
        assert fields[0] == b"PK\x03\x04" and fields[3] == entry["method"]
        start = entry["local_header_offset"] + 30 + fields[9] + fields[10]
        payload, prec = download_range(start, start + entry["compressed_bytes"] - 1)
        raw = zlib.decompress(payload, -15) if entry["method"] == 8 else payload
        assert len(raw) == entry["uncompressed_bytes"] and zlib.crc32(raw) & 0xffffffff == entry["CRC32"]
        path = dest / row["file_name"]
        path.write_bytes(raw)
        with Image.open(path) as image:
            rgb = image.convert("RGB")
        assert rgb.size == (640, 640)
        record.update({"status": "JPEG_CRC_SIZE_RGB_AND_DIMENSIONS_VERIFIED", "bytes": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest(), "RGB_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
                       "ranges": [hrec, prec], "WH": [640, 640]})
    except Exception as error:
        record.update({"status": "ACQUISITION_FAILED", "error": str(error)[:350]})
    return record


with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    records = list(pool.map(acquire, enumerate(plan["images"])))
result = {"status": "TEST50_ACQUISITION_FINISHED", "created_UTC": datetime.now(timezone.utc).isoformat(),
          "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(), "records": records,
          "new_model_forwards": 0, "existing_final_holdout_opened": False,
          "proxy_or_node_configuration_changed": False, "whole_goal_complete": False}
target = ROOT / "results/test50_acquisition.json"
target.parent.mkdir(exist_ok=True)
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
ok = sum(row["status"] == "JPEG_CRC_SIZE_RGB_AND_DIMENSIONS_VERIFIED" for row in records)
print(json.dumps({"images_verified": ok, "failed": 50 - ok, "downloaded_range_bytes": sum(part["bytes"] for row in records for part in row.get("ranges", [])), "new_model_forwards": 0}))
assert ok == 50
