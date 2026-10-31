set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130518 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130518 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029
../env/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('.')
for path in sorted((root/'results/training').glob('*/progress.json')):
    print('PROGRESS',path.parent.name,json.loads(path.read_text()))
for path in sorted((root/'results/training').glob('*/condition_complete.json')):
    x=json.loads(path.read_text());print('COMPLETE',x['condition']['condition_id'],x['training_batches'],x['optimizer_steps'],x['last_checkpoint_sha256'])
PY
for file in logs/train-130518_0.err logs/train-130518_1.err logs/train-130518_2.err; do
    if [ -f "$file" ]; then tail -n 4 "$file"; fi
done
