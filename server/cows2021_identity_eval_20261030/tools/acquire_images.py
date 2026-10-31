"""Download only frozen540 public crops; per-file CRC, decode and durable journal."""
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import concurrent.futures, hashlib, io, json, os, urllib.request, zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
protocol_file = ROOT / "protocol/run_v1.json"
plan = json.loads(protocol_file.read_text(encoding="utf-8"))
out = ROOT / "input/images"
out.mkdir(parents=True, exist_ok=False)
evidence = ROOT / "evidence"
results = ROOT / "results"
evidence.mkdir(exist_ok=True)
results.mkdir(exist_ok=True)
journal = evidence / "acquisition_rows.jsonl"
assert not journal.exists() and not (results / "acquisition.json").exists()


def acquire(item):
    index, row = item
    record = {"index": index, "phase": row["phase"], "purpose": row["purpose"], "identity_namespace": row["identity_namespace"],
              "publisher_identity": row["publisher_identity"], "date": row["date"], "local_relative_file": row["local_relative_file"]}
    url = plan["source_base_URL"] + row["publisher_identity"] + "/" + row["file_name"]
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
        with opener.open(urllib.request.Request(url, headers={"User-Agent": "cow-research-frozen-identity-v1"}), timeout=25) as response:
            raw = response.read(5000000)
            assert response.status == 200 and len(raw) < 5000000
            record.update({"URL": url, "HTTP_status": response.status, "resolved_URL": response.url, "content_type": response.headers.get("Content-Type")})
        assert len(raw) == row["zip_entry"]["uncompressed_size"]
        assert zlib.crc32(raw) & 0xffffffff == row["zip_entry"]["CRC32"]
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            rgb = image.convert("RGB")
        assert rgb.width > 0 and rgb.height > 0
        path = ROOT / row["local_relative_file"]
        assert path.resolve().is_relative_to(out.resolve()) and not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        record.update({"status": "AUTHOR_JPEG_CRC_AND_RGB_VERIFIED", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                       "WH": list(rgb.size), "RGB_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()})
    except Exception as error:
        record.update({"status": "ACQUISITION_FAILED", "error": repr(error)[:400]})
    return record


records = []
with journal.open("x", encoding="utf-8") as stream, concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for record in pool.map(acquire, enumerate(plan["selected_images"])):
        records.append(record)
        stream.write(json.dumps(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        if len(records) % 60 == 0:
            print(json.dumps({"captured_rows": len(records), "successful": sum(row["status"] == "AUTHOR_JPEG_CRC_AND_RGB_VERIFIED" for row in records), "new_model_forwards": 0}), flush=True)
result = {"status": "FROZEN540_IDENTITY_IMAGE_ACQUISITION_FINISHED", "created_UTC": datetime.now(timezone.utc).isoformat(),
          "protocol_sha256": hashlib.sha256(protocol_file.read_bytes()).hexdigest(), "records": records,
          "new_model_forwards": 0, "new_training_updates": 0, "reserved_date_pixels_opened": False,
          "proxy_or_node_settings_changed": False, "whole_goal_complete": False}
(results / "acquisition.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
failed = [row for row in records if row["status"] != "AUTHOR_JPEG_CRC_AND_RGB_VERIFIED"]
print(json.dumps({"total": len(records), "failed": len(failed), "total_JPEG_bytes": sum(row.get("bytes", 0) for row in records), "new_model_forwards": 0}), flush=True)
assert len(records) == 540 and not failed
