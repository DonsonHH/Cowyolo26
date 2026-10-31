set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_workload_20261031
tracker_job_id=$(cat tracker_job_id.txt)
sacct -j "$tracker_job_id" --format=JobID,JobName%40,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2 > logs/tracker_sacct.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
job=(root/'tracker_job_id.txt').read_text().strip()
records=[line.split('|')for line in(root/'logs/tracker_sacct.txt').read_text().splitlines()]
assert any(row[:4]==[job,'cow-parent-track','COMPLETED','0:0']for row in records)
summary=json.loads((root/'results/tracker_replay/summary.json').read_text())
figure=json.loads((root/'results/figure_manifest.json').read_text())
assert summary['status']=='ALL8_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES'
assert summary['Slurm_job_id']==figure['Slurm_job_id']==job
assert summary['observation_ticks']==17379 and summary['counter_paths']==16 and summary['new_model_forwards']==0
assert len(figure['files'])==2 and figure['new_model_forwards']==0
assert sha(root/'tracker_input/workload_summary.json')==figure['source_sha256']
for row in figure['files']:assert sha(root/row['file'])==row['sha256']
assert not(root/f'logs/tracker-{job}.err').read_text().strip()
files=sorted([p for directory in['tools','tracker_input','results','logs']for p in(root/directory).rglob('*')if p.is_file()and'__pycache__'not in p.parts]+[root/'tracker_job_id.txt'])
manifest=root/'result_manifest.json';assert not manifest.exists()
manifest.write_bytes((json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}for p in files],indent=2)+'\n').encode())
archive=root/'tracker_reference_delivery_v1.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=3)as tar:
 for path in files+[manifest]:tar.add(path,arcname=path.relative_to(root).as_posix(),recursive=False)
for row in json.loads(manifest.read_text()):assert sha(root/row['file'])==row['sha256']
transfer={'status':'TERMINAL_EIGHT_PERIOD_REFERENCE_AND_FIGURE_ARCHIVE_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
          'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,
          'manifest_files':len(files),'completed_job_id':job,'new_model_forwards':0}
with(root/'reference_transfer_v1.json').open('x')as stream:json.dump(transfer,stream,indent=2);stream.write('\n')
print(json.dumps(transfer),flush=True)
PY
