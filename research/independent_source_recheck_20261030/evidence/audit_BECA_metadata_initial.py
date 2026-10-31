"""Audit temporal IDs, aliases and source annotation contracts before any image decode."""
from pathlib import Path, PurePosixPath
from datetime import date,datetime,timezone
from collections import Counter,defaultdict
import hashlib,io,json,math,re,zipfile

ROOT=Path(__file__).resolve().parents[1];E=ROOT/"evidence";O=ROOT/"results"
out=O/"BECA_metadata_audit_v1.json";assert not out.exists()
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
index=load(O/"BECA_archive_index_v1.json")["entries"]
plan=load(O/"BECA_directory_range_plan_v1.json")
tail=(E/"BECA_zip_tail_dotnet_v1.bin").read_bytes()
central=(E/"BECA_central_directory_v1.bin").read_bytes()

class MetadataOnlyFile(io.RawIOBase):
    def __init__(self):
        self.position=0
        self.segments=[(plan["central_directory_start"],central),(plan["archive_declared_bytes"]-len(tail),tail)]
        self.reads=[]
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        at=offset if whence==0 else self.position+offset if whence==1 else plan["archive_declared_bytes"]+offset
        assert at>=0;self.position=at;return at
    def read(self,size=-1):
        if size<0:size=plan["archive_declared_bytes"]-self.position
        size=min(size,plan["archive_declared_bytes"]-self.position)
        if size==0:return b""
        for start,data in self.segments:
            if start<=self.position and self.position+size<=start+len(data):
                body=data[self.position-start:self.position-start+size]
                self.reads.append([self.position,len(body)]);self.position+=len(body);return body
        raise AssertionError(("Attempted member/non-metadata read",self.position,size))

virtual=MetadataOnlyFile()
with zipfile.ZipFile(virtual)as archive:
    infos=archive.infolist()
assert len(infos)==len(index)==68350
for actual,expected in zip(infos,index):
    assert actual.filename.replace("\\","/")==expected["name"]
    assert (actual.CRC,actual.file_size,actual.compress_size,actual.header_offset,actual.compress_type,actual.flag_bits)==(
        expected["CRC32"],expected["uncompressed_size"],expected["compressed_size"],expected["local_header_offset"],expected["method"],expected["flags"])

pattern=re.compile(r"(?P<ID>\d+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<hhmm>\d{4})_(?P<camera>\d+)_(?P<shed>\d+)_(?P<instance>\d+)_(?P<position>\d+\.\d+)\.jpg")
reid=[]
for row in index:
    if row["directory"]or not row["name"].startswith("BECA-L/reid/"):continue
    parts=PurePosixPath(row["name"]).parts
    assert len(parts)==4
    match=pattern.fullmatch(parts[-1]);assert match,row["name"]
    data=match.groupdict()
    day=date.fromisoformat(data["date"]);position=float(data["position"]);assert 0<=position<=1
    hour,minute=int(data["hhmm"][:2]),int(data["hhmm"][2:]);assert 0<=hour<24 and 0<=minute<60
    key=parts[-1].split("_",1)[1]
    reid.append({**row,"group":parts[2],"publisher_ID":data["ID"],"normalized_numeric_ID":int(data["ID"]),
                 "capture_date_filename":day.isoformat(),"HHMM_filename":data["hhmm"],
                 "camera_token":data["camera"],"shed_token":data["shed"],
                 "instance_token":data["instance"],"relative_camera_position_token":position,"identity_free_suffix":key})
groups=defaultdict(list)
for row in reid:groups[row["group"]].append(row)
assert {k:len(v)for k,v in groups.items()}=={"cowshed0":6686,"cowshed2":2158,"cowshed3":3328,"cowshed_sum":12172}
native=[r for r in reid if r["group"]!="cowshed_sum"];combined=groups["cowshed_sum"]
by_native={r["identity_free_suffix"]:r for r in native};by_combined={r["identity_free_suffix"]:r for r in combined}
assert len(by_native)==len(native)==len(by_combined)==len(combined)==12172
assert set(by_native)==set(by_combined)
mapping=defaultdict(set);reverse=defaultdict(set);conflicts=[]
for suffix,a in by_native.items():
    b=by_combined[suffix]
    assert (a["CRC32"],a["uncompressed_size"],a["compressed_size"])==(b["CRC32"],b["uncompressed_size"],b["compressed_size"])
    mapping[(a["group"],a["publisher_ID"])].add(b["publisher_ID"])
    reverse[b["publisher_ID"]].add((a["group"],a["publisher_ID"]))
