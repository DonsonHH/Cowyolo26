from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=load(ROOT/"results/overview_review_20261030_v20_sources.json")
assert previous["complete_current_review_coverage"]
snapshot=ROOT/"snapshots/overview_v20_before_external_transfer/研究阶段总结_20261030.md"
assert sha(snapshot)==previous["document"]["sha256"]
entry_path=ROOT/"results/entrypoint_update_20261031_v21_transfer.json";entry=load(entry_path)
for r in entry["previous_files_and_snapshots"]:assert sha(Path(r["snapshot"]))==r["sha256"]
for r in entry["current_entrypoints"]:assert sha(Path(r["path"]))==r["sha256"]
assert sha(Path(entry["diff"]["path"]))==entry["diff"]["sha256"]
fixed_path=PROJECT/"beca_fixed_transfer_20261030/results/final_review.json"
diag_path=PROJECT/"beca_score_diagnosis_20261031/results/final_review.json"
paper_path=PROJECT/"paper_readiness_20261030/results/manuscript_review_v2.json"
fixed,diag,paper=map(load,[fixed_path,diag_path,paper_path])
assert fixed["main_counts"]==[[14,13,15,2,26],[15,13,11,6,26]]and fixed["model_image_forwards"]==180
assert fixed["actually_viewed_images"]==90 and fixed["filename_camera_date_discrepancy_examples"]==2
assert diag["threshold_states"]==122 and diag["zero_W_FA_max_C"]==[1,3]
assert diag["new_model_forwards"]==0 and not diag["deployment_threshold_selected"]
for r,path in[(fixed,fixed_path),(diag,diag_path)]:
    directory=path.parents[1]
    for relative,digest in r["evidence_hashes"].items():assert sha(directory/relative)==digest
    for row in r["documents"]:assert sha(Path(row["path"]))==row["sha256"]
for row in paper["documents"]+paper["source_files"]+paper["tools"]:assert sha(Path(row["file"]))==row["sha256"]
assert paper["claims"]==15 and paper["numeric_table_rows_verified"]==10 and not paper["ready_for_submission"]
access_path=PROJECT/"beca_score_diagnosis_20261031/evidence/current_board_access_observation.json"
access=load(access_path);assert not access["COM6_enumerated"]and access["open_candidates"]==[]
assert not access["network_configuration_changed"]and not access["credentials_sent"]
records=list(previous["current_numeric_record_files"])
for path in[fixed_path,diag_path,paper_path,access_path]:records.append({"path":str(path),"sha256":sha(path)})
for r in records:assert sha(Path(r["path"]))==r["sha256"]
main=PROJECT/"研究阶段总结_20261030.md";content=main.read_text(encoding="utf-8")
assert "更新：2026年10月31日。"in content and "固定迁移阶段已隔离受影响ID"in content
assert "| 原 | 14 | 51.46% | 13 | 15 | 2 | 26 |"in content
assert "| Cows域 | 15 | 48.50% | 13 | 11 | 6 | 26 |"in content
links=[]
for m in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",content):
    target=unquote((m[1]or m[2]).strip())
    if target.startswith(("http://","https://","#")):continue
    p=Path(target);p=p if p.is_absolute()else main.parent/p
    assert p.exists(),target;links.append(str(p))
value=dict(previous)
value.update({
    "status":"CURRENT_OVERVIEW_V21_FIXED_EXTERNAL_TRANSFER_POSTHOC_BOUND_V2_DRAFT_AND_FRESH_ACCESS_SCOPE_REVIEWED",
    "created_UTC":datetime.now(timezone.utc).isoformat(),"document":{"path":str(main),"sha256":sha(main)},
    "review_method":"Previously reviewed V20 retained sections match snapshot; every V21 changed passage and complete BECA transfer/score diagnosis/v2 manuscript read. No new original board results certified.",
    "previous_complete_manual_read_provenance":"overview_review_20261030_v20_sources.json",
    "previous_review_preserved":"overview_review_20261030_v20_sources.json",
    "previous_overview_snapshot":{"path":str(snapshot),"sha256":sha(snapshot)},
    "entrypoint_update_evidence":{"path":str(entry_path),"sha256":sha(entry_path)},
    "changed_text_evidence":entry["diff"],"current_numeric_record_files":records,
    "local_overview_links_checked":len(links),
    "manual_review_topics":previous["manual_review_topics"]+[
        "Completed fixed BECA20/90 180CPU forwards and480decisions distinct from earlier metadata-only stage",
        "Main false accept26/30 both models, original higher workpoints all retained",
        "90 original images viewed; filename dates not independent capture-clock proof",
        "Posthoc122states zeroWFA C1/C3 bound is not calibration or new deployment threshold",
        "New paper v2 and15claims reflect negative external evidence; v1 hashes unchanged",
        "Fresh localLAN22/9090 candidates empty and COM6 not enumerated; no reset/network mutations or SD-loss claim",
        "Original actual-trigger4run raw/photos/terminal and independent events/current12IDs still pending"
    ],
    "new_external_transfer_CPU_image_forwards":180,"new_score_diagnosis_model_forwards":0,
    "BECA_primary_counts":fixed["main_counts"],"BECA_author_labels_independently_certified":False,
    "BECA_real_capture_dates_certified":False,"BECA_posthoc_zero_W_FA_max_C":[1,3],
    "BECA_20_IDs_now_seen":True,"paper_draft_version":2,"paper_ready_for_submission":False,
    "current_board_access_observation":{"path":str(access_path),"sha256":sha(access_path)},
    "current_board_access_restored":False,"current_COM6_enumerated":False,
    "main_paper_contribution_verified":False,"whole_goal_complete":False
})
out=ROOT/"results/overview_review_20261031_v21_transfer.json";assert not out.exists()
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"main_links":len(links),"bound_records":len(records),"whole_goal_complete":False}))
