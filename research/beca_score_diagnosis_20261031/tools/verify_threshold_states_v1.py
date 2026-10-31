from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import hashlib,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];O=ROOT/"results"
SOURCE=ROOT.parent/"beca_fixed_transfer_20261030/delivery/results/evaluation"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
path=O/"score_diagnosis_v1.json";diagnosis=load(path)
for source in diagnosis["source_bindings"]:assert sha(Path(source["file"]))==source["sha256"]
checked=0;bounds={}
for model,details in diagnosis["models"].items():
    rows=load(SOURCE/model/"retrieval_unthresholded.json")
    states=details["threshold_states"];assert len(states)==61
    assert len({r["score"]for r in rows})==60
    score_values=sorted({r["score"]for r in rows})
    candidate_thresholds=[float(np.nextafter(max(score_values),np.inf))]+list(reversed(score_values))
    functions={
        "zero_observed_W_and_FA":lambda W,FA,A:W==FA==0,
        "unknown_FA_at_most1_of30_W_unconstrained":lambda W,FA,A:FA<=1,
        "combined_W_plus_FA_at_most1":lambda W,FA,A:W+FA<=1,
        "observed_accepted_error_fraction_at_most5percent":lambda W,FA,A:A==0 or 20*(W+FA)<=A}
    independently=[]
    for i,tau in enumerate(candidate_thresholds):
        known=[r for r in rows if r["is_known"]];unknown=[r for r in rows if not r["is_known"]]
        C=sum(r["score"]>=tau and r["identity"]==r["predicted_id"]for r in known)
        W=sum(r["score"]>=tau and r["identity"]!=r["predicted_id"]for r in known)
        U=sum(r["score"]<tau for r in known);FA=sum(r["score"]>=tau for r in unknown)
        accepted=C+W+FA;error=(W+FA)/accepted if accepted else None
        assert all(states[i][k]==v for k,v in{"threshold":tau,"C":C,"W":W,"U":U,"FA":FA,"accepted":accepted,"accepted_error_fraction":error}.items())
        assert C+W+U==30 and sum(r["score"]>=tau for r in rows)==accepted
        independently.append({"C":C,"W":W,"U":U,"FA":FA,"accepted":accepted})
        # Exact equality, all-midpoint intervals, and reject-all cover all
        # possible decisions for an inclusive single scalar threshold.
        if i>0:
            lower=score_values[-i-1]if i<60 else -1.0
            mid=lower+(tau-lower)/2
            assert [r["source_index"]for r in rows if r["score"]>=tau]==[r["source_index"]for r in rows if r["score"]>=mid]
        checked+=1
    own={}
    for name,allows in functions.items():
        feasible=[(i,r)for i,r in enumerate(independently)if allows(r["W"],r["FA"],r["accepted"])]
        max_c=max(r["C"]for i,r in feasible)
        indices=[i for i,r in feasible if r["C"]==max_c]
        expected=details["constrained_correct_acceptance_upper_bounds"][name]
        assert expected["max_C"]==max_c and expected["all_maximizing_state_indices"]==indices
        assert expected["maxima_C_W_U_FA"]==[[independently[i][k]for k in["C","W","U","FA"]]for i in indices]
        own[name]=max_c
    bounds[model]=own
    categories=Counter("correct_rank1"if r["is_known"]and r["identity"]==r["predicted_id"]else"wrong_rank1"if r["is_known"]else"unknown"for r in rows)
    assert categories==details["category_counts"]
assert checked==122
out=O/"independent_verification_v1.json";assert not out.exists()
result={"status":"ALL122_REACHABLE_STATES_INTERVAL_COVERAGE_AND8_POSTHOC_UPPER_BOUNDS_INDEPENDENTLY_RECOMPUTED",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"threshold_states_verified":checked,
        "constraints_per_model":4,"upper_bounds":bounds,"diagnosis_SHA256":sha(path),
        "new_model_forwards":0,"new_pixels_read":0,"new_training_updates":0,"deployment_threshold_selected":False,
        "new_calibration_or_confirmatory_test":False,"whole_goal_complete":False}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
