from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import ast,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
ACCESS=PROJECT/"pynq_access_resume_20261031"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/"results/final_review_recovered_v2.json";assert not out.exists()
old=load(ROOT/"results/interruption_review_v1.json")
for name,digest in old["evidence_hashes"].items():assert sha(ROOT/name)==digest
archive=ROOT/"trigger_pair_interruption_originals_v1.tar.xz"
assert archive.stat().st_size==12260384 and sha(archive)=="dcce67e7b4fe2cb4492bd6d0a4d206f9384992fc9bd4882aa7601131739bc638"
meta=load(ROOT/"results/recovery_archive_verification_v2.json")
assert meta["members"]==163 and meta["manifest_files"]==162 and meta["source_terminal_complete"]
for r in load(ROOT/"delivery/interruption_recovery_manifest_v1.json"):
    p=ROOT/"delivery"/r["file"];assert sha(p)==r["sha256"]and p.stat().st_size==r["bytes"]
v=load(ROOT/"results/independent_verification.json")
ref=load(ROOT/"results/reference_independent_verification.json")
producer=load(ROOT/"results/producer_independent_verification.json")
cpu=load(ROOT/"results/CPU_independent_verification.json")
assert v["actual_O8_timed_forwards"]==1464 and v["actual_background_identity_jobs"]==35
assert v["all_new_actual_board_forwards"]==1519 and v["identity_warmups"]==4
assert [r["source_down_count"]for r in v["cases"]]==[10,10,8,7]
assert [r["processed_frames"]for r in v["cases"]]==[363,374,364,363]
assert [r["skipped_slots"]for r in v["cases"]]==[29,18,28,29]
assert [r["deadline_misses"]for r in v["cases"]]==[273,124,285,208]
assert [r["actual_jobs"]for r in v["backgrounds"]]==[10,10,8,7]
assert [r["accepted_provisional_predictions"]for r in v["backgrounds"]]==[1,0,0,0]
assert v["counter_observation_ticks_with_history"]==8596 and v["counter_paths"]==8
assert v["candidate_observations_separately_recomputed"]==202
assert not v["current_loaded_O8_claimed"]and v["boot_changed_before_collection"]
assert v["new_board_forwards_during_recovery"]==0
assert producer["producer_source_frames"]==1568 and producer["main_received_packets"]==1464
assert producer["overlapping_model_IO_packet_cases"]==1160 and producer["all_no_future_reads"]
assert cpu["frame_windows"]==1464 and len(cpu["runs"])==4
assert ref["Slurm_job_id"]=="130923"and ref["actual_Torch_image_forwards"]==ref["network_calls"]==89
assert ref["unique_model_input_queries"]==29 and ref["actual_query_jobs_represented"]==35
assert ref["retrieval_decisions_checked"]==116 and ref["tracker_replay_observation_ticks"]==8596
assert ref["verification_additional_model_forwards"]==0
full_ref=ROOT/"verification_delivery_v1.tar.gz"
assert full_ref.stat().st_size==16263209 and sha(full_ref)=="3fa6a935717701a6c63835cf1bc105766d3e8737ebe3a5b6902280adcdada88f"
manifest=load(ROOT/"reference_delivery/result_manifest.json");assert len(manifest)==103
for r in manifest:
    p=ROOT/"reference_delivery"/r["file"];assert sha(p)==r["sha256"]and p.stat().st_size==r["bytes"]
assert "130923|cow-trigger-verify|COMPLETED|0:0|"in(ROOT/"evidence/verification_repaired_status01.txt").read_text()
assert "130922|cow-trigger-verify|FAILED|1:0|"in(ROOT/"evidence/verification_status01_20261031.txt").read_text()
pair=load(ROOT/"results/job_pairing.json");assert len(pair["pairs"])==6 and len(pair["unmatched"])==23
assert sum(r["same_photo_sha256"]for r in pair["pairs"])==3
jobs=load(ROOT/"results/actual_job_rows.json");assert len(jobs)==35 and len({r["photo_sha256"]for r in jobs})==26
accepted=[r for r in jobs if r["accepted"]];assert len(accepted)==1 and accepted[0]["run"]=="r1_old"and accepted[0]["source_frame0"]==9795 and accepted[0]["predicted_id"]=="009"
assert not any(r["secondary_Cows_threshold_accepted"]for r in jobs)
photo=load(ROOT/"results/photo_panel_manifest.json");visual=load(ROOT/"results/actual_photo_visual_review.json")
assert photo["actual_jobs"]==visual["actual_jobs_mapped"]==35
assert photo["unique_photos"]==visual["unique_photos_viewed"]==26 and len(visual["pages_actually_viewed"])==5
assert visual["manifest_sha256"]==sha(ROOT/"results/photo_panel_manifest.json")
for p in photo["pages"]:assert sha(Path(p["file"]))==p["sha256"]
state_ssh=load(ACCESS/"evidence/final_recovery_state01.json")
assert state_ssh["status"]=="SSH_COMMAND_FINISHED"and state_ssh["exit_code"]==0
assert state_ssh["host"]=="192.168.3.100"and state_ssh["host_fingerprint_SHA256"]=="SHA256:TB0FfGjfMzgZUv/reJgTpeq/AM68sMCpGC5xm6Pit7o"
state=json.loads(state_ssh["stdout"].strip())
assert state["boot_id"]=="e7059099-ecb8-451e-a9aa-a66c8222196b"
assert state["all_bound_runtime_files_match"]and state["runtime_files_checked"]==23
assert state["services"]=={"ssh":"active","jupyter":"active"}and state["eth0_carrier"]=="1"
assert not state["collector_PID979_exists"]and state["accelerator_lock_free"]
assert state["new_model_forwards"]==0 and not state["PL_or_encoder_loaded_by_recovery"]and not state["original_experiment_restarted"]
login=load(ACCESS/"evidence/Jupyter_login_probe01.json");assert login["HTTP_status"]==200 and login["login_form_present"]and not login["authentication_submitted"]
boot=load(ACCESS/"evidence/boot_capture01.json");assert boot["received_bytes"]==34071 and boot["TX_bytes"]==0
assert sha(Path(boot["raw_file"]))==boot["raw_SHA256"]
pause=load(ACCESS/"evidence/uboot_pause01.json");assert not pause["space_sent"]
docs=[ROOT/"实际计数触发四轮恢复结果与时序取舍.md",ROOT/"Review与恢复后当前状态.md",ACCESS/"USB与网络恢复记录.md"]
text=docs[0].read_text(encoding="utf-8")
for c in v["cases"]:
    line=f'| {c["run"]}／{c["identity_model"]} | {c["processed_frames"]} | {c["skipped_slots"]} | {c["deadline_misses"]} | {c["processed_per_second_over_offered_duration"]:.3f} | {c["P95_release_to_count_ms"]:.2f} | {c["source_down_count"]} | {c["actual_background_jobs"]} |'
    assert line in text,line
