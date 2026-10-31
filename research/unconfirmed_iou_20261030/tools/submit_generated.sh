set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json
a=Path('unconfirmed_iou_20261030_control_inputs_v1.tar.gz');root=Path('unconfirmed_iou_20261030');assert not root.exists() and hashlib.sha256(a.read_bytes()).hexdigest()=='b8b0ad9c1e8df324a75832a486afcfdd4ef89717ad00bde9fcff673cb050a614'
root.mkdir()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
for name in ['results','logs','evidence']:(root/name).mkdir(exist_ok=True)
p=json.loads((root/'protocol/control_v1.json').read_text())
for c in p['caches']:
 assert hashlib.sha256(Path(c['raw_file']).read_bytes()).hexdigest()==c['raw_sha256'],c['id']
 assert hashlib.sha256(Path(c['trace_file']).read_bytes()).hexdigest()==c['trace_sha256'],c['id']
print('ALL111_/share/home/renly/projects/idcoo_research_20261026_RAW_AND_BASELINE_FILES_EXIST_AND_b8b0ad9c1e8df324a75832a486afcfdd4ef89717ad00bde9fcff673cb050a614_MATCH_BEFORE_SUBMISSION')
PY
sbatch --parsable unconfirmed_iou_20261030/tools/control.slurm
