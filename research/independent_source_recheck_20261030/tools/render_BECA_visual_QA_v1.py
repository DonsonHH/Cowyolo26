from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
import hashlib,json,struct,zlib,io
ROOT=Path(__file__).resolve().parents[1];E=ROOT/"evidence";O=ROOT/"results"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda b:hashlib.sha256(b).hexdigest()
protocol=load(ROOT/"protocol/BECA_visual_QA_v1.json")
normal=load(O/"BECA_QA_payload_ranges_v1.json")["members"]
duplicates=load(O/"BECA_duplicate_payload_ranges_v1.json")["members"]
selected_duplicate_aliases={r["alias"]for r in protocol["already_acquired_duplicate_evidence_to_view"]}
specs=normal+[r for r in duplicates if r["alias"]in selected_duplicate_aliases]
assert len(specs)==protocol["JPEG_decodes_allowed"]==8
folder=ROOT/"QA_images";folder.mkdir(exist_ok=False)
figures=O/"visual_QA";figures.mkdir(exist_ok=False)
records=[];images=[]
for position,m in enumerate(specs):
    alias=m["alias"];row=m["archive_record"]
    response=E/f"BECA_{alias}_payload_v1.bin";packed=response.read_bytes()
    acquisition=load(E/f"BECA_{alias}_payload_v1.json")
    assert acquisition["strict_range_received"]and sha(packed)==acquisition["sha256"]
    assert len(packed)==m["payload_request_length"]
    name=packed[:row["filename_bytes"]];assert sha(name)==row["filename_sha256"]
    extra=packed[len(name):len(name)+m["extra_bytes"]];fields={};at=0
    while at<len(extra):
        kind,size=struct.unpack_from("<HH",extra,at);at+=4;assert at+size<=len(extra)
        fields[kind]=extra[at:at+size];at+=size
    assert at==len(extra)
    zpos=0
    for local,expected in[(m["local_uncompressed_field"],row["uncompressed_size"]),(m["local_compressed_field"],row["compressed_size"])]:
        if local==0xffffffff:assert struct.unpack_from("<Q",fields[1],zpos)[0]==expected;zpos+=8
    compressed=packed[len(name)+len(extra):]
    decoder=zlib.decompressobj(-15);raw=decoder.decompress(compressed,row["uncompressed_size"]+1)
    assert len(raw)==row["uncompressed_size"]and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
    assert zlib.crc32(raw)&0xffffffff==row["CRC32"]
    path=folder/(alias+".jpg");path.write_bytes(raw)
    with Image.open(io.BytesIO(raw))as opened:
        assert opened.format=="JPEG"
        image=opened.convert("RGB");image.load()
        exif_present=bool(opened.getexif())
    images.append(image)
    record={"QA_index":position,"alias":alias,"member":row["name"],"publisher_ID":Path(row["name"]).name.split("_",1)[0],
            "QA_only_never_final_test":True,"source_response_SHA256":sha(packed),"JPEG_sha256":sha(raw),
            "JPEG_bytes":len(raw),"CRC32":row["CRC32"],"RGB_pixel_SHA256":sha(image.tobytes()),
            "dimensions_WH":list(image.size),"EXIF_present":exif_present,
            "file":str(path.resolve()),"role":"normal_first_last_QA"if position<6 else"conflict_input_QA_not_ID_adjudication"}
    records.append(record)
font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",23)
small=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",18)
pages=[]
for page,start in enumerate([0,4],1):
    canvas=Image.new("RGB",(1200,1480),"#e9edf2");draw=ImageDraw.Draw(canvas)
    draw.text((22,15),f"BECA v1 | frozen source QA only | page {page}/2",font=font,fill="#17222d")
    for j,index in enumerate(range(start,start+4)):
        x=10+(j%2)*600;y=60+(j//2)*705
        draw.rectangle((x,y,x+580,y+690),fill="white")
        r=records[index]
        filename=Path(r["member"]).name
        draw.text((x+12,y+8),f'QA{index}  publisher ID {r["publisher_ID"]}  {r["role"][:21]}',font=small,fill="#17222d")
        draw.text((x+12,y+33),filename,font=small,fill="#17222d")
        draw.text((x+12,y+58),f'{r["dimensions_WH"][0]} x {r["dimensions_WH"][1]} px; no added image overlay',font=small,fill="#17222d")
        im=images[index].copy();im.thumbnail((552,585),Image.Resampling.LANCZOS)
        canvas.paste(im,(x+14+(552-im.width)//2,y+88+(585-im.height)//2))
    p=figures/f"page{page}.png";canvas.save(p)
    pages.append({"page":page,"file":str(p.resolve()),"sha256":sha(p.read_bytes()),"QA_indices":list(range(start,start+4))})
manifest=O/"BECA_visual_QA_manifest_v1.json";assert not manifest.exists()
value={"status":"EXACT_FROZEN8_JPEG_MEMBERS_CRC_BYTE_AND_RGB_HASHES_CAPTURED_TWO_QA_PAGES_RENDERED",
       "created_UTC":datetime.now(timezone.utc).isoformat(),"protocol_sha256":sha((ROOT/"protocol/BECA_visual_QA_v1.json").read_bytes()),
       "records":records,"pages":pages,"unique_JPEG_inputs_decoded":8,"new_model_forwards":0,"new_training_updates":0,
       "images_actually_visually_reviewed_yet":False,"independent_identity_accuracy_evaluated":False,"whole_goal_complete":False}
manifest.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"dimensions":[r["dimensions_WH"]for r in records],"pages":[r["file"]for r in pages]},ensure_ascii=False))
