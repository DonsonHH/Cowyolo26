from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote
import hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

previous = load(ROOT/"results/overview_review_20261030_v18_interruption.json")
assert previous["complete_current_review_coverage"]
entry_path = ROOT/"results/entrypoint_update_20261030_v19_paper.json"
entry = load(entry_path)
main = PROJECT/"研究阶段总结_20261030.md"
snapshot = ROOT/"snapshots/overview_v18_before_paper_draft/研究阶段总结_20261030.md"
assert sha(snapshot) == previous["document"]["sha256"]
for item in entry["previous_files_and_snapshots"]:
    assert sha(Path(item["snapshot"])) == item["sha256"]
for item in entry["current_entrypoints"]:
    assert sha(Path(item["path"])) == item["sha256"]
assert sha(Path(entry["diff"]["path"])) == entry["diff"]["sha256"]
records = list(previous["current_numeric_record_files"])
new_records = [
    PROJECT/"paper_readiness_20261030/results/manuscript_review_v1.json",
    PROJECT/"identity_trigger_pair_20261030/evidence/router_discovery_v1.json",
    PROJECT/"identity_trigger_pair_20261030/evidence/router_serial_observation_v1.json",
]
for path in new_records:
    records.append({"path":str(path),"sha256":sha(path)})
for item in records:
    assert sha(Path(item["path"])) == item["sha256"]
paper = load(new_records[0])
assert not paper["ready_for_submission"] and not paper["actual_trigger_originals_obtained"]
for item in paper["documents"] + paper["method_sources_bound"] + paper["result_sources_bound_and_hash_verified"] + paper["tools"]:
    assert sha(Path(item["file"])) == item["sha256"]
router, serial = map(load,new_records[1:])
assert router["PC_IP"] == "192.168.3.13" and router["open_candidates"] == []
assert not router["network_configuration_changed"] and not router["credentials_sent"]
assert serial["bytes"] == 0 and not serial["reset_or_baud_changed"]
local = []
for match in re.finditer(r"\]\((?:<([^>]+)>|([^\)]+))\)",main.read_text(encoding="utf-8")):
    target = unquote((match[1] or match[2]).strip())
    if target.startswith(("http://","https://","#")):
        continue
    path = Path(target)
    if not path.is_absolute():
        path = main.parent/path
    assert path.exists(), target
    local.append(str(path))
value = dict(previous)
value.update({
    "status":"CURRENT_OVERVIEW_V19_PAPER_DRAFT_NUMBERS_SCOPE_AND_UNCHANGED_TRIGGER_GAPS_REVIEWED",
    "created_UTC":datetime.now(timezone.utc).isoformat(),
    "document":{"path":str(main),"sha256":sha(main)},
    "review_method":"Retained V18 sections match their reviewed snapshot; every V19 added/changed passage and all new manuscript/literature text manually read. No new board raw results verified.",
    "previous_complete_manual_read_provenance":"overview_review_20261030_v18_interruption.json",
    "previous_review_preserved":"overview_review_20261030_v18_interruption.json",
    "previous_overview_snapshot":{"path":str(snapshot),"sha256":sha(snapshot)},
    "entrypoint_update_evidence":{"path":str(entry_path),"sha256":sha(entry_path)},
    "changed_text_evidence":entry["diff"],
    "current_numeric_record_files":records,
    "local_overview_links_checked":len(local),
    "manual_review_topics":previous["manual_review_topics"]+[
        "All five nearest-paper mechanisms, source read levels and unmatched comparison conditions",
        "Ten-ID three-image gallery versus six-ID thirty-image system gallery",
        "Model-specific calibration thresholds versus shared legacy system threshold",
        "Prepared lowres input, fixed ten jobs and actual-trigger highres producer distinguished",
        "Candidate rank versus correct automatic acceptance and unknown false acceptance",
        "Processed rate versus per-frame deadlines and enqueue-to-result timing",
        "New draft has no full actual-trigger results or publication-ready claim",
        "Router connection is user-reported; last local scan and passive UART observations do not prove board identity or current service state"
    ],
    "paper_draft_self_reviewed":True,
    "paper_ready_for_submission":False,
    "new_model_forwards_by_paper_preparation":0,
    "new_board_experiments_by_paper_preparation":0,
    "current_board_access_restored":False,
    "whole_goal_complete":False,
})
out = ROOT/"results/overview_review_20261030_v19_paper.json"
assert not out.exists()
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"main_local_links":len(local),"bound_records":len(records),"whole_goal_complete":False}))
