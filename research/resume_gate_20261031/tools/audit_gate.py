"""Audit actual unresolved inputs and supported next work; never start a service/model."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/"evidence/gate_audit.json";assert not out.exists()
fixed=PROJECT/"beca_fixed_transfer_20261030/results/final_review.json"
diag=PROJECT/"beca_score_diagnosis_20261031/results/final_review.json"
paper=PROJECT/"paper_readiness_20261030/results/manuscript_review_v2.json"
overview=PROJECT/"research_synthesis_20261027/results/overview_review_20261031_v21_transfer.json"
v=load(overview);assert sha(Path(v["document"]["path"]))==v["document"]["sha256"]
assert not v["whole_goal_complete"]and not v["current_board_access_restored"]
for record in v["current_numeric_record_files"]:assert sha(Path(record["path"]))==record["sha256"]
for stage in[fixed,diag]:
    data=load(stage)
    for relative,digest in data["evidence_hashes"].items():assert sha(stage.parents[1]/relative)==digest
    for row in data["documents"]:assert sha(Path(row["path"]))==row["sha256"]
p=load(paper)
for row in p["documents"]+p["source_files"]+p["tools"]:assert sha(Path(row["file"]))==row["sha256"]
assert not p["ready_for_submission"]and not p["actual_trigger_originals_obtained"]
trigger=PROJECT/"identity_trigger_pair_20261030"
assert not(trigger/"delivery").exists()and not(trigger/"results/independent_verification.json").exists()
partial=load(trigger/"results/partial_observation_v1.json")
assert not partial["original_results_archive_obtained"]and not partial["fourth_case_terminal_observed"]
access_path=PROJECT/"beca_score_diagnosis_20261031/evidence/current_board_access_observation.json"
access=load(access_path);assert not access["COM6_enumerated"]and access["open_candidates"]==[]

def ps(command):
    result=subprocess.run(["pwsh","-NoProfile","-NonInteractive","-Command",command],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=15)
    assert result.returncode==0,(command,result.stderr[:250])
    value=json.loads(result.stdout)if result.stdout.strip()else[]
    return value if isinstance(value,list)else[value]
serial=ps("@(Get-CimInstance Win32_SerialPort | Select-Object DeviceID,Name) | ConvertTo-Json -Compress")
listeners=ps("@(Get-NetTCPConnection -LocalPort 8779 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess) | ConvertTo-Json -Compress")
queue_path=PROJECT/"beca_score_diagnosis_20261031/evidence/continuation_final_live_queue_20261031.txt"
queue=queue_path.read_text()
assert "renly\nmu01\n"in queue and "JOBID|"in queue
between=queue.split("JOBID|",1)[1].split("PartitionName=",1)[0].splitlines()[1:]
assert not any(re.match(r"\s*\d+\|",line)for line in between)
candidates=[]
for folder in[PROJECT/"evaluation_intake_20261028/results",PROJECT/"paired_event_intake_20261028/results"]:
    for path in folder.glob("*.json"):
        if any(t in path.name.lower()for t in["received_review","received_annotation","independent_reference_received","human_reference_received"]):
            candidates.append(str(path))
for pattern in["cow*annotation*.json","*cow*review*.json","*cow*events*.json","*奶牛*.json"]:
    candidates+=list(map(str,Path("C:/Users/Donson/Downloads").glob(pattern)))
assert not candidates
recurrence_paths=[
    PROJECT/"research_synthesis_20261027/results/overview_review_20261030_v19_paper.json",
    PROJECT/"research_synthesis_20261027/results/overview_review_20261030_v20_sources.json",
    overview]
recurrence=[]
for path in recurrence_paths:
    d=load(path)
    assert d["current_board_access_restored"]is False
    assert d["fourth_case_terminal_received"]is False
    assert d["actual_trigger_stage_raw_or_photo_vectors_received"]is False
    assert d["independent_event_JSON_received"]is False
    recurrence.append({"file":str(path.resolve()),"sha256":sha(path),"created_UTC":d["created_UTC"],
                       "same_blocking_inputs":["original board results inaccessible","independent source-event reference not received"],
                       "offline_work_that_progressed":d["status"]})
requirements=[
    {"requirement":"Local project and evidence-based research/paper route documented","state":"completed_current_stage","evidence":str(overview)},
    {"requirement":"Public-data detection/count and identity baselines with separate ranking/rejection metrics","state":"completed_components_with_remaining_system_quality_gaps","evidence":str(fixed)},
    {"requirement":"Independent event comparison and true bidirectional fixed-gate validation","state":"incomplete","needed":"reviewed event JSON and independent full direction-labelled sessions"},
    {"requirement":"PYNQ-Z2 detector and identity jointly, original actual-trigger stage verification","state":"incomplete","needed":"recover original SD result files and fourth-run terminal; current original process state unknown"},
    {"requirement":"Stable complete5FPS at tested input/workload conditions","state":"not_proven_existing_lateness_and_quality_limits","needed":"completed actual-trigger and live/long-running board evidence"},
    {"requirement":"Reliable recovery of original passage permanent cow identity","state":"unverified","needed":"trusted event/registry identity mapping and corresponding full-event evaluation"},
    {"requirement":"Scientific contribution and publication-ready paper","state":"draft_only_not_ready","evidence":str(paper),"needed":"specific new mechanism and matched validation with required independent truth"}
]
doc=ROOT/"继续研究需要的输入.md";text=doc.read_text(encoding="utf-8")
for m in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",text):
    target=unquote((m[1]or m[2]).strip())
    if target.startswith(("http://","https://")):continue
    path=Path(target);path=path if path.is_absolute()else doc.parent/path
    if path.resolve()==out.resolve():continue
    assert path.exists(),target
result={
    "status":"MAIN_COMPLETION_NOT_PROVEN_RECURRING_EXTERNAL_INPUT_GATES_AUDITED_AFTER_AVAILABLE_OFFLINE_WORK",
    "created_UTC":datetime.now(timezone.utc).isoformat(),
    "previous_goal_turn_classification":"progress",
    "current_turn_activity":"read-only requirement and current-access audit; no model experiment",
    "full_objective_complete":False,
    "current_serial_devices":serial,"COM6_enumerated":any(r["DeviceID"]=="COM6"for r in serial),
    "annotation8779_listeners":listeners,"annotation_server_start_auto_review_rejected":True,
    "annotation_browser_draft_contents_read_or_modified":False,
    "network_last_bounded_probe":{"file":str(access_path.resolve()),"sha256":sha(access_path)},
    "live_queue":{"file":str(queue_path.resolve()),"sha256":sha(queue_path),"renly_jobs_list_empty":True},
    "original_board_PID10099_current_state":"unobservable_after_access_loss_not_proven_terminal",
    "received_reference_candidates_in_declared_intake_and_narrow_download_names":candidates,
    "file_search_scope_not_entire_computer":True,
    "recurring_gate_evidence_across_three_preceding_goal_phases":recurrence,
    "requirements":requirements,
    "safe_available_offline_work_completed":["fixed external transfer","score-only rejection limits","source QA and timestamp concerns","v2 paper claims and synthesis"],
    "next_authorized_actions_require_external_state":["original board access to saved files","independent source-event reference","trusted event identity mapping"],
    "further_seen_score_search_would_not_complete_these_gates":True,
    "new_training_updates":0,"new_model_forwards":0,"new_board_experiments":0,
    "original_experiment_restarted":False,"network_configuration_changed":False,
    "handoff":{"file":str(doc.resolve()),"sha256":sha(doc)},
    "goal_status_not_yet_changed_by_this_script":True
}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":result["status"],"COM6_enumerated":result["COM6_enumerated"],"annotation8779_listeners":listeners,
                  "live_user_jobs":0,"incoming_reference_candidates":len(candidates),"recurring_gate_records":len(recurrence),
                  "full_objective_complete":False},ensure_ascii=False))
