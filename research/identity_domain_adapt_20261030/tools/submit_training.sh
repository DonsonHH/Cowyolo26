set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
test ! -e training_job_id.txt
sacct -j 130772 --format=JobID,JobName%24,State,ExitCode,Elapsed -P > logs/sacct-smoke-130772.txt
grep -q '130772|cow-id-domain-smoke|COMPLETED|0:0|' logs/sacct-smoke-130772.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib
r=Path.cwd();p=json.loads((r/'protocol/run_v1.json').read_text());gate=json.loads((r/'results/smoke/summary.json').read_text())
assert gate['status']=='BOTH_ARMS_ONE_REAL_CUDA_UPDATE_PASS_FORMAL_WEIGHTS_UNTOUCHED' and gate['source_image_forwards']==64 and gate['discarded_optimizer_updates']==2 and gate['formal_updates']==0
assert gate['protocol_sha256']==hashlib.sha256((r/'protocol/run_v1.json').read_bytes()).hexdigest()
for record in gate['records']:assert record['initial_encoder_state_digest']!=record['final_encoder_state_digest'] and record['optimizer_updates']==1
print(json.dumps({'smoke_actual_pass':True,'formal_updates_before_submission':0,'discarded_updates':2}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/train.slurm)
printf '%s\n' "$job_id" > training_job_id.txt
printf 'TRAINING_ARRAY_JOB_ID=%s\n' "$job_id"
