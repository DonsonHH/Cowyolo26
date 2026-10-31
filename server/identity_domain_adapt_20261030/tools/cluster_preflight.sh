set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
id -un
hostname
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
scontrol show partition -o
df -hT /share/home/renly/projects/idcoo_research_20261026
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
paths=[Path('/share/home/renly/projects/idcoo_research_20261026/identity_training/results/study/C_letterbox_trained_seed26/best_encoder.pt'),Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_identity_eval_20261030/protocol/run_v1.json')]
print(json.dumps({'frozen_sources':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}))
PY
