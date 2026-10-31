set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/paired_event_intake_20261028
cd "$root"
jobid=$(cat exit_probe_job_id.txt)
test "$(sacct -j "$jobid" -X -n -o State | xargs)" = COMPLETED
test ! -e results/exit_probe_delivery.tar.gz
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
r=Path('/share/home/renly/projects/idcoo_research_20261026/paired_event_intake_20261028')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
job=(r/'exit_probe_job_id.txt').read_text().strip()
files=[r/'exit_probe_job_id.txt',r/'protocol/exit_probe_v1.json',r/'tools/exit_probe.py',r/'tools/exit_probe.slurm',r/f'logs/exit_probe-{job}.out',r/f'logs/exit_probe-{job}.err']
files+=list((r/'results/exit_probe').glob('*.json'))
rows=[{'path':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
mp=r/'results/exit_probe_manifest.json';mp.write_text(json.dumps(rows,indent=2))
archive=r/'results/exit_probe_delivery.tar.gz'
with tarfile.open(archive,'w:gz') as tf:
    for p in files:tf.add(p,arcname=p.relative_to(r).as_posix())
    tf.add(mp,arcname='delivery_manifest.json')
record={'manifest_files':len(rows),'archive_members':len(rows)+1,'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp)}
(r/'results/exit_probe_delivery_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
PY
