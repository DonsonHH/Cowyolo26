from pathlib import Path
from datetime import date,datetime,timezone
from collections import defaultdict
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
SOURCE=PROJECT/"independent_source_recheck_20261030"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda text:hashlib.sha256(text.encode()).hexdigest()
protocol_dir=ROOT/"protocol";protocol_dir.mkdir(exist_ok=True)
out=protocol_dir/"run_v1.json";assert not out.exists()
audit_path=SOURCE/"results/BECA_metadata_audit_v1.json"
metadata_path=SOURCE/"results/BECA_L_canonical_metadata_v1.json"
audit=load(audit_path);metadata=load(metadata_path)["rows"]
conflicts={n.split("/")[-1].split("_",1)[0]for r in audit["identity_free_suffix_collisions"]for n in r["combined_files"]}
QA=set(load(SOURCE/"protocol/BECA_visual_QA_v1.json")["QA_only_IDs_never_future_final_test"])
eligible=defaultdict(list);perID={}
for record in audit["ID_date_records"]:
    ID=record["combined_ID"]
    if ID in conflicts|QA:continue
    rows=[r for r in metadata if r["publisher_ID"]==ID]
    dates=sorted({r["capture_date_filename"]for r in rows})
    if len(dates)<6:continue
    first3,last3=dates[:3],dates[-3:]
    gap=(date.fromisoformat(last3[0])-date.fromisoformat(first3[-1])).days
    if gap<30:continue
    selected={}
    for day in first3+last3:
        # Filename hashes cannot select on pixels or an encoded identity score.
        selected[day]=min([r for r in rows if r["capture_date_filename"]==day],
                          key=lambda r:digest("BECA-file-choice-20261030-v1:"+r["name"]))
    perID[ID]={"record":record,"gallery_dates":first3,"query_dates":last3,"gap_days":gap,"selected":selected}
    eligible[record["native_group"]].append(ID)
quotas={"cowshed0":(3,3),"cowshed2":(3,4),"cowshed3":(4,3)}
roles={"registered":[],"unknown":[]};assignments=[]
for shed,(known,unknown)in quotas.items():
    IDs=sorted(eligible[shed],key=lambda ID:digest("BECA-transfer20-20261030-v1:"+ID))
    assert len(IDs)>=known+unknown
    for role,values in[("registered",IDs[:known]),("unknown",IDs[known:known+unknown])]:
        roles[role].extend(values)
        for ID in values:assignments.append({"ID":ID,"role":role,"native_group":shed,"metadata_gap_days":perID[ID]["gap_days"]})
assert len(roles["registered"])==len(roles["unknown"])==10
assert not set(roles["registered"]+roles["unknown"])&(conflicts|QA)
images=[]
for purpose,IDs,datekey in[("gallery",roles["registered"],"gallery_dates"),
                           ("known_query",roles["registered"],"query_dates"),
                           ("unknown_query",roles["unknown"],"query_dates")]:
    for ID in IDs:
        info=perID[ID]
        for day in info[datekey]:
            source=info["selected"][day];idx=len(images)
            images.append({"index":idx,"publisher_identity":ID,"identity_namespace":"BECA32070171v1_BECA-L_cowshed_sum:"+ID,
                           "purpose":purpose,"is_known":purpose!="unknown_query","date":day,
                           "native_group":info["record"]["native_group"],"registered_to_query_minimum_gap_days":info["gap_days"],
                           "local_relative_file":f"input/images/{idx:02d}.jpg","source_record":source})
assert len(images)==90 and len({r["source_record"]["name"]for r in images})==90
assert len({(r["source_record"]["CRC32"],r["source_record"]["uncompressed_size"])for r in images})==90
expected_json=load(PROJECT/"identity_final20_20261030/protocol/execution_v1.json")
models=expected_json["models"]
for row in models:assert sha(Path(row["local_checkpoint"]))==row["checkpoint_sha256"]
sources=[audit_path,metadata_path,SOURCE/"results/final_review_v1.json",
         SOURCE/"results/BECA_visual_review_v1.json",SOURCE/"evidence/BECA_article_32070171_version1_powershell.json",
         PROJECT/"identity_final20_20261030/protocol/execution_v1.json"]
value={
    "status":"BECA20_ID_ROLES90_MEMBERS_MODELS_AND_ALL_FIXED_WORKPOINTS_FROZEN_BEFORE_REQUESTING_SELECTED_MEMBER_BYTES",
    "created_UTC":datetime.now(timezone.utc).isoformat(),"source_article":32070171,"source_version":1,"source_file_id":63928608,
    "archive_URL":"https://ndownloader.figshare.com/files/63928608","archive_declared_bytes":20309712996,
    "archive_MD5_publisher_value_not_full_file_verified":"8f4c06835a7d2dba1a6dbc74e34d38b3",
    "source_license":"CC BY 4.0","role_selection_prefix":"BECA-transfer20-20261030-v1:",
    "file_selection_prefix":"BECA-file-choice-20261030-v1:","role_quotas":quotas,
    "eligible_ID_counts_per_shed":{k:len(v)for k,v in eligible.items()},
    "roles":roles,"assignments":assignments,"excluded_metadata_conflict_IDs":sorted(conflicts,key=int),
    "excluded_seen_QA_IDs":sorted(QA,key=int),"image_count":90,"images":images,
    "gallery_IDs":10,"references_per_ID":3,"known_queries":30,"unknown_queries":30,"minimum_gallery_to_query_gap_days":30,
    "same_shed_contains_both_registered_and_unknown":True,"source_individuals_or_camera_masks_not_relabelled":True,
    "models":models,"threshold_policies":expected_json["threshold_policies"],"primary_policy":"primary_cal10_fold0",
    "score_method":"absolute_cosine_max_reference_per_ID","supplementary_MAP":"known_query average precision over30gallery image rows; stable ties by source index; unknownAP undefined",
    "frozen_body_tensor_SHA256":sha(PROJECT/"identity_final20_20261030/tools/frozen_body_tensor.py"),
    "source_bindings":[{"file":str(p.resolve()),"sha256":sha(p)}for p in sources],
    "batch":12,"Torch_version":"2.8.0+cu128","Pillow_version":"11.3.0","expected_model_image_forwards":180,"expected_network_calls":16,
    "bootstrap_seed":26031,"bootstrap_draws":2000,"bootstrap_unit":"publisher_ID stratified_by_source_shed",
    "tensor_anchor_indices":[0,3,29,30,59,60,87,89],"warmups":0,"new_training_updates":0,"new_board_forwards":0,
    "selected_image_member_bytes_requested_at_freeze":False,"entire_dataset_GT_independently_certified":False,
    "new_cow_identity_permanent_ear_tag_mapping":False,"new_continuous_counting_reference":False,
    "target_Holstein_real_passage_success_claim":False,"whole_goal_complete":False
}
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"roles":roles,"eligible":value["eligible_ID_counts_per_shed"],
                  "total_compressed_selected_JPEG_bytes":sum(r["source_record"]["compressed_size"]for r in images),
                  "protocol_sha256":sha(out)},ensure_ascii=False))
