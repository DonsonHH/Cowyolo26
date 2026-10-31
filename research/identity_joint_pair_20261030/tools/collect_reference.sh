set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_joint_pair_20261030
sacct -j 130870 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P > logs/sacct-130870.txt
grep -q '130870|cow-id-joint-ref|COMPLETED|0:0|' logs/sacct-130870.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
r=Path.cwd();s=json.loads((r/'results/cpu_reference/summary.json').read_text());assert s['status']=='ALL40_FIXED_AUG19_GALLERY_AND_ACTUAL_PHOTO_TORCH_NCNN_REFERENCE_PASS'
assert s['Torch_image_forwards']==s['NCNN_image_forwards']==40
files=sorted([p for d in['results','logs','protocol']for p in(r/d).rglob('*')if p.is_file()]+[r/'reference_job_id.txt'])
manifest=[{'file':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in files]
p=r/'result_manifest.json';assert not p.exists();p.write_text(json.dumps(manifest,indent=2)+'\n');files.append(p)
a=r/'cpu_reference_delivery_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz')as tar:
 for p in files:tar.add(p,arcname=p.relative_to(r).as_posix(),recursive=False)
print(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'archive':str(a),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'members':len(files),'manifest_files':len(manifest),'new_training_updates':0}))
PY
