set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028
cd "$root"
jobid=$(cat probe_job_id.txt)
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "logs/probe-$jobid.err" || cat "logs/probe-$jobid.err"
if test "$(sacct -j "$jobid" -X -n -o State | xargs)" != COMPLETED; then exit 0; fi
cat results/case_probe/summary.json
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
r=Path('/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
job=(r/'probe_job_id.txt').read_text().strip()
files=[r/'protocol/case_probe_v1.json',r/'probe_job_id.txt',r/'tools/case_probe.py',r/'tools/case_probe.slurm']
files+=list((r/'results/case_probe').glob('*.json'))+[r/f'logs/probe-{job}.out',r/f'logs/probe-{job}.err']
archive=r/'results/probe_delivery.tar.gz';assert not archive.exists()
rows=[{'path':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
mp=r/'results/probe_delivery_manifest.json';mp.write_text(json.dumps(rows,indent=2))
with tarfile.open(archive,'w:gz') as tf:
    for p in files:tf.add(p,arcname=p.relative_to(r).as_posix())
    tf.add(mp,arcname='delivery_manifest.json')
record={'manifest_files':len(rows),'archive_members':len(rows)+1,'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp)}
(r/'results/probe_delivery_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
PY
