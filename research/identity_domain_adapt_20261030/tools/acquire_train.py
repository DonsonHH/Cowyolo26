from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import concurrent.futures, hashlib, io, json, os, urllib.error, urllib.request, zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
plan = json.loads((ROOT / "protocol/run_v1.json").read_text())
dest = ROOT / "input/cows_train"
dest.mkdir(parents=True, exist_ok=False)
prior = json.loads((PROJECT / "cows2021_identity_eval_20261030/results/pixel_admission.json").read_text())
old = json.loads((PROJECT / "identity_training_20261026/delivery/results/input_audit/manifest.json").read_text())
old_pixels = {row["canonical_pixel_sha256"] for row in prior["rows"]} | {row["pixel_sha256"] for row in old}


def acquire(item):
    index, row = item
    record = {"index": index,"relative_file":row["relative_file"],"identity":row["identity"],"day":row["day"],"attempts":[]}
    for attempt in range(2):
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http":"http://127.0.0.1:7897","https":"http://127.0.0.1:7897"}))
            with opener.open(urllib.request.Request(row["URL"],headers={"User-Agent":"cow-research-frozen-new-train-IDs"}),timeout=25) as response:
                raw=response.read(5000000);assert response.status==200 and len(raw)<5000000
                attempt_record={"attempt":attempt+1,"HTTP_status":response.status,"URL":response.url}
            assert len(raw)==row["zip_entry"]["uncompressed_size"] and zlib.crc32(raw)&0xffffffff==row["zip_entry"]["CRC32"]
            with Image.open(io.BytesIO(raw)) as image:
                image.load();rgb=image.convert("RGB")
            pixel=hashlib.sha256(rgb.width.to_bytes(4,"big")+rgb.height.to_bytes(4,"big")+rgb.tobytes()).hexdigest()
            assert pixel not in old_pixels,"exact_pixel_overlap_previous_identity_inputs"
            path=(ROOT/row["relative_file"]).resolve();assert path.is_relative_to(dest.resolve()) and not path.exists()
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            record["attempts"].append({**attempt_record,"status":"SUCCESS"})
            record.update({"status":"NEW_TRAIN_JPEG_CRC_RGB_AND_PRIOR_PIXEL_OVERLAP_PASS","bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
                           "WH":list(rgb.size),"canonical_pixel_sha256":pixel})
            return record
        except (urllib.error.URLError,TimeoutError) as error:
            record["attempts"].append({"attempt":attempt+1,"status":"NETWORK_ERROR","error":repr(error)[:350]})
            if isinstance(error,urllib.error.HTTPError) or attempt==1:
                break
        except Exception as error:
            record["attempts"].append({"attempt":attempt+1,"status":"ADMISSION_FAILED","error":repr(error)[:350]})
            break
    record["status"]="FAILED_NO_IMAGE_REPLACEMENT"
    return record


records=[]
with (ROOT/"evidence/acquisition_rows.jsonl").open("x",encoding="utf-8") as journal,concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for row in pool.map(acquire,enumerate(plan["Cows_training_images"])):
        records.append(row);journal.write(json.dumps(row)+"\n");journal.flush();os.fsync(journal.fileno())
        if len(records)%60==0:
            print(json.dumps({"rows":len(records),"success":sum(row["status"]=="NEW_TRAIN_JPEG_CRC_RGB_AND_PRIOR_PIXEL_OVERLAP_PASS" for row in records),"new_model_forwards":0}),flush=True)
failures=[row for row in records if row["status"]!="NEW_TRAIN_JPEG_CRC_RGB_AND_PRIOR_PIXEL_OVERLAP_PASS"]
pixels=defaultdict(list)
for row in records:
    if "canonical_pixel_sha256" in row:
        pixels[row["canonical_pixel_sha256"]].append(row["index"])
result={"status":"FROZEN457_TRAIN_IMAGE_DOWNLOAD_AND_PIXEL_ADMISSION_FINISHED","created_UTC":datetime.now(timezone.utc).isoformat(),
        "protocol_sha256":hashlib.sha256((ROOT/"protocol/run_v1.json").read_bytes()).hexdigest(),"records":records,"failed_images":len(failures),
        "same_pixel_duplicate_groups":[indices for indices in pixels.values() if len(indices)>1],
        "prior540_and750_exact_pixel_overlap":0 if not failures else None,"future20_ID_pixels_opened":False,
        "new_model_forwards":0,"proxy_or_node_settings_changed":False,"whole_goal_complete":False}
(ROOT/"results/acquisition.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"images":len(records),"failures":len(failures),"bytes":sum(row.get("bytes",0) for row in records),"duplicate_groups":len(result["same_pixel_duplicate_groups"])}),flush=True)
assert len(records)==457 and not failures and not result["same_pixel_duplicate_groups"]
