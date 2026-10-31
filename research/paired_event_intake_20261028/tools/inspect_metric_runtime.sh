set -euo pipefail
date -u
id -un
hostname
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from importlib.metadata import version
import json
print(json.dumps({'scipy':version('scipy'),'numpy':version('numpy'),'inspection_only':True}))
PY