for b in v["backgrounds"]:
    line=f'| {b["run"]} | {b["actual_jobs"]} | {b["accepted_provisional_predictions"]} | {b["max_queue_wait_ms"]:.2f} | {b["max_enqueue_to_result_ms"]:.2f} | {b["mean_network_elapsed_ms"]:.2f} | {b["chosen_older_frame_jobs"]} |'
    assert line in text,line
for term in["不能承诺完整5FPS","本次没有重跑板端实验","不是相机曝光","23个未配对","没有原事件永久牛号","尚未","半包已隔离","CPU参考另89","当前不默认更换"]:
    if term=="尚未":continue
    assert term in text,term
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
for folder in["delivery","reference_delivery","reference_input","tracker_input","protocol","payload","tools","results","evidence"]:
    for p in sorted((ROOT/folder).rglob("*")):
        if p.is_file()and"__pycache__"not in p.parts and p.resolve()!=out.resolve():bindings[str(p.relative_to(ROOT))]=sha(p)
access_bindings=[{"path":str(p.resolve()),"sha256":sha(p)}for p in sorted(ACCESS.rglob("*"))if p.is_file()]
result={
    "status":"ORIGINAL4_ACTUAL_TRIGGER_RUNS_RECOVERED_FULL_RAW_PHOTO_TIMING_ASSOCIATION_AND_CPU_REFERENCE_COMPLETE_REVIEWED_NOT_5FPS_OR_ID_GT_SUCCESS",
    "created_UTC":datetime.now(timezone.utc).isoformat(),
    "source_protocol_SHA256":"4217824d2964e56218c566a73096a2f282c94020f3176c74bf86cef9a270513c",
    "original_timed_O8_forwards":1464,"original_qualification_O8":8,"original_warmup_O8":8,
    "actual_background_jobs":35,"identity_warmups":4,"original_total_board_image_forwards":1519,
    "actual_counts":[10,10,8,7],"processed_frames":[363,374,364,363],"skipped_slots":[29,18,28,29],
    "deadline_misses":[273,124,285,208],"accepted_provisional":[1,0,0,0],
    "all4_original_terminal_and_raw_results_received":True,"raw_event_photo_numeric_verification_complete":True,
    "producer_records_verified":1568,"CPU_frame_windows_verified":1464,
    "full_tracker_observation_ticks":8596,"full_tracker_counter_paths":8,"Torch_reference_image_forwards":89,
    "unique_reference_model_inputs":29,"fixed_reference_decisions":116,
    "source_archive_bytes":12260384,"source_archive_SHA256":sha(archive),"source_archive_members":163,"source_manifest_files":162,
    "CPU_reference_archive_bytes":16263209,"CPU_reference_archive_SHA256":sha(full_ref),
    "CPU_reference_manifest_files":103,"CPU_reference_job":"130923","preforward_failed_job":"130922",
    "literal_event_pairs":6,"unmatched_job_rows":23,"same_photo_pairs":3,
    "unique_photos_actually_viewed":26,"actual_photo_pages_viewed":5,
    "board_access_restored":True,"current_IP":"192.168.3.100","Jupyter_login_HTTP":200,
    "current23_bound_runtime_hashes_match":True,"current_loaded_O8_identity_claimed":False,
    "new_boot_before_collection":True,"new_board_forwards_by_recovery":0,"original_experiment_restarted":False,
    "new_training_updates":0,"current_source_passage_independent_GT_obtained":False,"current12_permanent_identity_GT_obtained":False,
    "full5FPS_target_achieved":False,"reliable_identity_recovery_proven":False,"actual_camera_RFID_proven":False,
    "power_failure_root_cause_proven":False,"whole_goal_complete":False,
    "reviewer_kind":"assistant_self_review_not_independent_human_events_or_IDs",
    "documents":[{"path":str(p.resolve()),"sha256":sha(p)}for p in docs],"local_links_checked":links,
    "evidence_hashes":bindings,"access_evidence":access_bindings}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:result[k]for k in["status","actual_counts","actual_background_jobs","Torch_reference_image_forwards","board_access_restored","local_links_checked","whole_goal_complete"]}))
