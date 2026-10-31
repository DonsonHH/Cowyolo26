from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest_path=ROOT/"results/visual_panels_manifest.json";manifest=json.loads(manifest_path.read_text())
assert len(manifest["pages"])==10 and len(manifest["panels"])==90
for page in manifest["pages"]:assert sha(Path(page["file"]))==page["sha256"]
notes=[
    {"pages":[1],"indices":[0,8],"observation":"All9 gallery crops in shed0 reviewed. Dorsal patterned or brown bodies, strong rails and source timestamp fragments; no added scoring overlay on image pixels."},
    {"pages":[2],"indices":[9,17],"observation":"All9 shed2 gallery crops reviewed. Brown-white coats, bright regions, long crops and neck rails; visually similar overall coat layouts across distinct publisher IDs."},
    {"pages":[3],"indices":[18,26],"observation":"All9 shed3 gallery crops reviewed. Brown bodies, sparse white patches, rails, occasional black rotation corners and source text."},
    {"pages":[4],"indices":[27,35],"observation":"Remaining gallery3 and known-query6 reviewed; ID6 primary accepts match publisher labels, ID28 has high-score wrong predictions. Fur and illumination change strongly across filename dates."},
    {"pages":[5],"indices":[36,44],"observation":"Known9 reviewed. ID4 accepts, ID43 and37 mix high-score mistakes and refusals. Source dates in pixels40/41 disagree with filename dates; originals40/41 subsequently viewed at original resolution."},
    {"pages":[6],"indices":[45,53],"observation":"Known9 reviewed; ID42 and76 mixed correct/wrong/unresolved, ID77 all wrong primary accepts. Sparse white pattern, neighboring bodies and rail regions remain in crops."},
    {"pages":[7],"indices":[54,62],"observation":"Known6 plus unknown3 reviewed. UnknownID8 gives high-score false accepts in both models. Known91 and83 mix correct/wrong/unresolved decisions."},
    {"pages":[8],"indices":[63,71],"observation":"Unknown9 reviewed. Dark mostly unpatterned cows25/20 and brown-white40 receive many false accepts; correct unknown refusals also retained."},
    {"pages":[9],"indices":[72,80],"observation":"Unknown9 reviewed. IDs51/54/63 are brown or brown-white; most primary outputs falsely accepted, including low-score-but-above-threshold returns."},
    {"pages":[10],"indices":[81,89],"observation":"Unknown9 reviewed. Dark95 and patterned96/92 contain source rails and partial neighboring animals; both false accepts and retained refusals visible."}
]
protocol=json.loads((ROOT/"protocol/run_v1.json").read_text())
dates=[]
for index,visible in[(40,"2024-05-13"),(41,"2024-05-20")]:
    row=protocol["images"][index];file=ROOT/row["local_relative_file"]
    assert row["date"]!=visible
    dates.append({"source_index":index,"source_member":row["source_record"]["name"],"filename_date":row["date"],
                  "visible_camera_overlay_date_manually_read":visible,"original_file":str(file.resolve()),
                  "JPEG_sha256":sha(file),"which_clock_is_correct_independently_verified":False})
value={"status":"ALL90_INPUTS_AND_PRIMARY_OUTCOMES_ACTUALLY_VIEWED_ON10_PAGES_DATE_DISCREPANCIES_RECORDED_NO_EXCLUSIONS",
       "created_UTC":datetime.now(timezone.utc).isoformat(),"reviewer_kind":"assistant_visual_review_not_independent_true_ID_adjudication",
       "manifest_sha256":sha(manifest_path),"actually_viewed_pages":[r["file"]for r in manifest["pages"]],
       "actually_viewed_unique_indices":list(range(90)),"all20_selected_publisher_IDs_viewed":True,
       "page_notes":notes,"filename_camera_date_discrepancy_examples":dates,
       "camera_clock_or_filename_ground_truth_certified":False,"minimum30day_gap_scope":"filename-defined only",
       "source_or_labels_removed_after_predictions":False,"models_thresholds_or_crops_changed":False,
       "new_model_forwards":0,"whole_goal_complete":False}
out=ROOT/"results/visual_review.json";assert not out.exists()
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"viewed_images":90,"date_discrepancy_examples":len(dates),"new_model_forwards":0}))
