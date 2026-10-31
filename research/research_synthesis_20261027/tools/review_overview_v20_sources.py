from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=load(ROOT/"results/overview_review_20261030_v19_paper.json")
assert previous["complete_current_review_coverage"]
snapshot=ROOT/"snapshots/overview_v19_before_source_recheck/研究阶段总结_20261030.md"
assert sha(snapshot)==previous["document"]["sha256"]
entry_path=ROOT/"results/entrypoint_update_20261030_v20_sources.json";entry=load(entry_path)
for row in entry["previous_files_and_snapshots"]:assert sha(Path(row["snapshot"]))==row["sha256"]
for row in entry["current_entrypoints"]:assert sha(Path(row["path"]))==row["sha256"]
assert sha(Path(entry["diff"]["path"]))==entry["diff"]["sha256"]
stage=PROJECT/"independent_source_recheck_20261030";source_review_path=stage/"results/final_review_v1.json"
review=load(source_review_path)
assert review["metadata_conflict_groups"]==40 and review["byte_verified_conflict_groups"]==2
assert review["CRC_only_remaining_groups"]==38 and review["actually_viewed_frozen_QA_images"]==8
assert review["new_model_forwards"]==review["new_identity_scores"]==review["new_training_updates"]==0
assert not review["new_counting_GT_or_current12_identity_GT"]and not review["board_results_recovered"]
for name,digest in review["evidence_hashes"].items():assert sha(stage/name)==digest
for row in review["documents"]:assert sha(Path(row["path"]))==row["sha256"]
assert sha(Path(review["board_network_observation"]["path"]))==review["board_network_observation"]["sha256"]
records=list(previous["current_numeric_record_files"])+[
    {"path":str(source_review_path),"sha256":sha(source_review_path)},
    {"path":review["board_network_observation"]["path"],"sha256":review["board_network_observation"]["sha256"]}]
for row in records:assert sha(Path(row["path"]))==row["sha256"]
main=PROJECT/"研究阶段总结_20261030.md";content=main.read_text(encoding="utf-8")
links=[]
for m in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",content):
    target=unquote((m[1]or m[2]).strip())
    if target.startswith(("http://","https://","#")):continue
    p=Path(target);p=p if p.is_absolute()else main.parent/p
    assert p.exists(),target;links.append(str(p))
result=dict(previous)
result.update({
    "status":"CURRENT_OVERVIEW_V20_ACTUAL_BECA_SOURCE_QA_CONFLICT_EVIDENCE_AND_UNCHANGED_MAIN_GAPS_REVIEWED",
    "created_UTC":datetime.now(timezone.utc).isoformat(),"document":{"path":str(main),"sha256":sha(main)},
    "review_method":"Retained V19 sections match reviewed snapshot; every V20 change and all new source reports manually read; frozen8 images visually reviewed. No model evaluation or new board raw results claimed.",
    "previous_complete_manual_read_provenance":"overview_review_20261030_v19_paper.json",
    "previous_review_preserved":"overview_review_20261030_v19_paper.json",
    "previous_overview_snapshot":{"path":str(snapshot),"sha256":sha(snapshot)},
    "entrypoint_update_evidence":{"path":str(entry_path),"sha256":sha(entry_path)},
    "changed_text_evidence":entry["diff"],"current_numeric_record_files":records,
    "local_overview_links_checked":len(links),
    "manual_review_topics":previous["manual_review_topics"]+[
        "Author-migrated BECA version and real206 HTTP range retrieval distinguished from403 failed paths",
        "68350 metadata rows matched independent zipfile; full archive MD5 still unverified",
        "12172 combined files not doubled by native aliases; filenames not legal cattle IDs",
        "Forty metadata conflicts versus two full JPEG byte proofs and remaining38 not byte-verified",
        "Frozen8 QA images only; new seen IDs11,65,100 no future final-test claim",
        "Beef dorsal feeding crops and overlays not direct Holstein passage validation",
        "No continuous passage GT, actual identity score, training, or board result recovery added"
    ],
    "new_source_review":{"path":str(source_review_path),"sha256":sha(source_review_path)},
    "new_source_QA_image_decodes":8,"new_model_forwards_by_source_recheck":0,
    "new_counting_or_current12_identity_GT_by_source_recheck":False,
    "new_independent_identity_scores_by_source_recheck":0,
    "main_paper_contribution_verified":False,"whole_goal_complete":False,
})
out=ROOT/"results/overview_review_20261030_v20_sources.json";assert not out.exists()
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":result["status"],"links":len(links),"bound_records":len(records),"whole_goal_complete":False}))
