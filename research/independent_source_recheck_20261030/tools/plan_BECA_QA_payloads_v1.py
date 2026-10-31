from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1];E=ROOT/"evidence";O=ROOT/"results"
p=ROOT/"protocol/BECA_visual_QA_v1.json"
protocol=json.loads(p.read_text());plans=[]
for m in protocol["new_acquisition_members"]:
    alias=m["alias"];row=m["archive_record"]
    header=E/f"BECA_{alias}_header_v1.bin";h=struct.unpack("<4s5H3I2H",header.read_bytes())
    assert h[0]==b"PK\x03\x04"and h[2]==row["flags"]and h[3]==row["method"]==8
    assert h[6]==row["CRC32"]and h[7]in{row["compressed_size"],0xffffffff}and h[8]in{row["uncompressed_size"],0xffffffff}
    assert h[9]==row["filename_bytes"]
    plans.append({**m,"payload_request_start":row["local_header_offset"]+30,"payload_request_length":h[9]+h[10]+row["compressed_size"],
                  "header_sha256":hashlib.sha256(header.read_bytes()).hexdigest(),"extra_bytes":h[10],
                  "local_compressed_field":h[7],"local_uncompressed_field":h[8]})
out=O/"BECA_QA_payload_ranges_v1.json";assert not out.exists()
out.write_text(json.dumps({"status":"SIX_QA_RANGES_BOUND_TO_FROZEN_PROTOCOL_AND_HEADERS","created_UTC":datetime.now(timezone.utc).isoformat(),
                           "frozen_protocol_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"members":plans,
                           "image_or_video_decodes":0,"new_model_forwards":0},ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps([{"alias":m["alias"],"start":m["payload_request_start"],"length":m["payload_request_length"]}for m in plans]))