assert all(len(v)==1 for v in mapping.values())and all(len(v)==1 for v in reverse.values())
assert len(mapping)==len(reverse)==103
id_records=[]
for cow in sorted(reverse,key=int):
    entries=[r for r in combined if r["publisher_ID"]==cow]
    days=sorted({r["capture_date_filename"]for r in entries})
    counts=Counter(r["capture_date_filename"]for r in entries)
    native_group,native_ID=next(iter(reverse[cow]))
    id_records.append({"combined_ID":cow,"native_group":native_group,"native_ID":native_ID,"images":len(entries),
                       "distinct_dates":len(days),"earliest_date":days[0],"latest_date":days[-1],
                       "span_days":(date.fromisoformat(days[-1])-date.fromisoformat(days[0])).days,
                       "date_counts":dict(sorted(counts.items())),"camera_tokens":sorted({r["camera_token"]for r in entries}),
                       "HHMM_tokens":sorted({r["HHMM_filename"]for r in entries})})
dups=defaultdict(list)
for row in combined:dups[(row["CRC32"],row["uncompressed_size"])].append(row["name"])
duplicates=[value for value in dups.values()if len(value)>1]
obj_groups=defaultdict(list)
for row in index:
    if not row["directory"]and row["name"].startswith("BECA-L/obj_detection/")and row["name"].endswith(".jpg"):
        obj_groups[PurePosixPath(row["name"]).parts[2]].append(row)
annotations=load(ROOT/"metadata/annotations.json")
images={row["id"]:row for row in annotations["images"]}
assert len(images)==len(annotations["images"])==8321
assert len({r["id"]for r in annotations["annotations"]})==len(annotations["annotations"])==15788
raw_names={PurePosixPath(r["name"]).name for r in obj_groups["roi_image"]}
assert {r["file_name"]for r in images.values()}==raw_names
box_issues=[];keypoint_lengths=Counter();subnames=[]
for ann in annotations["annotations"]:
    assert ann["image_id"]in images
    image=images[ann["image_id"]];x1,y1,x2,y2=ann["bbox"]
    assert all(math.isfinite(v)for v in ann["bbox"])
    issues=[]
    if x2<=x1 or y2<=y1:issues.append("nonpositive_xyxy")
    if x1<0 or y1<0 or x2>image["width"]or y2>image["height"]:issues.append("outside_image")
    if issues:box_issues.append({"annotation_id":ann["id"],"image_id":ann["image_id"],"issues":issues,"bbox":ann["bbox"]})
    keypoint_lengths[len(ann["keypoints"])]+=1
    assert len(ann["xywh_angle"])==5 and ann["sub_image_name"].endswith(".jpg")
    subnames.append(ann["sub_image_name"])
obb={PurePosixPath(r["name"]).name:r for r in obj_groups["obb_bbox"]}
bbox={PurePosixPath(r["name"]).name:r for r in obj_groups["bbox"]}
sum_to_obb=sum_to_bbox=0;missing_obb=[]
for row in combined:
    suffix=row["identity_free_suffix"]
    if suffix not in obb:missing_obb.append(row["name"]);continue
    source=obb[suffix]
    sum_to_obb+=int((row["CRC32"],row["uncompressed_size"])==(source["CRC32"],source["uncompressed_size"]))
    if suffix in bbox:
        b=bbox[suffix];sum_to_bbox+=int((row["CRC32"],row["uncompressed_size"])==(b["CRC32"],b["uncompressed_size"]))
pair_rows=[]
val={PurePosixPath(r["name"]).name for r in index if r["name"].startswith("BECA-D/val/")and not r["directory"]}
for line in (ROOT/"metadata/val_pair.txt").read_text().splitlines():
    first,second,label=line.split();assert first in val and second in val and label in{"0","1"}
    same=first.split("_")[0]==second.split("_")[0]
    assert same==(label=="1")
    pair_rows.append((first,second,label))
