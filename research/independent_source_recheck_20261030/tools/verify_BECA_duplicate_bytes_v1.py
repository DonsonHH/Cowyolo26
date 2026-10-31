from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import hashlib,json,struct,zlib
ROOT=Path(__file__).resolve().parents[1];E=ROOT/"evidence";O=ROOT/"results"
out=O/"BECA_duplicate_byte_verification_v1.json";assert not out.exists()
plan=O/"BECA_duplicate_payload_ranges_v1.json";spec=json.loads(plan.read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
records=[];grouped=defaultdict(list)
for m in spec["members"]:
    alias=m["alias"];row=m["archive_record"]
    source=E/f"BECA_{alias}_payload_v1.bin";packed=source.read_bytes()
    acquisition=json.loads((E/f"BECA_{alias}_payload_v1.json").read_text(encoding="utf-8-sig"))
    assert acquisition["strict_range_received"]and acquisition["sha256"]==sha(packed)and len(packed)==m["payload_request_length"]
    name=packed[:row["filename_bytes"]];assert sha(name)==row["filename_sha256"]
    extra=packed[len(name):len(name)+m["extra_bytes"]];at=0;fields={}
    while at<len(extra):
        kind,size=struct.unpack_from("<HH",extra,at);at+=4
        assert at+size<=len(extra);fields[kind]=extra[at:at+size];at+=size
    assert at==len(extra)
    zpos=0
    for local,expected in [(m["local_uncompressed_field"],row["uncompressed_size"]),(m["local_compressed_field"],row["compressed_size"])]:
        if local==0xffffffff:
            assert struct.unpack_from("<Q",fields[1],zpos)[0]==expected;zpos+=8
    compressed=packed[len(name)+len(extra):];assert len(compressed)==row["compressed_size"]
    decoder=zlib.decompressobj(-15);raw=decoder.decompress(compressed,row["uncompressed_size"]+1)
    assert decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
    assert len(raw)==row["uncompressed_size"]and zlib.crc32(raw)&0xffffffff==row["CRC32"]
    assert raw.startswith(b"\xff\xd8")and raw.endswith(b"\xff\xd9")
    # These bytes are forensic evidence only. No Image.open/CV decoder/model is called.
    rec={"member":row["name"],"alias":alias,"group_index":m["group_index"],"JPEG_bytes":len(raw),
         "JPEG_byte_SHA256":sha(raw),"compressed_member_SHA256":sha(compressed),"CRC32_verified":row["CRC32"],
         "ID_prefix":row["name"].split("/")[-1].split("_",1)[0],"source_response_sha256":sha(packed)}
    grouped[m["group_index"]].append((rec,raw))
    records.append(rec)
pairs=[]
for group,items in sorted(grouped.items()):
    a,b=items;assert a[0]["ID_prefix"]!=b[0]["ID_prefix"]
    assert a[1]==b[1]and a[0]["JPEG_byte_SHA256"]==b[0]["JPEG_byte_SHA256"]
    pairs.append({"group":group,"different_publisher_IDs":[a[0]["ID_prefix"],b[0]["ID_prefix"]],
                  "byte_identical":True,"SHA256":a[0]["JPEG_byte_SHA256"],"members":[a[0]["member"],b[0]["member"]]})
result={"status":"TWO_FROZEN_GROUPS_FOUR_ARCHIVE_MEMBERS_PROVE_IDENTICAL_JPEG_BYTES_WITH_DIFFERENT_ID_PREFIXES",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"members":records,"pairs":pairs,
        "metadata_candidate_groups_total":40,"byte_proven_groups":len(pairs),"CRC_only_remaining_groups":40-len(pairs),
        "image_or_video_decodes":0,"new_model_forwards":0,"new_training_updates":0,
        "publisher_labels_changed":False,"all40_groups_byte_verified":False,"whole_goal_complete":False}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":result["status"],"pairs":pairs,"remaining_CRC_only":result["CRC_only_remaining_groups"]},ensure_ascii=False))
