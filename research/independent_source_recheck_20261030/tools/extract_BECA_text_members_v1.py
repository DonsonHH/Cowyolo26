from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,struct,zlib
ROOT=Path(__file__).resolve().parents[1];E=ROOT/"evidence";O=ROOT/"results"
sha=lambda b:hashlib.sha256(b).hexdigest()
plans=json.loads((O/"BECA_text_member_ranges_v1.json").read_text())["plans"]
out=O/"BECA_text_extraction_v1.json";assert not out.exists()
dest=ROOT/"metadata";dest.mkdir(exist_ok=True)
records=[]
for p in plans:
    alias=p["alias"];response=E/f"BECA_{alias}_payload_v1.bin"
    acquisition=json.loads((E/f"BECA_{alias}_payload_v1.json").read_text(encoding="utf-8-sig"))
    packed=response.read_bytes()
    assert acquisition["strict_range_received"]and sha(packed)==acquisition["sha256"]and len(packed)==p["range_length"]
    name=packed[:p["filename_bytes"]];assert sha(name)==p["filename_sha256"]
    extra=packed[p["filename_bytes"]:p["filename_bytes"]+p["extra_bytes"]]
    at=0;fields={}
    while at<len(extra):
        kind,size=struct.unpack_from("<HH",extra,at);at+=4
        assert at+size<=len(extra);fields[kind]=extra[at:at+size];at+=size
    assert at==len(extra)
    zip64=fields.get(1,b"");zpos=0
    for local,expected in [(p["local_uncompressed_field"],p["uncompressed_size"]),(p["local_compressed_field"],p["compressed_size"])]:
        if local==0xffffffff:
            assert struct.unpack_from("<Q",zip64,zpos)[0]==expected;zpos+=8
    compressed=packed[len(name)+len(extra):];assert len(compressed)==p["compressed_size"]and p["method"]==8
    decoder=zlib.decompressobj(-15)
    raw=decoder.decompress(compressed,p["uncompressed_size"]+1)
    assert len(raw)==p["uncompressed_size"]and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
    assert zlib.crc32(raw)&0xffffffff==p["CRC32"]
    suffix=".json"if alias=="annotations"else".txt"
    path=dest/(alias+suffix);assert not path.exists();path.write_bytes(raw)
    if suffix==".json":
        value=json.loads(raw)
        details={"JSON_keys":list(value),"array_lengths":{k:len(v)for k,v in value.items()if isinstance(v,list)}}
    else:
        try:text=raw.decode("utf-8-sig");encoding="utf-8-sig"
        except UnicodeDecodeError:text=raw.decode("gb18030");encoding="gb18030"
        details={"text_encoding":encoding,"text_lines":len(text.splitlines())}
    records.append({"archive_member":p["member"],"file":str(path.resolve()),"bytes":len(raw),"sha256":sha(raw),
                    "CRC32_verified":p["CRC32"],"local_and_central_header_consistent":True,**details})
result={"status":"THREE_TEXT_MEMBERS_NAME_LOCAL_ZIP64_CRC_AND_LENGTH_VERIFIED",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"records":records,"image_or_video_decodes":0,
        "new_model_forwards":0,"whole_goal_complete":False}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
print((dest/"readme.txt").read_text(encoding=records[0]["text_encoding"]))
