from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];O=ROOT/"results"
manifest_path=O/"BECA_visual_QA_manifest_v1.json"
manifest=json.loads(manifest_path.read_text())
notes=[
    {"QA_indices":[0,1],"publisher_ID":"11","observations":"Dorsal crops with brown/dark coat and small white patches; feeding rails hide head/neck; source timestamp visible in QA0; illumination, fur and camera-relative shape differ.","identity_consistency_adjudicated":False},
    {"QA_indices":[2,3],"publisher_ID":"65","observations":"Brown/tan dorsal body with limited high-contrast pattern; rails cover head/neck, body appearance and light change across dates; source overlay fragment visible in QA3.","identity_consistency_adjudicated":False},
    {"QA_indices":[4,5],"publisher_ID":"100","observations":"Brown-white dorsal pattern visible; rails occlude upper body; rotated crop has black corner/boundary regions and a source overlay fragment; sampled target is not a black-white Holstein passage.","identity_consistency_adjudicated":False},
    {"QA_indices":[6],"publisher_ID":"16_or5_conflict","observations":"One targeted dorsal body with white-brown pattern, rail occlusion and source timestamp; byte-identical alternate ID is5. Visual inspection does not select which label is correct.","identity_consistency_adjudicated":False},
    {"QA_indices":[7],"publisher_ID":"71_or79_conflict","observations":"One targeted brown dorsal body, limited high-contrast pattern and rail occlusion; byte-identical alternate ID is79. Visual inspection does not select which label is correct.","identity_consistency_adjudicated":False}
]
assert sorted(i for n in notes for i in n["QA_indices"])==list(range(8))
for rec in manifest["records"]:
    path=Path(rec["file"]);assert hashlib.sha256(path.read_bytes()).hexdigest()==rec["JPEG_sha256"]
for rec in manifest["pages"]:
    assert hashlib.sha256(Path(rec["file"]).read_bytes()).hexdigest()==rec["sha256"]
out=O/"BECA_visual_review_v1.json";assert not out.exists()
value={"status":"ALL8_FROZEN_QA_IMAGES_VISUALLY_READ_ON_TWO_RENDERED_PAGES_WITH_DORSAL_DOMAIN_AND_ID_CONFLICT_SCOPE",
       "created_UTC":datetime.now(timezone.utc).isoformat(),
       "reviewer_kind":"assistant_visual_QA_not_independent_human_label_adjudication",
       "actually_viewed_pages":[r["file"]for r in manifest["pages"]],"viewed_QA_indices":list(range(8)),
       "manifest_SHA256":hashlib.sha256(manifest_path.read_bytes()).hexdigest(),"notes":notes,
       "interpretation":"Overhead/dorsal source is suitable for further limited identity-component source work; sampled beef-cattle coat/feeding and crop/overlay conditions differ from target Holstein passage. Not a live or continuous counting source.",
       "all_dataset_pixels_audited":False,"whole_dataset_ID_labels_certified":False,"source_true_permanent_IDs_known":False,
       "new_model_forwards":0,"new_training_updates":0,"continuous_passage_GT_obtained":False,"whole_goal_complete":False}
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"viewed_images":8,"new_model_forwards":0}))
