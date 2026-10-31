set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028
cd "$root"
test "$(sacct -j "$(cat job_id.txt)" -X -n -o State | xargs)" = COMPLETED
test ! -e results/delivery.tar.gz
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
r=Path('/share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028');p=json.loads((r/'protocol/regression_v1.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[r/'job_id.txt',r/'protocol/regression_v1.json',r/'results/summary.json',r/'results/scored_conditions.csv',r/'results/method_scope_verification.json']
files+=list((r/'input').glob('*'))+list((r/'tools').glob('*.py'))+list((r/'tools').glob('*.slurm'))+list((r/'logs').glob('replay-*'))
for d in (r/'results').iterdir():
    if d.is_dir() and any(d.name==m['name']+'_'+v for m in p['models'] for v in p['variants']):files+=list(d.iterdir())
mapping={f.relative_to(r).as_posix():f for f in files};assert len(mapping)==len(files)
for model in p['models']:
    for item in model['cache_files']:
        f=Path(item['path']);assert sha(f)==item['sha256'];mapping['original_cache/'+model['name']+'/'+f.name]=f
ref=Path(p['reference_author_summary']['path']);assert sha(ref)==p['reference_author_summary']['sha256'];mapping['reference_author_summary.json']=ref
manifest=[{'path':name,'bytes':f.stat().st_size,'sha256':sha(f)} for name,f in sorted(mapping.items())]
mp=r/'results/delivery_manifest.json';mp.write_text(json.dumps(manifest,indent=2));archive=r/'results/delivery.tar.gz'
with tarfile.open(archive,'w:gz') as tf:
    for name,f in sorted(mapping.items()):tf.add(f,arcname=name)
    tf.add(mp,arcname='delivery_manifest.json')
record={'manifest_files':len(manifest),'archive_members':len(manifest)+1,'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp)}
(r/'results/delivery_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
PY
