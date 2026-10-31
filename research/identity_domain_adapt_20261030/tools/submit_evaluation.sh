set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
test ! -e evaluation_job_id.txt
sacct -j 130777 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P > logs/sacct-training-130777.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib
r=Path.cwd();p=json.loads((r/'protocol/run_v1.json').read_text());account=(r/'logs/sacct-training-130777.txt').read_text().splitlines()
for index,condition in enumerate(p['conditions']):
 assert any(line.startswith('130777_'+str(index)+'|cow-id-domain-pair|COMPLETED|0:0|')for line in account)
 f=r/'results/training'/condition['name'];t=json.loads((f/'terminal.json').read_text());assert t['status']=='ONE_DOMAIN_TRAINING_CONDITION_COMPLETE'and t['optimizer_updates']==300 and t['training_image_forwards']==9600
 assert hashlib.sha256((f/'last_encoder.pt').read_bytes()).hexdigest()==t['last_encoder_sha256'];assert len((f/'actual_updates.jsonl').read_text().splitlines())==300
print(json.dumps({'six_real_training_runs_completed':True,'formal_updates':1800,'training_image_forwards':57600,'new_eval_forwards':0}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/evaluate.slurm)
printf '%s\n' "$job_id" > evaluation_job_id.txt
printf 'EVALUATION_JOB_ID=%s\n' "$job_id"
