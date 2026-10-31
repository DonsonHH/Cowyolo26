from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import hashlib,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
SOURCE=PROJECT/"beca_fixed_transfer_20261030";OUT=SOURCE/"delivery/results/evaluation"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result_dir=ROOT/"results";result_dir.mkdir(exist_ok=True)
target=result_dir/"score_diagnosis_v1.json";assert not target.exists()
source_review=load(SOURCE/"results/final_review.json")
assert source_review["model_image_forwards"]==180 and source_review["source_images"]==90
for name,digest in source_review["evidence_hashes"].items():assert sha(SOURCE/name)==digest
protocol=load(SOURCE/"protocol/run_v1.json")
sources=[SOURCE/"protocol/run_v1.json",SOURCE/"protocol/execution_v1.json",SOURCE/"results/independent_verification.json",
         SOURCE/"results/visual_review.json",SOURCE/"results/final_review.json",
         OUT/"old_C/retrieval_unthresholded.json",OUT/"new_C_domain_seed26/retrieval_unthresholded.json",
         OUT/"all_outcomes.json",OUT/"all_decisions.json"]
constraints={
    "zero_observed_W_and_FA":lambda x:x["W"]==0 and x["FA"]==0,
    "unknown_FA_at_most1_of30_W_unconstrained":lambda x:x["FA"]<=1,
    "combined_W_plus_FA_at_most1":lambda x:x["W"]+x["FA"]<=1,
    "observed_accepted_error_fraction_at_most5percent":lambda x:x["accepted"]==0 or (x["W"]+x["FA"])*20<=x["accepted"],
}
models={}
for model in["old_C","new_C_domain_seed26"]:
    rows=load(OUT/model/"retrieval_unthresholded.json")
    assert len(rows)==60 and sum(r["is_known"]for r in rows)==30
    for r in rows:
        r["category"]="correct_rank1"if r["is_known"]and r["identity"]==r["predicted_id"]else"wrong_rank1"if r["is_known"]else"unknown"
        assert math.isfinite(r["score"])
    counts=Counter(r["category"]for r in rows);assert counts["unknown"]==30
    groups={s:[r for r in rows if r["score"]==s]for s in sorted({r["score"]for r in rows},reverse=True)}
    states=[{"state_index":0,"threshold":float(np.nextafter(max(groups),np.inf)),"acceptance_interval":"threshold > maximum_observed_score",
             "C":0,"W":0,"U":30,"FA":0,"accepted":0,"accepted_error_fraction":None,"newly_accepted_source_indices":[]}]
    c=w=fa=0
    for score,subset in groups.items():
        c+=sum(r["category"]=="correct_rank1"for r in subset)
        w+=sum(r["category"]=="wrong_rank1"for r in subset)
        fa+=sum(r["category"]=="unknown"for r in subset)
        accepted=c+w+fa
        states.append({"state_index":len(states),"threshold":score,"acceptance_interval":"current_score >= threshold > next_lower_distinct_score; exact decision state represented by threshold=current_score",
                       "C":c,"W":w,"U":30-c-w,"FA":fa,"accepted":accepted,
                       "accepted_error_fraction":(w+fa)/accepted,"newly_accepted_source_indices":[r["source_index"]for r in subset]})
    assert states[-1]["C"]==counts["correct_rank1"]and states[-1]["W"]==counts["wrong_rank1"]and states[-1]["FA"]==30
    upper_bounds={}
    for name,allows in constraints.items():
        valid=[r for r in states if allows(r)];best=max(r["C"]for r in valid)
        maxima=[r for r in valid if r["C"]==best]
        upper_bounds[name]={"max_C":best,"correct_acceptance_coverage":best/30,
                            "all_maximizing_state_indices":[r["state_index"]for r in maxima],
                            "maxima_C_W_U_FA":[[r[k]for k in["C","W","U","FA"]]for r in maxima],
                            "deployment_threshold_selected":False}
    distribution={}
    for category in["correct_rank1","wrong_rank1","unknown"]:
        values=np.array([r["score"]for r in rows if r["category"]==category])
        distribution[category]={"queries":len(values),"minimum":float(values.min()),"median":float(np.median(values)),"maximum":float(values.max())}
    worst_errors=sorted([r for r in rows if r["category"]!="correct_rank1"],key=lambda r:(-r["score"],r["source_index"]))
    max_error=worst_errors[0]["score"]
    correct_above=[r["source_index"]for r in rows if r["category"]=="correct_rank1"and r["score"]>max_error]
    assert len(correct_above)==upper_bounds["zero_observed_W_and_FA"]["max_C"]
    order_correct=sum(r["category"]=="correct_rank1"for r in rows)
    models[model]={"threshold_states":states,"state_count":len(states),"category_counts":dict(counts),
                   "rank1_upper_bound_even_with_per_query_correctness_oracle":order_correct,
                   "constrained_correct_acceptance_upper_bounds":upper_bounds,"score_distributions":distribution,
                   "highest_score_error":{k:worst_errors[0][k]for k in["source_index","identity","is_known","predicted_id","score","category"]},
                   "correct_rank1_queries_above_all_errors":correct_above,
                   "primary_workpoint":next(r for r in load(OUT/"all_outcomes.json")if r["model"]==model and r["policy"]==protocol["primary_policy"])}
result={"status":"ALL_REACHABLE_SINGLE_ABSOLUTE_SCORE_THRESHOLD_STATES_ENUMERATED_POSTHOC_DIAGNOSTIC_NOT_CALIBRATION",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"models":models,"registered_queries":30,"unknown_queries":30,
        "source_bindings":[{"file":str(p.resolve()),"sha256":sha(p)}for p in sources],
        "source_labels_and_dates_independently_certified":False,
        "constraints_chosen_after_fixed_transfer_results":True,"new_confirmatory_or_out_of_sample_result":False,
        "deployment_threshold_selected":False,"default_model_or_threshold_changed":False,"new_model_forwards":0,
        "new_training_updates":0,"new_pixels_read":0,"new_board_work":0,"whole_goal_complete":False}
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":result["status"],"upper_bounds":{m:v["constrained_correct_acceptance_upper_bounds"]for m,v in models.items()}},ensure_ascii=False))
