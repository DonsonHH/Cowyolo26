from pathlib import Path
from datetime import date,datetime,timezone
from collections import Counter,defaultdict
import ast,hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=ROOT/"protocol/run_v1.json";p=load(plan)
assert not list((ROOT/"evidence").glob("BECA_img_*"))
assert not (ROOT/"input").exists()
assert len(p["images"])==p["image_count"]==90
assert [r["index"]for r in p["images"]]==list(range(90))
assert Counter(r["purpose"]for r in p["images"])=={"gallery":30,"known_query":30,"unknown_query":30}
excluded=set(p["excluded_metadata_conflict_IDs"]+p["excluded_seen_QA_IDs"])
assert not excluded&set(p["roles"]["registered"]+p["roles"]["unknown"])
assert len(set(p["roles"]["registered"]+p["roles"]["unknown"]))==20
for ID in p["roles"]["registered"]:
    gallery=[r for r in p["images"]if r["publisher_identity"]==ID and r["purpose"]=="gallery"]
    query=[r for r in p["images"]if r["publisher_identity"]==ID and r["purpose"]=="known_query"]
    assert len(gallery)==len(query)==3
    assert len({r["date"]for r in gallery+query})==6
    assert (date.fromisoformat(min(r["date"]for r in query))-date.fromisoformat(max(r["date"]for r in gallery))).days>=30
for ID in p["roles"]["unknown"]:
    selected=[r for r in p["images"]if r["publisher_identity"]==ID]
    assert len(selected)==3 and all(r["purpose"]=="unknown_query"for r in selected)
    assert len({r["date"]for r in selected})==3
for row in p["source_bindings"]:assert sha(Path(row["file"]))==row["sha256"]
old=load(PROJECT/"identity_final20_20261030/protocol/execution_v1.json")
assert p["models"]==old["models"]and p["threshold_policies"]==old["threshold_policies"]
for name in ["evaluate_transfer.py","admit_inputs_v1.py","frozen_body_tensor.py","freeze_run_v1.py","freeze_execution_v1.py"]:
    ast.parse((ROOT/"tools"/name).read_text(encoding="utf-8"))
assert sha(ROOT/"tools/frozen_body_tensor.py")==p["frozen_body_tensor_SHA256"]
files=[f"tools/{name}"for name in["evaluate_transfer.py","admit_inputs_v1.py","frozen_body_tensor.py","acquire_inputs_v1.ps1",
                                "fetch_BECA_range_v1.ps1","evaluation.slurm","collect_final.sh","freeze_run_v1.py","freeze_execution_v1.py"]]
value={"status":"TRANSFER_MODELS_FIXED_WORKPOINTS_CODE_METRICS_AND_NO_PIXEL_ACCESS_REVIEWED_BEFORE_SELECTED_MEMBER_REQUEST",
       "created_UTC":datetime.now(timezone.utc).isoformat(),"protocol_sha256":sha(plan),
       "models":p["models"],"threshold_policies":p["threshold_policies"],"batch":p["batch"],
       "Torch_version":p["Torch_version"],"Pillow_version":p["Pillow_version"],
       "bootstrap_seed":p["bootstrap_seed"],"bootstrap_draws":p["bootstrap_draws"],"bootstrap_unit":p["bootstrap_unit"],
       "tensor_anchor_indices":p["tensor_anchor_indices"],"expected_model_image_forwards":180,"expected_network_calls":16,
       "warmups":0,"new_training_updates":0,"new_board_forwards":0,"new_pixels_requested_at_freeze":0,
       "file_hashes_verified_before_every_model_forward_stage":True,
       "files_sha256":{name:sha(ROOT/name)for name in files},
       "reviewer_kind":"assistant_manual_code_and_metadata_review_before_pixels",
       "whole_goal_complete":False}
out=ROOT/"protocol/execution_v1.json";assert not out.exists()
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"protocol_sha256":sha(plan),"execution_sha256":sha(out),"files":len(files),"expected_model_image_forwards":180}))
