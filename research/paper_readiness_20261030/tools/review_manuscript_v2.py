from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=load(ROOT/"results/manuscript_review_v1.json")
for r in old["documents"]+old["method_sources_bound"]+old["result_sources_bound_and_hash_verified"]+old["tools"]:
    assert sha(Path(r["file"]))==r["sha256"]
ledger=load(ROOT/"results/claim_ledger_v2.json")
assert len(ledger["claims"])==15 and len(ledger["sources"])==11
assert [r["ID"]for r in ledger["claims"][-3:]]==["C13","C14","C15"]
assert not ledger["whole_goal_complete"]and not ledger["ready_for_submission"]
for r in ledger["sources"]:assert sha(Path(r["file"]))==r["sha256"]
source={r["name"]:load(Path(r["file"]))for r in ledger["sources"]}
BECA=source["BECA_fixed_transfer"]
assert [[r[k]for k in["known_Top1","C","W","U","unknown_FA"]]for r in BECA["main_outcomes"]]==[[14,13,15,2,26],[15,13,11,6,26]]
diagnosis=PROJECT/"beca_score_diagnosis_20261031/results/final_review.json";d=load(diagnosis)
assert d["threshold_states"]==122 and d["zero_W_FA_max_C"]==[1,3]
assert not d["deployment_threshold_selected"] and d["posthoc_label_use_explicit"]
for name,digest in d["evidence_hashes"].items():assert sha(diagnosis.parents[1]/name)==digest
path=ROOT/"论文方法与实验草稿_v2.md";text=path.read_text(encoding="utf-8");lines=set(text.splitlines())
def row(*items):return"| "+" | ".join(map(str,items))+" |"
for label,actual in zip(["原编码器","新域编码器，种子26"],source["identity_CPU"]["outcomes"][::4]):
    assert row(label,*(actual[k]for k in["known_Top1","known_Top5","C","W","U","unknown_FA"]))in lines
for label,model in[("原编码器","old_C"),("新域编码器","new_C_domain_seed26")]:
    actual=source["identity_ARM"]["timings"][model]
    assert row(label,90,f'{actual["network_mean_ms"]:.2f}',f'{actual["network_P95_ms"]:.2f}')in lines
for actual in source["fixed_workload"]["cases"]:
    assert row(actual["run"],"原"if actual["identity_model"]=="old"else"新",actual["processed_frames"],actual["skipped_slots"],
               actual["deadline_misses"],f'{actual["processed_per_second_over_offered_duration"]:.3f}',
               f'{actual["P95_release_to_count_ms"]:.2f}',actual["source_down_count"],f'{actual["maximum_identity_result_ms"]:.2f}')in lines
for label,r in zip(["原编码器","新域编码器，种子26"],BECA["main_outcomes"]):
    assert row(label,r["known_Top1"],f'{r["known_mAP"]*100:.2f}%',r["C"],r["W"],r["U"],r["unknown_FA"])in lines
for term in["按BECA作者文件名日期划分","没有BECA训练或新阈值校准","至少两图的文件名日期与相机叠字日期不一致",
             "发布方ID也未得到本项目的独立人工认证","事后诊断","不是独立校准或新的部署门限","1/30和3/30",
             "不据此换主工作点","本次稿件整理没有新增训练或模型前向","BECA评价的180次CPU图前向","尚未达到投稿状态"]:
    assert term in text,term
assert len(source["BECA_visual_dates"]["filename_camera_date_discrepancy_examples"])==2
assert text.count(r"\[")==text.count(r"\]")==3
assert len([c for c in ledger["claims"]if c["status"].startswith("pending")])==4
documents=[ROOT/n for n in["论文主张与证据对应_v2.md","论文方法与实验草稿_v2.md","Review与当前状态_v2.md"]]
links=0;external=set()
out=ROOT/"results/manuscript_review_v2.json";assert not out.exists()
for doc in documents:
    for m in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",doc.read_text(encoding="utf-8")):
        target=unquote((m[1]or m[2]).strip())
        if target.startswith(("http://","https://")):external.add(target);continue
        if target.startswith("#"):continue
        p=Path(target);p=p if p.is_absolute()else doc.parent/p
        if p.resolve()==out.resolve():continue
        assert p.exists(),(doc,target);links+=1
result={
    "status":"MANUSCRIPT_V2_EXTERNAL_FIXED_RESULTS_DATE_CONCERNS_AND_POSTHOC_BOUND_SEPARATELY_REVIEWED_V1_PRESERVED",
    "created_UTC":datetime.now(timezone.utc).isoformat(),
    "reviewer_kind":"assistant_self_review_not_independent_human_or_peer_review",
    "complete_v2_text_read_in_full":True,"v1_bound_sources_documents_and_tools_unchanged":True,
    "numeric_table_rows_verified":10,"claims":15,"bound_result_sources":11,"local_links_checked":links,
    "external_link_count":len(external),"external_network_accessibility_verified_by_this_script":False,
    "source_files":ledger["sources"],
    "documents":[{"file":str(p.resolve()),"sha256":sha(p)}for p in documents],
    "v2_ledger":{"file":str((ROOT/"results/claim_ledger_v2.json").resolve()),"sha256":sha(ROOT/"results/claim_ledger_v2.json")},
    "prior_review":{"file":str((ROOT/"results/manuscript_review_v1.json").resolve()),"sha256":sha(ROOT/"results/manuscript_review_v1.json")},
    "score_diagnosis_review":{"file":str(diagnosis.resolve()),"sha256":sha(diagnosis)},
    "tools":[{"file":str(p.resolve()),"sha256":sha(p)}for p in[ROOT/"tools/update_manuscript_v2.py",Path(__file__)]],
    "new_model_forwards_by_writing":0,"new_training_updates_by_writing":0,"BECA_original_evaluation_CPU_forwards":180,
    "actual_trigger_originals_obtained":False,"ready_for_submission":False,"whole_goal_complete":False}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:result[k]for k in["status","numeric_table_rows_verified","claims","local_links_checked","ready_for_submission"]}))
