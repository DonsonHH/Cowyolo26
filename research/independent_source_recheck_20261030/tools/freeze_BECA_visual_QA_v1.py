from pathlib import Path
from datetime import date,datetime,timezone
from collections import defaultdict
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];O=ROOT/"results";P=ROOT/"protocol"
sha=lambda b:hashlib.sha256(b).hexdigest()
audit_path=O/"BECA_metadata_audit_v1.json";audit=json.loads(audit_path.read_text())
metadata_path=O/"BECA_L_canonical_metadata_v1.json";rows=json.loads(metadata_path.read_text())["rows"]
conflicts={name.split("/")[-1].split("_",1)[0]for group in audit["identity_free_suffix_collisions"]for name in group["combined_files"]}
eligible=defaultdict(list)
for record in audit["ID_date_records"]:
    if record["combined_ID"]not in conflicts and record["span_days"]>=30:
        eligible[record["native_group"]].append(record)
members=[];qa_IDs=[]
for shed in sorted(eligible):
    chosen=min(eligible[shed],key=lambda r:sha(("BECA-source-QA-20261030:"+r["combined_ID"]).encode()))
    identity=chosen["combined_ID"];qa_IDs.append(identity)
    images=sorted([r for r in rows if r["publisher_ID"]==identity],key=lambda r:(r["capture_date_filename"],r["name"]))
    for role,row in[("earliest",images[0]),("latest",images[-1])]:
        members.append({"alias":f"qa_{shed}_{role}","ID":identity,"role":role,"group":shed,
                        "header_request_start":row["local_header_offset"],"header_request_length":30,"archive_record":row})
proof=json.loads((O/"BECA_duplicate_byte_verification_v1.json").read_text())
duplicate_members=[]
for pair in proof["pairs"]:
    name=pair["members"][0];row=next(r for r in rows if r["name"]==name)
    original=next(r for r in proof["members"]if r["member"]==name)
    duplicate_members.append({"member":name,"alias":original["alias"],"ID_labels":pair["different_publisher_IDs"],
                              "JPEG_byte_SHA256":pair["SHA256"],"pixel_use":"QA_only_not_true_ID_adjudication"})
assert len(members)==6 and len(qa_IDs)==3 and len(duplicate_members)==2
value={"status":"SIX_EARLIEST_LATEST_IMAGES_THREE_QA_ONLY_IDS_AND_TWO_PREEXISTING_DUPLICATE_INPUTS_FROZEN_BEFORE_PIXEL_DECODE",
       "created_UTC":datetime.now(timezone.utc).isoformat(),"purpose":"Check overhead crop, body visibility, overlays, uniform-coat vs Holstein applicability and sample failure modes; not score identities.",
       "metadata_source_sha256":sha(metadata_path.read_bytes()),"audit_source_sha256":sha(audit_path.read_bytes()),
       "selection":"One minimum-SHA ID per native cowshed among IDs spanning>=30days and absent from all metadata conflict groups; first and last file by date/name.",
       "QA_only_IDs_never_future_final_test":qa_IDs,"conflict_IDs_quarantined":sorted(conflicts,key=int),
       "new_acquisition_members":members,"already_acquired_duplicate_evidence_to_view":duplicate_members,
       "JPEG_decodes_allowed":8,"model_forwards_allowed":0,"training_updates_allowed":0,
       "no_training_or_final_test_split_of_BECA_L_claimed":True,"main_Holstein_evaluation_admitted":False,
       "new_independent_identity_GT_verified":False,"whole_goal_complete":False}
out=P/"BECA_visual_QA_v1.json";assert not out.exists();out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"QA_IDs":qa_IDs,"new_members":[{"alias":m["alias"],"name":m["archive_record"]["name"],"start":m["header_request_start"]}for m in members],
                  "additional_existing_images_to_decode":len(duplicate_members)},ensure_ascii=False))
