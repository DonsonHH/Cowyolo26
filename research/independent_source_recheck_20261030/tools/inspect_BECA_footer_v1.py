from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,struct

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"evidence"
out=ROOT/"results/BECA_directory_range_plan_v1.json"
out.parent.mkdir(exist_ok=True);assert not out.exists()
source=OUT/"BECA_zip_tail_dotnet_v1.bin"
record=json.loads((OUT/"BECA_zip_tail_dotnet_v1.json").read_text(encoding="utf-8-sig"))
data=source.read_bytes();total=record["archive_declared_bytes"];base=total-len(data)
assert record["strict_range_received"] and len(data)==131072
assert hashlib.sha256(data).hexdigest()==record["sha256"]
end=data.rfind(b"PK\x05\x06");assert end>=0
e=struct.unpack_from("<4s4H2IH",data,end)
assert e[1]==e[2]==0 and end+22+e[7]==len(data)
locator=struct.unpack_from("<4sIQI",data,end-20)
assert locator[0]==b"PK\x06\x07" and locator[1]==0 and locator[3]==1
zpos=locator[2]-base
assert 0<=zpos<=len(data)-56
z=struct.unpack_from("<4sQHHIIQQQQ",data,zpos)
assert z[0]==b"PK\x06\x06" and z[4]==z[5]==0 and z[6]==z[7]
entries,size,offset=z[7],z[8],z[9]
assert 0<entries<=500000 and 0<size<=16*1024*1024
assert offset+size==locator[2] and locator[2]+12+z[1]==base+end-20
result={"status":"ZIP64_FOOTER_VALIDATED_DIRECTORY_REQUEST_FIXED_BEFORE_MEMBER_READ",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"archive_declared_bytes":total,
        "entry_count_declared":entries,"central_directory_start":offset,
        "central_directory_bytes":size,"central_directory_end_inclusive":offset+size-1,
        "archive_comment_bytes":e[7],"source_tail_sha256":record["sha256"],
        "request_maximum_bytes":16*1024*1024,"image_or_video_decodes":0,
        "new_model_forwards":0,"whole_goal_complete":False}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
