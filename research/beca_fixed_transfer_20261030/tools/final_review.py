from pathlib import Path
from datetime import date,datetime,timezone
from urllib.parse import unquote
from collections import Counter
import ast,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;O=ROOT/"results"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=O/"final_review.json";assert not out.exists()
p=load(ROOT/"protocol/run_v1.json");e=load(ROOT/"protocol/execution_v1.json")
v=load(O/"independent_verification.json");a=load(O/"pixel_admission.json")
assert v["image_inputs"]==90 and v["model_image_forwards"]==180 and v["network_calls"]==16
assert v["gallery_pair_cells"]==3600 and v["ID_score_cells"]==1200 and v["fixed_decisions"]==480
assert v["paired_ID_contrasts"]==24 and not v["near1e7_threshold_endpoints"]
main=v["main_outcomes"]
assert [[r[k]for k in["known_Top1","known_Top5","C","W","U","unknown_FA"]]for r in main]==[[14,24,13,15,2,26],[15,26,13,11,6,26]]
assert [round(r["known_mAP"]*100,2)for r in main]==[51.46,48.50]
assert [round(r["accepted_wrong_fraction"]*100,2)for r in main]==[75.93,74.0]
assert len(v["primary_shed_subgroups"])==6
assert e["protocol_sha256"]==sha(ROOT/"protocol/run_v1.json")
for name,digest in e["files_sha256"].items():assert sha(ROOT/name)==digest
for row in p["source_bindings"]:assert sha(Path(row["file"]))==row["sha256"]
for row in p["models"]:assert sha(Path(row["local_checkpoint"]))==row["checkpoint_sha256"]
assert set(p["roles"]["registered"]).isdisjoint(p["roles"]["unknown"])
assert not set(p["roles"]["registered"]+p["roles"]["unknown"])&set(p["excluded_metadata_conflict_IDs"]+p["excluded_seen_QA_IDs"])
assert len(p["excluded_metadata_conflict_IDs"])==15 and len(p["excluded_seen_QA_IDs"])==3
assert len(a["rows"])==90 and sum(r["bytes"]for r in a["rows"])==13282368
response_count=0;response_bytes=0
for row in p["images"]:
    alias=f'BECA_img_{row["index"]:02d}'
    for kind in["header","payload"]:
        report=load(ROOT/"evidence"/f"{alias}_{kind}_v1.json")
        path=ROOT/"evidence"/f"{alias}_{kind}_v1.bin"
        assert report["HTTP_status"]==206 and report["strict_range_received"]
        assert path.stat().st_size==report["saved_bytes"]and sha(path)==report["sha256"]
        assert e["created_UTC"]<report["created_UTC"]<v["created_UTC"]
        response_count+=1;response_bytes+=report["saved_bytes"]
assert response_count==180 and response_bytes==13255992
archive=ROOT/"BECA_transfer_delivery_v1.tar.gz"
assert archive.stat().st_size==28326942 and sha(archive)=="be5ab3331d6ccf3f10a2cd0caa9608b8e6270059fe5820ebd3b2bfc457381292"
manifest=load(ROOT/"delivery/result_manifest.json");assert len(manifest)==495
for row in manifest:assert sha(ROOT/"delivery"/row["file"])==row["sha256"]and(ROOT/"delivery"/row["file"]).stat().st_size==row["bytes"]
assert (ROOT/"delivery/logs/evaluation-130909.err").stat().st_size==0
assert "130909|cow-beca-fixed20|COMPLETED|0:0|00:00:10|4|"in(ROOT/"evidence/status01.txt").read_text()
visual=load(O/"visual_review.json");panels=load(O/"visual_panels_manifest.json")
assert visual["actually_viewed_unique_indices"]==list(range(90))and len(visual["actually_viewed_pages"])==10
assert len(visual["filename_camera_date_discrepancy_examples"])==2
assert not visual["camera_clock_or_filename_ground_truth_certified"]and not visual["source_or_labels_removed_after_predictions"]
assert visual["minimum30day_gap_scope"]=="filename-defined only"
for row in panels["pages"]:assert sha(Path(row["file"]))==row["sha256"]
docs=[ROOT/n for n in["计划与验收.md","固定模型外来源结果与阈值失配.md","Review与当前状态.md"]]
report=docs[1].read_text(encoding="utf-8")
def row(*items):return"| "+" | ".join(map(str,items))+" |"
labels={"old_C":"原编码器","new_C_domain_seed26":"Cows域编码器"}
for r in main:
    assert row(labels[r["model"]],r["known_Top1"],r["known_Top5"],f'{r["known_mAP"]*100:.2f}%',r["C"],r["W"],r["U"],r["unknown_FA"])in report