summary={
    "status":"METADATA_ID_DATE_ALIAS_AND_ANNOTATION_CONTRACT_AUDITED_BEFORE_IMAGE_PIXELS",
    "created_UTC":datetime.now(timezone.utc).isoformat(),
    "official_archive_rows_independently_matched_with_python_zipfile":len(index),
    "zipfile_only_metadata_read_requests":virtual.reads,
    "reid_stored_images":len(reid),"canonical_combined_images":len(combined),"canonical_IDs":103,
    "native_group_images":{k:len(v)for k,v in groups.items()if k!="cowshed_sum"},
    "native_to_combined_alias_matches_filename_CRC_size":12172,
    "aliases_are_metadata_matches_not_full_pixel_hash_proof":True,
    "one_to_one_ID_namespace_map":[{"native_group":k[0],"native_ID":k[1],"combined_ID":next(iter(v))}for k,v in sorted(mapping.items())],
    "ID_date_records":id_records,
    "canonical_date_range":[min(r["capture_date_filename"]for r in combined),max(r["capture_date_filename"]for r in combined)],
    "canonical_distinct_dates":len({r["capture_date_filename"]for r in combined}),
    "IDs_span_at_least30days":sum(r["span_days"]>=30 for r in id_records),
    "IDs_span_at_least60days":sum(r["span_days"]>=60 for r in id_records),
    "IDs_with_at_least7_distinct_dates":sum(r["distinct_dates"]>=7 for r in id_records),
    "HHMM_all0000_fraction":sum(r["HHMM_filename"]=="0000"for r in combined)/len(combined),
    "filename_time_not_assumed_wall_clock":True,
    "within_combined_CRC_size_duplicate_candidates":duplicates,
    "object_detection_image_folders":{k:len(v)for k,v in obj_groups.items()},
    "annotation_image_rows":len(images),"annotation_object_rows":len(subnames),
    "annotation_sub_image_names_unique":len(set(subnames)),
    "annotation_bbox_contract":"xyxy per publisher readme; do not use COCO xywh conversion",
    "annotation_keypoint_coordinate_list_lengths":dict(keypoint_lengths),
    "annotation_box_issues":box_issues,"annotation_missing_category_schema":not any("category_id"in r for r in annotations["annotations"]),
    "canonical_reid_crc_size_matches_obb":sum_to_obb,"canonical_reid_crc_size_matches_bbox":sum_to_bbox,
    "canonical_reid_missing_obb_filename":missing_obb,
    "D_validation_images":len(val),"D_pairs":len(pair_rows),"D_pair_labels":dict(Counter(row[2]for row in pair_rows)),
    "D_train_images":sum(r["name"].startswith("BECA-D/train/")and not r["directory"]for r in index),
    "annotation_readme_source_SHA":[{"file":str(p.resolve()),"sha256":sha(p)}for p in[ROOT/"metadata/readme.txt",ROOT/"metadata/annotations.json",ROOT/"metadata/val_pair.txt"]],
    "image_or_video_decodes":0,"new_model_forwards":0,"new_training_updates":0,
    "continuous_passage_GT_obtained":False,"current12_permanent_ID_mapping_obtained":False,
    "cross_date_evaluation_protocol_frozen":False,"whole_goal_complete":False
}
out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
canonical=O/"BECA_L_canonical_metadata_v1.json";assert not canonical.exists()
canonical.write_text(json.dumps({"rows":combined,"ID_namespace":"BECA32070171v1_BECA-L_cowshed_sum","metadata_only":True},ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:summary[k]for k in ["status","canonical_combined_images","canonical_IDs","canonical_date_range","canonical_distinct_dates","IDs_span_at_least30days","IDs_span_at_least60days","IDs_with_at_least7_distinct_dates","HHMM_all0000_fraction","object_detection_image_folders","annotation_image_rows","annotation_object_rows","canonical_reid_crc_size_matches_obb","canonical_reid_crc_size_matches_bbox","D_pairs","D_pair_labels"]},ensure_ascii=False))
print(json.dumps({"box_issue_count":len(box_issues),"duplicate_candidate_groups":len(duplicates),"missing_obb":len(missing_obb)}))
