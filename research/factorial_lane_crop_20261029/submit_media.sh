set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
root=Path('factorial_lane_crop_20261029')
state=subprocess.check_output(['sacct','-j','130559','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0')
assert not (root/'results/media').exists()
assert hashlib.sha256((root/'protocol/media_v1.json').read_bytes()).hexdigest()=='599caf60f2983a3cd09292798e40fb0b9cb39290c9634f0d6afa386e0d02b9e9'
assert json.loads((root/'results/roi/summary.json').read_text())['actual_detector_source_image_forwards']==39810
print('MEDIA_GATE_AND_TERMINAL_DATA_VERIFIED;CU_CPU_ONLY;NO_NEW_NETWORK_FORWARDS')
PY
sbatch --parsable factorial_lane_crop_20261029/media.slurm
