set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_trigger_pair_20261030
sacct -j 130922,130923 --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2 > logs/verification_sacct_all.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
root=Path.cwd()
state=json.loads((root/'results/reference/summary.json').read_text())
tracker=json.loads((root/'results/tracker_replay/summary.json').read_text())
assert state['status']=='ALL_UNIQUE_TRIGGER_PHOTOS_AND_BOTH30_GALLERIES_TORCH_REFERENCE_AND_FIXED_DECISIONS_PASS'
assert tracker['status']=='ALL4_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES'
assert state['actual_Torch_image_forwards']==89 and tracker['observation_ticks']==8596
assert state['Slurm_job_id']==tracker['Slurm_job_id']=='130923'
assert '130923|cow-trigger-verify|COMPLETED|0:0|'in(root/'logs/verification_sacct_all.txt').read_text()
assert '130922|cow-trigger-verify|FAILED|1:0|'in(root/'logs/verification_sacct_all.txt').read_text()
files=sorted([p for directory in['tools','protocol','reference_input','tracker_input','results','logs']for p in(root/directory).rglob('*')if p.is_file()and'__pycache__'not in p.parts]+[root/'verification_job_id.txt',root/'verification_retry_v2_job_id.txt'])
manifest=root/'result_manifest.json';assert not manifest.exists()
manifest.write_bytes((json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in files],indent=2)+'\n').encode())
archive=root/'verification_delivery_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as tar:
 for p in files+[manifest]:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'archive':str(archive),'bytes':archive.stat().st_size,
                  'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':len(files)+1,
                  'manifest_files':len(files),'completed_job_id':'130923','failed_pre_forward_job_id':'130922'}),flush=True)
PY
