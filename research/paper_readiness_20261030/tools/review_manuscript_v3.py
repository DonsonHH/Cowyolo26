from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=load(ROOT/"results/manuscript_review_v2.json")
for r in old["documents"]+old["source_files"]+old["tools"]:assert sha(Path(r["file"]))==r["sha256"]
ledger=load(ROOT/"results/claim_ledger_v3.json")
assert len(ledger["sources"])==15 and len(ledger["claims"])==15
assert [r["ID"]for r in ledger["claims"]if r["status"].startswith("pending")]==["C10","C11","C12"]
assert next(r for r in ledger["claims"]if r["ID"]=="C09")["status"]=="supported_actual_replay_system_unmet_target"
for r in ledger["sources"]:assert sha(Path(r["file"]))==r["sha256"]
stage=PROJECT/"identity_trigger_pair_20261030"
fixed=load(stage/"results/independent_verification.json")
full=load(stage/"results/final_review_recovered_v2.json")
assert full["actual_counts"]==[10,10,8,7]and full["Torch_reference_image_forwards"]==89
assert full["board_access_restored"]and not full["full5FPS_target_achieved"]
for relative,digest in full["evidence_hashes"].items():assert sha(stage/relative)==digest
for r in full["documents"]+full["access_evidence"]:assert sha(Path(r["path"]))==r["sha256"]
paper=ROOT/"论文方法与实验草稿_v3.md";text=paper.read_text(encoding="utf-8");lines=set(text.splitlines())
def row(*items):return"| "+" | ".join(map(str,items))+" |"
# V2's already-verified ten result rows are preserved verbatim.
old_text=(ROOT/"论文方法与实验草稿_v2.md").read_text(encoding="utf-8")
for line in old_text.splitlines():
    if line.startswith("| ")and("原编码器" in line or"新域编码器" in line or line.startswith("| r")):
        assert line in lines,line
for c in fixed["cases"]:
    assert row(c["run"],c["processed_frames"],c["skipped_slots"],c["deadline_misses"],
               f'{c["processed_per_second_over_offered_duration"]:.3f}',f'{c["P95_release_to_count_ms"]:.2f}',
               c["source_down_count"],c["actual_background_jobs"])in lines
for term in["v0.3","原始记录现已完整取回","完整结果现已核验","35项后台身份任务完成","计数为10、10、8、7",
             "没有重跑板端","时钟不包含曝光和相机传输","按作者ID评分，日期按文件名","116项固定决定","未达到完整5FPS","永久牛号",
             "89次CPU参考","恢复时boot已变化"]:
    assert term in text,term
assert "尚待从SD卡取回"not in text and "实际触发实验的待验收项目"not in text
assert text.count(r"\[")==text.count(r"\]")==3
docs=[ROOT/n for n in["论文主张与证据对应_v3.md","论文方法与实验草稿_v3.md","Review与当前状态_v3.md"]]
out=ROOT/"results/manuscript_review_v3.json";assert not out.exists()
links=0
for p in docs:
    for m in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",p.read_text(encoding="utf-8")):
        target=unquote((m[1]or m[2]).strip())
        if target.startswith(("http://","https://","#")):continue
        q=Path(target);q=q if q.is_absolute()else p.parent/q
        if q.resolve()==out.resolve():continue
        assert q.exists(),(p,target);links+=1
value={
    "status":"V3_MANUSCRIPT_ACTUAL_TRIGGER4RUNS_COMPLETE_RECOVERY_AND_UNMET_TIMING_CLAIM_REVIEWED",
    "created_UTC":datetime.now(timezone.utc).isoformat(),
    "reviewer_kind":"assistant_self_review_not_independent_human_or_peer_review",
    "full_v3_text_manually_read":True,"old_v2_and_its_bound_sources_preserved":True,
    "numeric_table_rows_verified":14,"claims":15,"bound_sources":15,"local_links_checked":links,
    "actual_trigger_originals_obtained":True,"actual_trigger_all_reference_verifications_complete":True,
    "actual_trigger_counts":[10,10,8,7],"actual_trigger_original_board_forwards":1519,
    "CPU_reference_forwards":89,"new_forwards_by_writing":0,"pending_claims":["C10","C11","C12"],
    "ready_for_submission":False,"whole_goal_complete":False,
    "source_files":ledger["sources"],"documents":[{"file":str(p.resolve()),"sha256":sha(p)}for p in docs],
    "v3_ledger":{"file":str((ROOT/"results/claim_ledger_v3.json").resolve()),"sha256":sha(ROOT/"results/claim_ledger_v3.json")},
    "previous_review":{"file":str((ROOT/"results/manuscript_review_v2.json").resolve()),"sha256":sha(ROOT/"results/manuscript_review_v2.json")},
    "tools":[{"file":str(p.resolve()),"sha256":sha(p)}for p in[ROOT/"tools/update_manuscript_v3_recovery.py",Path(__file__)]],
}
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:value[k]for k in["status","numeric_table_rows_verified","claims","local_links_checked","ready_for_submission"]}))
