"""Parse central-directory metadata only; no archive member is decompressed."""
from pathlib import Path, PurePosixPath
from collections import Counter
from datetime import datetime, timezone
import hashlib, json, struct, zlib

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/"evidence";O=ROOT/"results"
index_path=O/"BECA_archive_index_v1.json"
summary_path=O/"BECA_archive_index_summary_v1.json"
assert not index_path.exists() and not summary_path.exists()
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda b:hashlib.sha256(b).hexdigest()
plan=load(O/"BECA_directory_range_plan_v1.json")
record=load(E/"BECA_central_directory_v1.json")
assert record["strict_range_received"]
data=(E/"BECA_central_directory_v1.bin").read_bytes()
assert len(data)==plan["central_directory_bytes"]==record["saved_bytes"]
assert sha(data)==record["sha256"]
tail=(E/"BECA_zip_tail_dotnet_v1.bin").read_bytes()
tail_start=plan["archive_declared_bytes"]-len(tail)
overlap_start=max(tail_start,plan["central_directory_start"])
overlap_end=plan["central_directory_start"]+len(data)
assert data[overlap_start-plan["central_directory_start"]:]==tail[overlap_start-tail_start:overlap_end-tail_start]
position=0;rows=[]
while position<len(data):
    assert data[position:position+4]==b"PK\x01\x02",(position,data[position:position+4])
    values=struct.unpack_from("<4s6H3I5H2I",data,position)
    flags,method,mtime,mdate,crc,csize,usize=values[3:10]
    nlen,xlen,clen,disk,iattr,eattr,offset=values[10:17]
    end=position+46+nlen+xlen+clen
    assert end<=len(data)
    raw_name=data[position+46:position+46+nlen]
    extra=data[position+46+nlen:position+46+nlen+xlen]
    parts={};at=0
    while at<len(extra):
        kind,size=struct.unpack_from("<HH",extra,at);at+=4
        assert at+size<=len(extra);parts[kind]=extra[at:at+size];at+=size
    assert at==len(extra)
    zip64=parts.get(1,b"");zpos=0
    resolved=[]
    for value in [usize,csize,offset]:
        if value==0xffffffff:
            assert zpos+8<=len(zip64)
            value=struct.unpack_from("<Q",zip64,zpos)[0];zpos+=8
        resolved.append(value)
    usize,csize,offset=resolved
    if disk==0xffff:
        assert zpos+4<=len(zip64);disk=struct.unpack_from("<I",zip64,zpos)[0]
    assert disk==0 and offset+30+csize<=plan["central_directory_start"]
    encoding="utf-8"if flags&0x800 else"cp437"
    name=raw_name.decode(encoding)
    if 0x7075 in parts:
        unicode_path=parts[0x7075]
        if len(unicode_path)>=5 and unicode_path[0]==1 and struct.unpack_from("<I",unicode_path,1)[0]==zlib.crc32(raw_name)&0xffffffff:
            name=unicode_path[5:].decode("utf-8");encoding="zip_unicode_path_extra"
    canonical=name.replace("\\","/")
    p=PurePosixPath(canonical)
    assert not p.is_absolute() and ".."not in p.parts and "\0"not in name and ":"not in p.parts[0]
    rows.append({"index":len(rows),"name":canonical,"original_decoded_name":name,
                 "name_encoding":encoding,"filename_bytes":nlen,"filename_sha256":sha(raw_name),
                 "directory":canonical.endswith("/"),"method":method,"flags":flags,"encrypted":bool(flags&1),
                 "CRC32":crc,"compressed_size":csize,"uncompressed_size":usize,"local_header_offset":offset,
                 "zip_container_DOS_time":[1980+(mdate>>9),(mdate>>5)&15,mdate&31,mtime>>11,(mtime>>5)&63,(mtime&31)*2]})
    position=end
assert position==len(data) and len(rows)==plan["entry_count_declared"]
counts=Counter(r["name"].split("/")[0]for r in rows)
prefix2=Counter("/".join(r["name"].split("/")[:2])for r in rows)
prefix3=Counter("/".join(r["name"].split("/")[:3])for r in rows)
extensions=Counter(PurePosixPath(r["name"]).suffix.lower()or"<none>"for r in rows if not r["directory"])
texts=[r for r in rows if not r["directory"]and PurePosixPath(r["name"]).suffix.lower()in{".txt",".csv",".json",".md",".xml",".yaml",".yml",".xlsx",".xls",".pdf"}]
names=[r["name"]for r in rows]
summary={"status":"ALL_ZIP64_DIRECTORY_ROWS_PARSED_NO_MEMBER_ACCESS",
         "created_UTC":datetime.now(timezone.utc).isoformat(),"entry_count":len(rows),
         "directory_entries":sum(r["directory"]for r in rows),"duplicate_exact_names":len(rows)-len(set(names)),
         "encrypted_entries":sum(r["encrypted"]for r in rows),"top_level":dict(counts),
         "prefix2":dict(prefix2),"prefix3":dict(prefix3),"extensions":dict(extensions),
         "methods":dict(Counter(r["method"]for r in rows)),"text_or_annotation_members":texts,
         "CD_tail_overlap_bytes_verified":overlap_end-overlap_start,
         "central_directory_sha256":sha(data),"source_tail_sha256":sha(tail),
         "complete_archive_downloaded":False,"image_or_video_decodes":0,"new_model_forwards":0,
         "archive_container_times_not_capture_dates":True,
         "whole_goal_complete":False}
index_path.write_text(json.dumps({"archive_id":32070171,"file_id":63928608,"version":1,"entries":rows},ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
summary["index_sha256"]=sha(index_path.read_bytes())
summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:summary[k]for k in ["status","entry_count","directory_entries","duplicate_exact_names","encrypted_entries","top_level","prefix2","extensions","methods","CD_tail_overlap_bytes_verified"]},ensure_ascii=False))
print(json.dumps({"text_member_count":len(texts),"text_samples":[{"name":r["name"],"size":r["uncompressed_size"]}for r in texts[:12]],"name_samples":[r["name"]for r in rows[:12]]},ensure_ascii=False))
