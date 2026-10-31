set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_joint_pair_20261030
sacct -j 130876 --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2 > logs/sacct-130876.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
r=Path.cwd();s=json.loads((r/'results/tracker_replay/summary.json').read_text());assert s['status']=='ALL4_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES';assert s['observation_ticks']==8696 and s['new_model_forwards']==0
files=sorted([p for p in(r/'results/tracker_replay').rglob('*')if p.is_file()]+[p for p in(r/'logs').glob('*130876*')]+[r/'tracker_input/protocol.json',r/'tools/replay_tracker.py',r/'tools/tracker_replay.slurm',r/'tracker_job_id.txt'])
rows=[{'file':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in files];m=r/'tracker_result_manifest.json';assert not m.exists();m.write_text(json.dumps(rows,indent=2)+'\n');a=r/'tracker_delivery_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz')as tar:
 for p in files:tar.add(p,arcname=p.relative_to(r).as_posix(),recursive=False)
 tar.add(m,arcname='result_manifest.json',recursive=False)
print(json.dumps({'archive':str(a),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'members':len(files)+1,'manifest_files':len(files),'new_model_forwards':0}))
PY
