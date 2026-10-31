set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028
cd "$root"
test "$(sacct -j "$(cat replay_job_id.txt)" -X -n -o State | xargs)" = COMPLETED
test ! -e results/replay_delivery.tar.gz
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
r=Path('/share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=list((r/'protocol').glob('*.json'))+list((r/'tools').glob('*.py'))+list((r/'tools').glob('*.slurm'))+list((r/'input').glob('*.py'))
files+=[r/'red_job_id.txt',r/'replay_job_id.txt']+list((r/'logs').glob('red-*'))+list((r/'logs').glob('replay-*'))
files+=list((r/'results').glob('*tests.json'))+list((r/'results').glob('*tests.log'))
files+=[r/'results/method_scope_verification.json',r/'results/summary.json',r/'results/candidate_test_process.log']
for folder in (r/'results').glob('*_seed*'):
    if folder.is_dir():files+=list(folder.iterdir())
assert len(files)==len(set(files)) and all(p.is_file() for p in files)
rows=[{'path':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
mp=r/'results/replay_manifest.json';mp.write_text(json.dumps(rows,indent=2))
archive=r/'results/replay_delivery.tar.gz'
with tarfile.open(archive,'w:gz') as tf:
    for p in sorted(files):tf.add(p,arcname=p.relative_to(r).as_posix())
    tf.add(mp,arcname='delivery_manifest.json')
record={'manifest_files':len(rows),'archive_members':len(rows)+1,'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp)}
(r/'results/replay_delivery_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
PY
