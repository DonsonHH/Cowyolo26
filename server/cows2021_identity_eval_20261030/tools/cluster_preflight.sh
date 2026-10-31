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
project=Path('/share/home/renly/projects/idcoo_research_20261026')
paths=[project/'identity_training/models/mobilenet_v3_small-047dcff4.pth',project/'identity_training/results/study/C_letterbox_trained_seed26/best_encoder.pt']
print(json.dumps({'models':[{'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths]}))
PY
