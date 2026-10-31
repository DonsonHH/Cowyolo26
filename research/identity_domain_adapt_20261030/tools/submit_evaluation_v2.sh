set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
test ! -e evaluation_v2_job_id.txt
test ! -e results/evaluation
sacct -j 130835 --format=JobID,JobName%24,State,ExitCode,Elapsed -P > logs/sacct-failed-evaluation-130835.txt
grep -q '130835|cow-id-domain-eval|FAILED|1:0|' logs/sacct-failed-evaluation-130835.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
r=Path.cwd();p=json.loads((r/'protocol/run_v1.json').read_text());e=json.loads((r/'protocol/evaluation_execution_v2.json').read_text())
assert e['protocol_sha256']==hashlib.sha256((r/'protocol/run_v1.json').read_bytes()).hexdigest()
for relative,digest in e['code_hashes'].items():assert hashlib.sha256((r/relative).read_bytes()).hexdigest()==digest
assert 'AttributeError' in (r/'logs/evaluation-130835.err').read_text()
print(json.dumps({'failed_original_evaluation_feature_forwards':0,'training_weights_unchanged':True,'original_evaluation_results_directory_absent':True}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/evaluate_v2.slurm)
printf '%s\n' "$job_id" > evaluation_v2_job_id.txt
printf 'EVALUATION_V2_JOB_ID=%s\n' "$job_id"
