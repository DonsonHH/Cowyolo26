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
import hashlib, importlib.util, json
p=Path('/share/home/renly/projects/idcoo_research_20261026')
files=['models/yolo26n.pt', 'detector_factorial_20261029/results/training/S192_rot90_seed26/weights/last.pt', 'mosaic_pair_20261030/results/training/mosaic050_seed26/weights/last.pt']
print(json.dumps({'models':[{'relative_file':f,'bytes':(p/f).stat().st_size,'sha256':hashlib.sha256((p/f).read_bytes()).hexdigest()} for f in files], 'pycocotools_available':importlib.util.find_spec('pycocotools') is not None}))
PY
