from datetime import datetime,timezone
import hashlib,json,os
from train_condition import ROOT,load,save_new,execute,sha

plan=load(ROOT/"protocol/run_v1.json")
records=[]
for condition in plan["conditions"][:2]:
    records.append(execute(condition,smoke=True))
assert sum(row["optimizer_updates"] for row in records)==2
assert sum(row["training_image_forwards"] for row in records)==64
assert records[0]["initial_encoder_state_digest"]==records[1]["initial_encoder_state_digest"]
result={"status":"BOTH_ARMS_ONE_REAL_CUDA_UPDATE_PASS_FORMAL_WEIGHTS_UNTOUCHED","created_UTC":datetime.now(timezone.utc).isoformat(),
        "Slurm_job_id":os.environ["SLURM_JOB_ID"],"discarded_optimizer_updates":2,"source_image_forwards":64,
        "formal_updates":0,"records":records,"protocol_sha256":sha(ROOT/"protocol/run_v1.json"),"whole_goal_complete":False}
save_new(ROOT/"results/smoke/summary.json",result)
print(json.dumps({key:value for key,value in result.items() if key!="records"}),flush=True)
