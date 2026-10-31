"""Resume only the missing admitted JPEGs after original process was absent."""
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
assert dest.is_dir() and not (ROOT / "results/test50_acquisition.json").exists()
existing_names = sorted(path.name for path in dest.glob("*.jpg"))
failure_record = {"created_UTC": datetime.now(timezone.utc).isoformat(),
                  "original_exec_handle": 68884, "handle_missing_on_poll": True,
                  "matching_Win32_python_process_absent_on_direct_inspection": True,
                  "completed_manifest_exists": False, "existing_JPEG_files": existing_names,
                  "original_code_sha256": hashlib.sha256((ROOT / "tools/acquire_test50.py").read_bytes()).hexdigest(),
                  "cause_of_process_exit_not_observed": True,
                  "action": "Verify existing JPEGs against frozen CRC and acquire only missing members; no model work begun."}
evidence = ROOT / "evidence/first_acquisition_process_absent.json"
assert not evidence.exists()
evidence.write_text(json.dumps(failure_record, indent=2) + "\n", encoding="utf-8")


def read_range(start, end):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
    request = urllib.request.Request(plan["source_release_asset"]["URL"], headers={"Range": f"bytes={start}-{end}", "User-Agent": "cow-research-frozen-COLO-eval"})
    with opener.open(request, timeout=25) as response:
        expected = f"bytes {start}-{end}/{plan['source_release_asset']['bytes']}"
        assert response.status == 206 and response.headers.get("Content-Range") == expected
        payload = response.read(end - start + 2)
        assert len(payload) == end - start + 1
    return payload, {"Range": f"bytes={start}-{end}", "status": 206, "Content-Range": expected, "bytes": len(payload), "SHA256": hashlib.sha256(payload).hexdigest()}


def process(item):
    index, row = item
    entry = row["zip_entry"]
    path = dest / row["file_name"]
    reused = path.exists()
    ranges = []
    if reused:
        raw = path.read_bytes()
    else:
        header, hrec = read_range(entry["local_header_offset"], entry["local_header_offset"] + 29)
        fields = struct.unpack("<4s5H3I2H", header)
        assert fields[0] == b"PK\x03\x04" and fields[3] == entry["method"]
        start = entry["local_header_offset"] + 30 + fields[9] + fields[10]
        payload, prec = read_range(start, start + entry["compressed_bytes"] - 1)
        raw = zlib.decompress(payload, -15) if entry["method"] == 8 else payload
        ranges = [hrec, prec]
    assert len(raw) == entry["uncompressed_bytes"] and zlib.crc32(raw) & 0xffffffff == entry["CRC32"]
    if not reused:
        path.write_bytes(raw)
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    assert rgb.size == (640, 640)
    return {"index": index, "file_name": row["file_name"], "image_id": row["image"]["id"], "lighting": row["lighting"],
            "status": "JPEG_CRC_SIZE_RGB_AND_DIMENSIONS_VERIFIED", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "RGB_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(), "WH": [640, 640], "ranges": ranges,
            "existing_original_download_reused": reused,
            "per_request_HTTP_headers_persisted": not reused}


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    records = list(pool.map(process, enumerate(plan["images"])))
assert len(records) == 50 and sum(row["existing_original_download_reused"] for row in records) == len(existing_names)
result = {"status": "TEST50_ACQUISITION_FINISHED_WITH42_EXISTING_FILES_VERIFIED_NOT_REDOWNLOADED",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
          "records": records, "reused_existing_source_JPEGs": len(existing_names), "new_missing_JPEGs_downloaded": 50 - len(existing_names),
          "original_exit_cause_unobserved": True, "all50_source_CRC_and_pixel_hashes_verified": True,
          "all50_HTTP_response_headers_claimed_persisted": False,
          "new_model_forwards": 0, "existing_final_holdout_opened": False,
          "proxy_or_node_configuration_changed": False, "whole_goal_complete": False}
target = ROOT / "results/test50_acquisition.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "reused_existing_source_JPEGs", "new_missing_JPEGs_downloaded", "new_model_forwards"]}))
