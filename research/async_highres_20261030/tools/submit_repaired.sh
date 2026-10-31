set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly
cd /share/home/renly/projects/idcoo_research_20261026/async_highres_20261030
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
root=Path.cwd();old=root/'tools/reference.slurm';raw=old.read_bytes();assert hashlib.sha256(raw).hexdigest()=='6b188b77dcca330fc61ee4b5883d7c9aa0ecb80e11d958e099a3c917a2f00704'
target=root/'tools/reference_lf.slurm';assert not target.exists();new=raw.replace(b'\r\n',b'\n');assert hashlib.sha256(new).hexdigest()=='b38427277ad668d61a19b0730ad249e149c234d3b08167456cbbcab9495854dd'
with target.open('xb') as f:f.write(new)
p=json.loads((root/'protocol/reference_v1.json').read_text())
for row in p['input_files']:assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
print(json.dumps({'status':'ONLY_BATCH_SCRIPT_LINE_ENDINGS_NORMALIZED_INPUTS_UNCHANGED','queries':p['query_count']}))
PY
sbatch --parsable tools/reference_lf.slurm
