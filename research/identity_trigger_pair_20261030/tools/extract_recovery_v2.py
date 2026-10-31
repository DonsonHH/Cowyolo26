"""Extract actual saved originals; preserve cold-boot provenance without fabricating PL state."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=load(ROOT/"evidence/recovery_result_transfer_v1.json")
archive=ROOT/"trigger_pair_interruption_originals_v1.tar.xz"
assert archive.stat().st_size==meta["bytes"]and sha(archive)==meta["sha256"]
assert meta["source_terminal_consistent_complete"]
out=ROOT/"delivery";out.mkdir(exist_ok=False)
with tarfile.open(archive)as tar:
    members=tar.getmembers()
    assert len(members)==meta["members"]and len({r.name for r in members})==len(members)
    for member in members:
        rel=PurePosixPath(member.name)
        assert member.isfile()and not rel.is_absolute()and".."not in rel.parts
        path=(out/member.name).resolve();assert path.is_relative_to(out.resolve())and not path.exists()
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
manifest=load(out/"interruption_recovery_manifest_v1.json")
assert len(manifest)==meta["manifest_files"]
assert {r["file"]for r in manifest}=={r.name for r in members}-{"interruption_recovery_manifest_v1.json"}
for r in manifest:
    path=out/r["file"];assert path.stat().st_size==r["bytes"]and sha(path)==r["sha256"]
assert sha(out/"run_protocol.json")==sha(ROOT/"protocol/run_v1.json")=="4217824d2964e56218c566a73096a2f282c94020f3176c74bf86cef9a270513c"
p=load(ROOT/"protocol/run_v1.json")
for row in p["payload_files"]:
    assert sha(out/row["file"])==sha(ROOT/"payload"/row["file"])==row["sha256"]
recovery=load(out/"interruption_recovery_v1.json")
assert recovery["source_parent_terminal_consistent_complete"]and recovery["boot_changed_since_experiment"]
assert recovery["source_boot_id"]=="9ecd4ca1-edd1-45f8-aa09-dfac2a089f2f"
assert recovery["collection_boot_id"]==meta["collection_boot_id"]=="e7059099-ecb8-451e-a9aa-a66c8222196b"
assert not recovery["models_or_PL_loaded_or_programmed"]and not recovery["current_loaded_PL_observed"]
state=load(out/"results/record.json");terminal=load(out/"results/terminal.json")
assert state["status"]==terminal["status"]=="ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE"
assert terminal["record_sha256"]==sha(out/"results/record.json")
result={"status":"ALL_SAVED_ORIGINAL163_MEMBERS162_MANIFEST_ROWS_AND_SOURCE_TERMINAL_HASH_VERIFIED_AFTER_COLD_BOOT",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"archive_bytes":meta["bytes"],"archive_SHA256":meta["sha256"],
        "members":len(members),"manifest_files":len(manifest),
        "source_boot_id":recovery["source_boot_id"],"collection_boot_id":recovery["collection_boot_id"],
        "boot_changed":True,"all_bound_runtime_files_match_now":recovery["all_bound_runtime_files_match_now"],
        "current_loaded_O8_verified_or_programmed":False,"experiment_end_PL_record_scope_only":True,
        "source_terminal_complete":True,"actual_timed_O8_forwards_in_original_terminal":terminal["actual_O8_forwards"],
        "full_numeric_or_event_verification_by_this_extraction":False,
        "new_model_forwards":0,"original_experiment_restarted":False,"whole_goal_complete":False}
target=ROOT/"results/recovery_archive_verification_v2.json";assert not target.exists()
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
