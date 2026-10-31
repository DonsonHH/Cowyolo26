"""Recover the index from all50 already downloaded source JPEGs, without HTTP."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
plan_path = ROOT / "protocol/run_v1.json"
plan = json.loads(plan_path.read_text(encoding="utf-8"))
first = json.loads((ROOT / "evidence/first_acquisition_process_absent.json").read_text(encoding="utf-8"))
prior_names = set(first["existing_JPEG_files"])
records = []
for index, row in enumerate(plan["images"]):
    path = ROOT / "input/test50" / row["file_name"]
    raw = path.read_bytes()
    assert len(raw) == row["zip_entry"]["uncompressed_bytes"]
    assert zlib.crc32(raw) & 0xffffffff == row["zip_entry"]["CRC32"]
    with Image.open(path) as source:
        rgb = source.convert("RGB")
    assert rgb.size == (640, 640)
    records.append({"index": index, "file_name": row["file_name"], "image_id": row["image"]["id"], "lighting": row["lighting"],
                    "status": "JPEG_CRC_SIZE_RGB_AND_DIMENSIONS_VERIFIED", "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(), "RGB_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
                    "WH": [640, 640], "already_present_before_missing8_resume": path.name in prior_names,
                    "per_request_HTTP_headers_persisted": False})
assert len(records) == len(list((ROOT / "input/test50").glob("*.jpg"))) == 50
assert len(prior_names) == 42
result = {"status": "ALL50_LOCAL_JPEGS_FROZEN_SOURCE_CRC_AND_RGB_VERIFIED_INDEX_RECOVERED_NO_REDOWNLOAD",
          "created_UTC": datetime.now(timezone.utc).isoformat(), "protocol_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
          "records": records, "original42_reused": 42, "missing8_then_downloaded": 8,
          "original_handle_missing_and_process_absent": True,
          "resume_completed_JPEGs_but_index_write_failed_missing_results_directory": True,
          "recovery_only_local_reads_no_HTTP_requests": True, "per_request_HTTP_headers_not_recovered_from_lost_index": True,
          "new_model_forwards": 0, "existing_final_holdout_opened": False,
          "proxy_or_node_configuration_changed": False, "whole_goal_complete": False}
target = ROOT / "results/test50_acquisition.json"
target.parent.mkdir(exist_ok=True)
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: result[key] for key in ["status", "original42_reused", "missing8_then_downloaded", "new_model_forwards"]}))
