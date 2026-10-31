set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_trigger_pair_20261030
test ! -e verification_retry_v2_job_id.txt
sacct -j 130922 --format=JobID,State,ExitCode --parsable2
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
root=Path.cwd()
assert not(root/'results/tracker_replay').exists()and not(root/'results/reference').exists()
for row in json.loads((root/'tracker_input/protocol.json').read_text())['files']:
 assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
e=json.loads((root/'protocol/reference_execution_v1.json').read_text())
for name,digest in e['code_sha256'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
print('Missing pre-frozen provenance artifact repaired; model forwards before this submission=0')
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/reference.slurm)
printf '%s\n' "$job_id" > verification_retry_v2_job_id.txt
printf 'TRIGGER_VERIFICATION_REPAIRED_JOB_ID=%s\n' "$job_id"