all_outcomes=load(ROOT/"delivery/results/evaluation/all_outcomes.json")
for r in all_outcomes:
    assert row(labels[r["model"]],r["policy"],f'{r["threshold"]:.16f}',r["C"],r["W"],r["U"],r["unknown_FA"])in report
for r in v["primary_shed_subgroups"]:
    assert row(labels[r["model"]],r["native_group"],f'{r["Top1"]}/{r["known_queries"]}',r["C"],r["W"],r["U"],f'{r["FA"]}/{r["unknown_queries"]}')in report
for s in["13,282,368","52–167","86.67%","54次","41次","50次","37次","2000次","26031","−6.67至13.33","−11.58至6.96","−13.33至13.33",
          "相机叠字","助手目视读取","未修订日期","不能认定全部图片真实采集日期已核实","已隔离","本次20ID已评分","没有移动阈值"]:
    assert s in report,s
links=0
for doc in docs:
    for match in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",doc.read_text(encoding="utf-8")):
        target=unquote((match[1]or match[2]).strip())
        if target.startswith(("http://","https://","#")):continue
        path=Path(target);path=path if path.is_absolute()else doc.parent/path
        if path.resolve()==out.resolve():continue
        assert path.exists(),(doc,target);links+=1
for path in(ROOT/"tools").glob("*.py"):ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
bindings={}
for folder in["input","protocol","tools","evidence","results","delivery"]:
    for path in sorted((ROOT/folder).rglob("*")):
        if path.is_file()and"__pycache__"not in path.parts and path.resolve()!=out.resolve():
            bindings[str(path.relative_to(ROOT))]=sha(path)
result={"status":"FIXED_BECA20_TRANSFER180_CPU_FORWARDS_COMPLETE_ORIGINALS_ALL_WORKPOINTS_DATE_CONCERNS_AND_NONADOPTION_SELF_REVIEWED",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"local_date":"2026-10-31",
        "source_images":90,"publisher_registered_IDs":10,"publisher_unknown_IDs":10,"model_image_forwards":180,"network_calls":16,
        "Slurm_job_id":"130909","Slurm_state":"COMPLETED","Slurm_exit":"0:0","main_counts":[[14,13,15,2,26],[15,13,11,6,26]],
        "main_mAP":[r["known_mAP"]for r in main],"workpoints":8,"ID_score_cells":1200,"gallery_image_pair_cells":3600,
        "fixed_decisions":480,"stratified_ID_paired_contrasts":24,"actually_viewed_images":90,"actually_viewed_pages":10,
        "filename_camera_date_discrepancy_examples":2,"real_capture_dates_independently_verified":False,
        "selected_IDs_now_seen":True,"source_labels_independently_certified":False,"excluded_conflict_IDs":15,"excluded_seen_QA_IDs":3,
        "strict_range_responses":180,"range_response_bytes":13255992,"archive_bytes":28326942,
        "archive_sha256":sha(archive),"archive_members":496,"manifest_files":495,
        "new_training_updates":0,"new_NCNN_reference_forwards":0,"new_board_forwards":0,"warmups":0,
        "additional_model_forwards_by_review":0,"default_model_or_threshold_changed":False,"source_images_or_labels_changed":False,
        "new_current12_identity_or_counting_GT":False,"actual_trigger_board_results_recovered":False,
        "Cows_reserved_date_pixels_opened":False,"whole_goal_complete":False,"ready_for_automatic_identity_deployment":False,
        "reviewer_kind":"assistant_self_review_not_independent_human_true_ID_review",
        "documents":[{"path":str(path.resolve()),"sha256":sha(path)}for path in docs],
        "local_links_checked":links,"evidence_hashes":bindings}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:result[k]for k in["status","Slurm_job_id","model_image_forwards","actually_viewed_images","local_links_checked","whole_goal_complete"]}))
