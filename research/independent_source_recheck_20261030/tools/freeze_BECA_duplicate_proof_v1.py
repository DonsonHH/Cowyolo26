"""Freeze four exact members from two metadata collision groups, before byte access."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];O=ROOT/"results";P=ROOT/"protocol";P.mkdir(exist_ok=True)
load=lambda p:json.loads(p.read_text())
audit=load(O/"BECA_metadata_audit_v1.json")
index={r["name"]:r for r in load(O/"BECA_archive_index_v1.json")["entries"]}
collisions=audit["identity_free_suffix_collisions"]
groups={}
for collision in collisions:
    assert collision["same_CRC_size_compressed_size"]
    shed=collision["native_files"][0].split("/")[2]
    groups.setdefault(shed,[]).append(collision)
selected=[]
for shed in sorted(groups):
    collision=sorted(groups[shed],key=lambda c:c["suffix"])[0]
    selected.append(collision)
assert len(selected)==2 and all(len(c["combined_files"])==2 for c in selected)
members=[]
for group,collision in enumerate(selected):
    for i,name in enumerate(sorted(collision["combined_files"])):
        row=index[name]
        members.append({"group_index":group,"alias":f"dup_g{group}_m{i}","header_request_start":row["local_header_offset"],
                        "header_request_length":30,"archive_record":row})
out=P/"BECA_duplicate_byte_proof_v1.json";assert not out.exists()
value={"status":"TWO_PRESELECTED_METADATA_COLLISION_GROUPS_FOUR_MEMBERS_BEFORE_ANY_IMAGE_MEMBER_BYTES",
       "created_UTC":datetime.now(timezone.utc).isoformat(),"selection":"First lexical identity-free suffix per affected native shed; no model score or pixel selection.",
       "source_audit_sha256":hashlib.sha256((O/"BECA_metadata_audit_v1.json").read_bytes()).hexdigest(),
       "members":members,"permit":"Read exact compressed members, check local/central header CRC and JPEG byte SHA only; do not decode image pixels or run models.",
       "purpose":"Distinguish CRC-size collision candidate from actual byte-identical data assigned to different publisher IDs.",
       "additional_compressed_payload_upper_bound":sum(m["archive_record"]["compressed_size"]for m in members),
       "image_or_video_decodes":0,"new_model_forwards":0,"whole_goal_complete":False}
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"selected_sheds":sorted(groups),"members":[{"alias":r["alias"],"name":r["archive_record"]["name"],"start":r["header_request_start"],"compressed":r["archive_record"]["compressed_size"]}for r in members]},ensure_ascii=False))
