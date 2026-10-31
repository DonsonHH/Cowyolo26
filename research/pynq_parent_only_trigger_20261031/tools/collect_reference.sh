set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_trigger_20261031
reference_job_id=$(cat reference_job_id.txt)
sacct -j "$reference_job_id" --format=JobID,JobName%40,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2 > logs/reference_sacct.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
job=(root/'reference_job_id.txt').read_text().strip()
rows=[line.split('|')for line in(root/'logs/reference_sacct.txt').read_text().splitlines()]
assert any(row[:4]==[job,'cow-parent-trigger','COMPLETED','0:0']for row in rows)
s=json.loads((root/'results/reference/summary.json').read_text());t=json.loads((root/'results/tracker_replay/summary.json').read_text())
assert s['Slurm_job_id']==t['Slurm_job_id']==job
assert s['actual_Torch_image_forwards']==13 and s['reused_gallery_vectors']==60 and s['reused_unique_query_features']==12
assert s['status']in['REFERENCE_COMPLETE_ALL_NUMERICS_AND_FIXED_DECISIONS_MATCH','REFERENCE_COMPLETE_WITH_NUMERIC_OR_DECISION_DIFFERENCES']
assert t['status']=='ALL4_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES'
assert t['observation_ticks']==8664 and t['counter_paths']==8
files=sorted([p for folder in['tools','protocol','reference_input','tracker_input','results','logs']for p in(root/folder).rglob('*')if p.is_file()and'__pycache__'not in p.parts]+[root/'reference_job_id.txt'])
manifest=root/'result_manifest.json';assert not manifest.exists()
manifest.write_bytes((json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}for p in files],indent=2)+'\n').encode())
archive=root/'reference_delivery_v1.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=3)as tar:
 for path in files+[manifest]:tar.add(path,arcname=path.relative_to(root).as_posix(),recursive=False)
for row in json.loads(manifest.read_text()):assert sha(root/row['file'])==row['sha256']
transfer={'status':'PARENT_ONLY_DYNAMIC_REFERENCE_ARCHIVE_CLOSED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files),
 'completed_job_id':job,'actual_new_Torch_image_forwards':13}
with(root/'reference_transfer_v1.json').open('x')as f:json.dump(transfer,f,indent=2);f.write('\n')
print(json.dumps(transfer),flush=True)
PY
