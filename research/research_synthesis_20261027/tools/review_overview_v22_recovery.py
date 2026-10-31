from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=load(ROOT/"results/overview_review_20261031_v21_transfer.json")
assert previous["complete_current_review_coverage"]
snapshot=ROOT/"snapshots/overview_v21_before_board_result_recovery/研究阶段总结_20261030.md"
assert sha(snapshot)==previous["document"]["sha256"]
entry_path=ROOT/"results/entrypoint_update_20261031_v22_recovery.json";entry=load(entry_path)
for row in entry["previous_files_and_snapshots"]:assert sha(Path(row["snapshot"]))==row["sha256"]
for row in entry["current_entrypoints"]:assert sha(Path(row["path"]))==row["sha256"]
assert sha(Path(entry["diff"]["path"]))==entry["diff"]["sha256"]
complete_path=PROJECT/"identity_trigger_pair_20261030/results/final_review_recovered_v2.json"
paper_path=PROJECT/"paper_readiness_20261030/results/manuscript_review_v3.json"
access_path=PROJECT/"pynq_access_resume_20261031/evidence/final_recovery_state01.json"
login_path=PROJECT/"pynq_access_resume_20261031/evidence/Jupyter_login_probe01.json"
complete=load(complete_path);paper=load(paper_path);access=json.loads(load(access_path)["stdout"])
assert complete["actual_counts"]==[10,10,8,7]and complete["Torch_reference_image_forwards"]==89
assert complete["all4_original_terminal_and_raw_results_received"]and complete["raw_event_photo_numeric_verification_complete"]
assert complete["board_access_restored"]and complete["new_board_forwards_by_recovery"]==0
assert not complete["full5FPS_target_achieved"]and not complete["current12_permanent_identity_GT_obtained"]
for relative,digest in complete["evidence_hashes"].items():assert sha(complete_path.parents[1]/relative)==digest
for row in complete["documents"]+complete["access_evidence"]:assert sha(Path(row["path"]))==row["sha256"]
assert paper["numeric_table_rows_verified"]==14 and paper["claims"]==15 and paper["pending_claims"]==["C10","C11","C12"]
for row in paper["documents"]+paper["source_files"]+paper["tools"]:assert sha(Path(row["file"]))==row["sha256"]
assert access["services"]=={"ssh":"active","jupyter":"active"}and access["all_bound_runtime_files_match"]
assert access["eth0_carrier"]=="1"and "192.168.3.100"in access["IPv4"]
assert load(login_path)["HTTP_status"]==200
records=list(previous["current_numeric_record_files"])
for path in[complete_path,paper_path,access_path,login_path]:records.append({"path":str(path),"sha256":sha(path)})
for row in records:assert sha(Path(row["path"]))==row["sha256"]
main=PROJECT/"研究阶段总结_20261030.md";text=main.read_text(encoding="utf-8")
assert "实际计数触发四轮已完整核验"in text and "### 3.14 "in text
assert "原包及CPU参考通过"in text and "192.168.3.100"in text
for expected in["| r1_old | 363 | 29 | 273 | 4.630 | 429.31 | 10 | 10／1 |",
                 "| r1_new | 374 | 18 | 124 | 4.770 | 334.10 | 10 | 10／0 |",
                 "| r2_new | 364 | 28 | 285 | 4.643 | 393.94 | 8 | 8／0 |",
                 "| r2_old | 363 | 29 | 208 | 4.630 | 445.17 | 7 | 7／0 |"]:
    assert expected in text
links=[]
for match in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",text):
    target=unquote((match[1]or match[2]).strip())
    if target.startswith(("http://","https://","#")):continue
    p=Path(target);p=p if p.is_absolute()else main.parent/p
    assert p.exists(),target;links.append(str(p))
value=dict(previous)
value.update({
    "status":"CURRENT_OVERVIEW_V22_RECOVERED_ORIGINAL4RUNS_RAW_FULL_REFERENCES_AND_CURRENT_ACCESS_SCOPE_REVIEWED",
    "created_UTC":datetime.now(timezone.utc).isoformat(),"document":{"path":str(main),"sha256":sha(main)},
    "review_method":"Retained V21 sections match snapshot; every V22 change, complete recovered report and v3 manuscript manually read; actual numeric, source hashes and reference replays checked.",
    "previous_complete_manual_read_provenance":"overview_review_20261031_v21_transfer.json",
    "previous_review_preserved":"overview_review_20261031_v21_transfer.json",
    "previous_overview_snapshot":{"path":str(snapshot),"sha256":sha(snapshot)},
    "entrypoint_update_evidence":{"path":str(entry_path),"sha256":sha(entry_path)},
    "changed_text_evidence":entry["diff"],"current_numeric_record_files":records,"local_overview_links_checked":len(links),
    "manual_review_topics":previous["manual_review_topics"]+[
        "USB FTDI enumeration and passive repeated boot before restored pinnedSSH192.168.3.100",
        "Power fault not proven; autoboot pause never sent; no image/boot/network rewrite",
        "New collection boot distinguished from original experimental boot and source PL_after record",
        "Original terminal1464timed output and all4 counts10,10,8,7 recovered; stale RUNNING progress not terminal",
        "All35 actual jobs26photos and dynamic workload not fixed40task control",
        "Original1519board forwards, zero recovery board forwards,89new CPU reference separately accounted",
        "130922 pre-forward missing artifact failure and early partial download preserved before repaired full verification",
        "8596 association ticks and116 reference decisions pass; no independent passageID correctness inferred",
        "V3 C09 supported actual-replay evidence; C10,C11,C12 remain pending and no5FPS completion"
    ],
    "actual_trigger_stage_finalized":True,"original_trigger_timed_O8_forwards":1464,"original_trigger_total_board_forwards":1519,
    "fourth_case_terminal_received":True,"actual_trigger_stage_raw_or_photo_vectors_received":True,
    "actual_trigger_stage_full_independent_verification_completed":True,"recovery_code_executed_on_board":True,
    "new_model_forwards_by_recovery_on_board":0,"new_CPU_reference_forwards_after_recovery":89,
    "original_experiment_current_process_state":"saved_complete_terminal_in_original_boot; no matching task during collection in_new_boot",
    "original_experiment_restarted":False,"current_board_access_restored":True,"current_IP":"192.168.3.100",
    "current_board_carrier_live_rechecked":True,"current_COM6_enumerated":None,"COM6_available_during_boot_capture":True,
    "current_board_loaded_O8_verified_now":False,"source_results_lost_claimed":False,"network_configuration_changed":False,
    "paper_draft_version":3,"paper_ready_for_submission":False,"power_failure_root_cause_proven":False,
    "full_periodic_5FPS_target_fixed":False,"main_paper_contribution_verified":False,"whole_goal_complete":False,
})
out=ROOT/"results/overview_review_20261031_v22_recovery.json";assert not out.exists()
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"main_links":len(links),"bound_records":len(records),"board_access_restored":True,"whole_goal_complete":False}))
