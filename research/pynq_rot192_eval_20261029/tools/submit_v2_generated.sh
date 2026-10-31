set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130567 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json,subprocess
root=Path('pynq_rot192_eval_20261029');archive=Path('pynq_rot192_eval_20261029_v2_inputs.tar.gz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='73902f0bd84cc5e788ea75729c7e2f9b5d0e70e446dbace0611a9737fe06cdf1'
state=subprocess.check_output(['sacct','-j','130567','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('FAILED|1:0')
assert (root/'results/quality/validation_metrics.json').exists() and not (root/'results/quality_v2').exists()
with tarfile.open(archive) as tar:
 for item in tar.getmembers():
  assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
  target=(root/item.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
print('FAILED130567_PRESERVED;ALL8_EXACT_GPU_INPUT_GATES_BEFORE_NEW_FORWARDS')
PY
sbatch --parsable pynq_rot192_eval_20261029/tools/run_v2.slurm
