set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 130563 --format=JobID,State,ExitCode,Elapsed -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import subprocess
state=subprocess.check_output(['sacct','-j','130563','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('FAILED|1:0')
root=Path('factorial_lane_crop_20261029');assert (root/'results/media').is_dir() and not (root/'results/media_v2').exists()
print('FAILED_MEDIA_PRESERVED;NEW_PATH_TYPE_FIX_ONLY;NO_INFERENCE_REPEATED')
PY
sbatch --parsable factorial_lane_crop_20261029/media_v2.slurm
