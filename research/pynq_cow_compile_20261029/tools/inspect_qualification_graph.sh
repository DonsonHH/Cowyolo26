set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026
PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline env/bin/python - <<'PY'
from pathlib import Path
import json,numpy as np
root=Path('pynq_cow_compile_20261029/results/qualification/compiled/model');g=json.loads((root/'graph.json').read_text())
with np.load(root/'constants.npz') as arrays:
    rows=[]
    for node in g['nodes']:
        if node['op'] not in ['Tile','Gather','Mod']:continue
        rows.append({'node':node,'input_shapes':{k:g['tensors'].get(k) for k in node['inputs']},
           'output_shapes':{k:g['tensors'].get(k) for k in node['outputs']},
           'small_constants':{k:arrays[k].tolist() for k in node['inputs'] if k in arrays and arrays[k].size<=20}})
print(json.dumps({'status':'READONLY_EXPORTED_NEW_OP_SHAPES','unsupported_by_original_engine':rows}))
PY
