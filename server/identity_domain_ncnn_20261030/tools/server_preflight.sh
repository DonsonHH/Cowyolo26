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
PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029/dependencies /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import importlib.util,hashlib,json
spec=importlib.util.find_spec('pnnx');folder=Path(spec.origin).parent
files=[p for p in folder.rglob('*')if p.is_file()and p.name in['pnnx','pnnx.py']]
print(json.dumps({'pnnx_module':spec.origin,'candidate_converter_files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in files]}))
checkpoint=Path('/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030/results/training/C_domain_seed26/last_encoder.pt')
print(json.dumps({'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest()}))
PY
