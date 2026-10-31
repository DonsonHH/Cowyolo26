"""Bound completed source evidence and check scope; no model or extra image decoding."""
from pathlib import Path,PurePosixPath
from collections import Counter
from datetime import datetime,timezone
from urllib.parse import unquote
import ast,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;O=ROOT/"results";E=ROOT/"evidence"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=O/"final_review_v1.json";assert not out.exists()
article=load(E/"BECA_article_32070171_version1_powershell.json")
assert article["version"]==1 and article["license"]["name"]=="CC BY 4.0"
assert len(article["files"])==1
f=article["files"][0];assert f["id"]==63928608 and f["size"]==20309712996 and f["computed_md5"]==f["supplied_md5"]=="8f4c06835a7d2dba1a6dbc74e34d38b3"
rows=load(O/"BECA_archive_index_v1.json")["entries"]
assert len(rows)==68350 and sum(not r["directory"]and r["name"].endswith(".jpg")for r in rows)==68334
assert not any(PurePosixPath(r["name"]).suffix.lower()in{".mp4",".avi",".mkv",".mov"}for r in rows)
audit=load(O/"BECA_metadata_audit_v1.json")
expect={"official_archive_rows_independently_matched_with_python_zipfile":68350,
        "reid_stored_images":24344,"canonical_combined_images":12172,"canonical_IDs":103,
        "native_to_combined_alias_matches_filename_CRC_size":12172,
        "canonical_distinct_dates":134,"IDs_span_at_least30days":99,"IDs_span_at_least60days":93,
        "IDs_with_at_least7_distinct_dates":103,"annotation_image_rows":8321,"annotation_object_rows":15788,
        "D_validation_images":806,"D_pairs":1424,"D_train_images":16083,
        "canonical_reid_crc_size_matches_obb":12172,"canonical_reid_crc_size_matches_bbox":0,
        "image_or_video_decodes":0,"new_model_forwards":0,"continuous_passage_GT_obtained":False}
for k,v in expect.items():assert audit[k]==v,(k,audit[k],v)
assert audit["canonical_date_range"]==["2023-12-10","2024-07-26"]
assert audit["native_group_images"]=={"cowshed0":6686,"cowshed2":2158,"cowshed3":3328}
assert audit["D_pair_labels"]=={"1":712,"0":712}
assert audit["annotation_keypoint_coordinate_list_lengths"]=={"26":15788}
assert audit["HHMM_all0000_fraction"]==sum(r["HHMM_filename"]=="0000"for r in load(O/"BECA_L_canonical_metadata_v1.json")["rows"])/12172
for prefix,expected_images,expected_IDs in[("BECA-D/train/",16083,5361),("BECA-D/val/",806,300)]:
    selected=[r for r in rows if r["name"].startswith(prefix)and not r["directory"]]
    assert len(selected)==expected_images and len({r["name"].split("/")[-1].split("_",1)[0]for r in selected})==expected_IDs
collisions=audit["identity_free_suffix_collisions"]
assert len(collisions)==len(audit["within_combined_CRC_size_duplicate_candidates"])==40
assert sum(len(r["combined_files"])for r in collisions)==80
conflict_IDs=sorted({name.split("/")[-1].split("_",1)[0]for r in collisions for name in r["combined_files"]},key=int)
assert conflict_IDs==["5","16","67","68","70","71","72","73","74","75","78","79","80","81","86"]
proof=load(O/"BECA_duplicate_byte_verification_v1.json")
assert proof["byte_proven_groups"]==2 and proof["CRC_only_remaining_groups"]==38
assert len(proof["members"])==4 and all(r["byte_identical"]for r in proof["pairs"])
assert {tuple(r["different_publisher_IDs"])for r in proof["pairs"]}=={("16","5"),("71","79")}
assert not proof["all40_groups_byte_verified"] and not proof["publisher_labels_changed"]
qa=load(O/"BECA_visual_QA_manifest_v1.json");visual=load(O/"BECA_visual_review_v1.json")
protocol=load(ROOT/"protocol/BECA_visual_QA_v1.json")
assert qa["unique_JPEG_inputs_decoded"]==8 and len(qa["records"])==8
assert len(qa["pages"])==2 and visual["viewed_QA_indices"]==list(range(8))
assert visual["manifest_SHA256"]==sha(O/"BECA_visual_QA_manifest_v1.json")
assert qa["protocol_sha256"]==sha(ROOT/"protocol/BECA_visual_QA_v1.json")
assert protocol["QA_only_IDs_never_future_final_test"]==["11","65","100"]
assert protocol["conflict_IDs_quarantined"]==conflict_IDs
assert all(r["ID"]not in conflict_IDs for r in protocol["new_acquisition_members"])
for rec in qa["records"]:
    assert sha(Path(rec["file"]))==rec["JPEG_sha256"]
    assert rec["QA_only_never_final_test"]
for rec in qa["pages"]:
    assert sha(Path(rec["file"]))==rec["sha256"]
assert not visual["whole_dataset_ID_labels_certified"]and not visual["source_true_permanent_IDs_known"]
assert not visual["continuous_passage_GT_obtained"] and visual["new_model_forwards"]==0

