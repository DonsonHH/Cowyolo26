from pathlib import Path
from datetime import datetime,timezone
import hashlib,io,json,struct,zlib,sys
import numpy as np
from PIL import Image
from frozen_body_tensor import body_tensor
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;E=ROOT/"evidence";O=ROOT/"results"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda b:hashlib.sha256(b).hexdigest()
p=load(ROOT/"protocol/run_v1.json");e=load(ROOT/"protocol/execution_v1.json")
assert sha((ROOT/"protocol/run_v1.json").read_bytes())==e["protocol_sha256"]
assert all(sha((ROOT/name).read_bytes())==digest for name,digest in e["files_sha256"].items())
acquire=load(E/"input_acquisition_complete_v1.json")
assert acquire["protocol_sha256"]==e["protocol_sha256"]and len(acquire["members"])==90
prior=load(PROJECT/"independent_source_recheck_20261030/results/BECA_visual_QA_manifest_v1.json")
old_JPEG={r["JPEG_sha256"]for r in prior["records"]};old_pixels={r["RGB_pixel_SHA256"]for r in prior["records"]}
folder=ROOT/"input/images";folder.mkdir(parents=True,exist_ok=False)
O.mkdir(exist_ok=True);out=O/"pixel_admission.json";assert not out.exists()
seen_JPEG=set();seen_pixels=set();records=[]
try:
    for member in p["images"]:
        index=member["index"];alias=f"BECA_img_{index:02d}";source=member["source_record"]
        header_path=E/(alias+"_header_v1.bin");payload_path=E/(alias+"_payload_v1.bin")
        h=struct.unpack("<4s5H3I2H",header_path.read_bytes())
        report=load(E/(alias+"_payload_v1.json"));packed=payload_path.read_bytes()
        assert report["strict_range_received"]and sha(packed)==report["sha256"]and len(packed)==report["saved_bytes"]
        assert h[0]==b"PK\x03\x04"and h[2]==source["flags"]and h[3]==source["method"]==8 and h[6]==source["CRC32"]
        filename=packed[:h[9]];assert sha(filename)==source["filename_sha256"]
        extra=packed[h[9]:h[9]+h[10]];at=0;fields={}
        while at<len(extra):
            kind,size=struct.unpack_from("<HH",extra,at);at+=4
            assert at+size<=len(extra);fields[kind]=extra[at:at+size];at+=size
        assert at==len(extra);zpos=0
        for local,expected in[(h[8],source["uncompressed_size"]),(h[7],source["compressed_size"])]:
            if local==0xffffffff:
                assert struct.unpack_from("<Q",fields[1],zpos)[0]==expected;zpos+=8
            else:assert local==expected
        compressed=packed[h[9]+h[10]:];assert len(compressed)==source["compressed_size"]
        dec=zlib.decompressobj(-15);raw=dec.decompress(compressed,source["uncompressed_size"]+1)
        assert len(raw)==source["uncompressed_size"]and dec.eof and not dec.unused_data and not dec.unconsumed_tail
        assert zlib.crc32(raw)&0xffffffff==source["CRC32"]
        digest=sha(raw);assert digest not in old_JPEG|seen_JPEG
        with Image.open(io.BytesIO(raw))as opened:
            assert opened.format=="JPEG";opened.load();image=opened.convert("RGB")
        pixel=sha(image.tobytes());assert pixel not in old_pixels|seen_pixels
        tensor=body_tensor(image)
        assert tensor.shape==(1,3,224,224)and tensor.dtype==np.float32 and np.isfinite(tensor).all()
        path=ROOT/member["local_relative_file"];assert not path.exists();path.write_bytes(raw)
        seen_JPEG.add(digest);seen_pixels.add(pixel)
        records.append({"index":index,"file":member["local_relative_file"],"publisher_identity":member["publisher_identity"],
                        "date":member["date"],"purpose":member["purpose"],"native_group":member["native_group"],
                        "bytes":len(raw),"sha256":digest,"RGB_pixel_SHA256":pixel,"dimensions_WH":list(image.size),
                        "input_tensor_sha256":sha(tensor.tobytes()),"source_member_name":source["name"],
                        "source_CRC32_verified":source["CRC32"],"payload_SHA256":sha(packed)})
    assert len(records)==90
    result={"status":"ALL90_FROZEN_BECA_MEMBERS_CRC_RGB_AND_NO_QA_OR_INTERNAL_DUPLICATE_PASS",
            "created_UTC":datetime.now(timezone.utc).isoformat(),"protocol_sha256":e["protocol_sha256"],
            "rows":records,"image_decodes":90,"selected_IDs_now_pixels_opened":True,
            "prior_QA_exact_JPEG_or_pixel_duplicates":0,"within90_exact_JPEG_or_pixel_duplicates":0,
            "label_true_identity_independently_certified":False,"new_model_forwards":0,
            "new_training_updates":0,"whole_goal_complete":False}
except BaseException as error:
    result={"status":"INPUT_ADMISSION_FAILED_NO_IMAGE_REPLACEMENT","created_UTC":datetime.now(timezone.utc).isoformat(),
            "rows":records,"error":repr(error),"image_decodes_completed":len(records),"new_model_forwards":0,"whole_goal_complete":False}
    raise
finally:
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items()if k!="rows"}),flush=True)
