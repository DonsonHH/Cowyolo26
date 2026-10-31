from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import ast,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;O=ROOT/"results"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=O/"final_review.json";assert not out.exists()
d=load(O/"score_diagnosis_v1.json");verified=load(O/"independent_verification_v1.json")
assert verified["threshold_states_verified"]==122 and verified["diagnosis_SHA256"]==sha(O/"score_diagnosis_v1.json")
assert verified["new_model_forwards"]==verified["new_pixels_read"]==0
for r in d["source_bindings"]:assert sha(Path(r["file"]))==r["sha256"]
expected={
    "old_C":{"zero_observed_W_and_FA":1,"unknown_FA_at_most1_of30_W_unconstrained":2,"combined_W_plus_FA_at_most1":1,"observed_accepted_error_fraction_at_most5percent":1},
    "new_C_domain_seed26":{"zero_observed_W_and_FA":3,"unknown_FA_at_most1_of30_W_unconstrained":3,"combined_W_plus_FA_at_most1":3,"observed_accepted_error_fraction_at_most5percent":3}}
assert verified["upper_bounds"]==expected
for model,values in expected.items():
    assert d["models"][model]["state_count"]==61
    assert {k:v["max_C"]for k,v in d["models"][model]["constrained_correct_acceptance_upper_bounds"].items()}==values
assert d["models"]["old_C"]["correct_rank1_queries_above_all_errors"]==[45]
assert d["models"]["new_C_domain_seed26"]["correct_rank1_queries_above_all_errors"]==[31,37,45]
assert not d["deployment_threshold_selected"]and not d["new_confirmatory_or_out_of_sample_result"]
assert d["new_model_forwards"]==d["new_pixels_read"]==d["new_training_updates"]==0
source=PROJECT/"beca_fixed_transfer_20261030"
original=load(source/"results/final_review.json")
for relative,digest in original["evidence_hashes"].items():assert sha(source/relative)==digest
for row in original["documents"]:assert sha(Path(row["path"]))==row["sha256"]
figure=load(O/"figure_manifest_v2_local.json")
assert figure["source_SHA256"]==sha(O/"score_diagnosis_v1.json")
for row in figure["files"]:assert sha(Path(row["file"]))==row["sha256"]
assert "130920|cow-beca-score-plot|COMPLETED|0:0|"in(ROOT/"evidence/plot_collection.txt").read_text()
assert "130921|cow-beca-score-plot|COMPLETED|0:0|"in(ROOT/"evidence/plot_collection_v2.txt").read_text()
for archive_name,report_name,dir_name,manifest_name in[
    ("score_plot_delivery_v1.tar.gz","plot_collection.txt","plot_delivery","plot_manifest.json"),
    ("score_plot_delivery_v2.tar.gz","plot_collection_v2.txt","plot_delivery_v2","plot_v2_manifest.json")]:
    record=json.loads((ROOT/"evidence"/report_name).read_text().strip().splitlines()[-1])
    archive=ROOT/archive_name;assert archive.stat().st_size==record["bytes"]and sha(archive)==record["sha256"]
    for row in load(ROOT/dir_name/manifest_name):
        p=ROOT/dir_name/row["file"];assert p.stat().st_size==row["bytes"]and sha(p)==row["sha256"]
access=load(ROOT/"evidence/current_board_access_observation.json")
assert not access["COM6_enumerated"]and access["open_candidates"]==[]and not access["network_configuration_changed"]
assert not access["credentials_sent"]and access["new_model_forwards"]==0
docs=[ROOT/n for n in["计划与范围.md","单阈值能解决多少问题.md","Review与当前状态.md"]]
text=docs[1].read_text(encoding="utf-8")
for value in["事后","不能作为独立校准成绩","原分数、候选与主阈值都未改变","1／30和3／30","122状态","0.93488246","0.90557145","26／30","不能据此判断SD","COM6"]:
    assert value in text,value
for model,prefix in[("old_C","原"),("new_C_domain_seed26","新")]:
    labels={"correct_rank1":"Top-1正确","wrong_rank1":"Top-1错误","unknown":"未知"}
    for category,row in d["models"][model]["score_distributions"].items():
        line=f'| {prefix}／{labels[category]} | {row["queries"]} | {row["minimum"]:.5f} | {row["median"]:.5f} | {row["maximum"]:.5f} |'
        assert line in text,line
links=0
for p in docs:
    for m in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",p.read_text(encoding="utf-8")):
        target=unquote((m[1]or m[2]).strip())
        if target.startswith(("http://","https://","#")):continue
        q=Path(target);q=q if q.is_absolute()else p.parent/q
        if q.resolve()==out.resolve():continue
        assert q.exists(),target;links+=1
for p in(ROOT/"tools").glob("*.py"):ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
bindings={}
for folder in["tools","evidence","results","plot_delivery","plot_delivery_v2"]:
    for p in sorted((ROOT/folder).rglob("*")):
        if p.is_file()and p.resolve()!=out.resolve():bindings[str(p.relative_to(ROOT))]=sha(p)
result={
    "status":"POSTHOC122_THRESHOLD_STATES8_BOUNDS_FINAL_FIGURE_ORIGINAL_SOURCES_AND_NO_DEPLOYMENT_THRESHOLD_SELF_REVIEWED",
    "created_UTC":datetime.now(timezone.utc).isoformat(),"threshold_states":122,"constraints":8,
    "zero_W_FA_max_C":[1,3],"correct_rank1_limits":[14,15],
    "new_model_forwards":0,"new_training_updates":0,"new_dataset_pixels_read":0,
    "new_calibration_or_confirmatory_evaluation":False,"deployment_threshold_selected":False,
    "default_model_or_threshold_changed":False,"posthoc_label_use_explicit":True,
    "final_plot_version":"figures_v2","figure_actually_viewed":True,"both_V1_and_V2_viewed":True,
    "plot_job_ids":["130920","130921"],"plot_jobs_completed_zero":True,
    "original_fixed_transfer180_forwards_results_unchanged":True,
    "new_board_results_recovered":False,"current_COM6_enumerated":False,"current_LAN22_9090_candidates":[],
    "new_event_or_current12_identity_GT":False,"whole_goal_complete":False,
    "documents":[{"path":str(p.resolve()),"sha256":sha(p)}for p in docs],
    "local_links_checked":links,"evidence_hashes":bindings,
    "reviewer_kind":"assistant_self_review_not_independent_human_GT"}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:result[k]for k in["status","threshold_states","zero_W_FA_max_C","local_links_checked","whole_goal_complete"]}))