response_rows=[]
for p in sorted(E.glob("*.json")):
    try:data=load(p)
    except json.JSONDecodeError:
        assert p.name=="BECA_article_32070171_v1.json"
        assert p.read_bytes().startswith(b"<html>");continue
    nested=data.get("records",[])
    if isinstance(nested,list):
        for r in nested:
            if isinstance(r,dict)and "saved_bytes"in r and "HTTP_status"in r:
                assert sha(Path(r["saved_file"]))==r["sha256"]
                response_rows.append({"file":r["saved_file"],"bytes":r["saved_bytes"],"HTTP_status":r["HTTP_status"]})
    if "saved_bytes"in data and ("HTTP_status"in data or"native_client_exit_code"in data):
        path=Path(data.get("saved_file",data.get("raw_file","")))
        assert path.is_file()and path.stat().st_size==data["saved_bytes"]and sha(path)==data["sha256"]
        status=data.get("HTTP_status")or int(data["native_telemetry_no_URLs"].split("|")[0])
        response_rows.append({"file":str(path),"bytes":data["saved_bytes"],"HTTP_status":status})
        if data.get("strict_range_received"):
            assert status==206
            content=data.get("content_range","")
            match=re.fullmatch(r"bytes ([0-9]+)-([0-9]+)/20309712996",content);assert match
            start,end=map(int,match.groups());assert end-start+1==data["saved_bytes"]
assert len(response_rows)==31
assert Counter(r["HTTP_status"]for r in response_rows)=={206:28,403:2,200:1}
assert sum(r["bytes"]for r in response_rows)==14561616

documents=[ROOT/n for n in["计划与准入.md","原始来源检索.md","BECA身份数据准入与冲突核查.md","Review与当前状态.md"]]
main=documents[2].read_text(encoding="utf-8")
for value in["68,350","130,974","16,083","5,361","806","300","1,424","712","6,686／2,158／3,328",
              "12,172","103","8,321","15,788","24,344","134","99","93","46.71%","40组","80个文件","15个ID","38组",
              "已实际取得","没有下载整包","未修改","永久牛号","身份评分、训练更新和模型前向均为0"]:
    assert value in main,value
for rec in proof["pairs"]:assert rec["SHA256"]in main
local_links=0
for p in documents:
    for m in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",p.read_text(encoding="utf-8")):
        target=unquote((m[1]or m[2]).strip())
        if target.startswith(("http://","https://","#")):continue
        path=Path(target);path=path if path.is_absolute()else p.parent/path
        if path.resolve()==out.resolve():continue
        assert path.exists(),(p,target);local_links+=1
for path in (ROOT/"tools").glob("*.py"):ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
network=PROJECT/"identity_trigger_pair_20261030/evidence/router_static_probe_v1.json"
n=load(network);assert not n["network_configuration_changed"]and not n["credentials_sent"]and n["new_model_forwards"]==0
assert n["ARP"][0]["destination"]=="192.168.3.1"and n["ARP"][0]["return_code"]==0
assert n["ARP"][1]["return_code"]==67 and all(r["exit_code"]==1 for r in n["DNS"])
bindings={}
for base in["evidence","metadata","protocol","tools","QA_images","results"]:
    for p in sorted((ROOT/base).rglob("*")):
        if p.is_file()and p.resolve()!=out.resolve():bindings[str(p.relative_to(ROOT))]=sha(p)
result={
    "status":"NEW_BECA_OFFICIAL_METADATA_ARCHIVE_DIRECTORY_TEXTS_DUPLICATE_BYTES_AND_FROZEN8_VISUAL_QA_REVIEWED_NO_MODEL_EVALUATION",
    "created_UTC":datetime.now(timezone.utc).isoformat(),"assistant_self_review_not_independent_labeling":True,
    "official_archive_entries":68350,"JPEG_entries":68334,"canonical_L_files":12172,"canonical_L_IDs":103,
    "L_dates":134,"metadata_conflict_groups":40,"byte_verified_conflict_groups":2,"CRC_only_remaining_groups":38,
    "conflict_IDs":conflict_IDs,"actually_viewed_frozen_QA_images":8,"QA_only_IDs":["11","65","100"],
    "HTTP_response_records":len(response_rows),"HTTP_status_counts":dict(Counter(r["HTTP_status"]for r in response_rows)),
    "saved_response_bytes_including_failed_bodies":14561616,"strict_archive_range_responses":28,
    "source_archive_full_MD5_verified":False,"complete_archive_downloaded":False,
    "new_counting_GT_or_current12_identity_GT":False,"new_identity_scores":0,"new_training_updates":0,"new_model_forwards":0,
    "new_board_experiments":0,"board_results_recovered":False,"publisher_labels_changed":False,
    "Cows_reserved_date_pixels_opened":False,"BECA_entire_GT_certified":False,
    "forms_or_author_messages_sent":False,"network_configuration_changed":False,
    "local_links_checked":local_links,"documents":[{"path":str(p.resolve()),"sha256":sha(p)}for p in documents],
    "board_network_observation":{"path":str(network.resolve()),"sha256":sha(network)},
    "response_rows":response_rows,"evidence_hashes":bindings,"whole_goal_complete":False
}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:result[k]for k in["status","official_archive_entries","metadata_conflict_groups","byte_verified_conflict_groups","actually_viewed_frozen_QA_images","HTTP_response_records","saved_response_bytes_including_failed_bodies","local_links_checked","new_model_forwards","whole_goal_complete"]}))
