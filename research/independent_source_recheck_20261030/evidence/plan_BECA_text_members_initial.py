from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1];E=ROOT/"evidence";O=ROOT/"results"
rows=json.loads((O/"BECA_archive_index_v1.json").read_text())["entries"]
plans=[]
for member,alias in [("readme","readme"),("BECA-D/val_pair.txt","val_pair"),("BECA-L/obj_detection/annotations.json","annotations")]:
    row=next(r for r in rows if r["name"]==member)
    header_path=E/f"BECA_{alias}_header_v1.bin"
    body=header_path.read_bytes()
    h=struct.unpack("<4s5H3I2H",body)
    assert h[0]==b"PK\x03\x04" and h[2]==row["flags"] and h[3]==row["method"]
    assert h[6]==row["CRC32"] and h[7]==row["compressed_size"] and h[8]==row["uncompressed_size"]
    assert h[9]==row["filename_bytes"] and not row["encrypted"]
    plans.append({"member":member,"alias":alias,"header_sha256":hashlib.sha256(body).hexdigest(),
                  "range_start":row["local_header_offset"]+30,"range_length":h[9]+h[10]+row["compressed_size"],
                  "filename_bytes":h[9],"extra_bytes":h[10],"compressed_size":row["compressed_size"],
                  "uncompressed_size":row["uncompressed_size"],"CRC32":row["CRC32"],
                  "filename_sha256":row["filename_sha256"],"method":row["method"]})
value={"status":"THREE_PLAIN_TEXT_MEMBERS_RANGES_BOUND_TO_LOCAL_AND_CENTRAL_HEADERS","created_UTC":datetime.now(timezone.utc).isoformat(),
       "plans":plans,"image_or_video_decodes":0,"new_model_forwards":0,"whole_goal_complete":False}
out=O/"BECA_text_member_ranges_v1.json";assert not out.exists();out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(plans,ensure_ascii=False))
