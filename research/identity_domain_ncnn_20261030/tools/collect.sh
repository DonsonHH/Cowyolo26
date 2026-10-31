set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_ncnn_20261030
sacct -j 130863 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P > logs/sacct-130863.txt
grep -q '130863|cow-new-id-ncnn|COMPLETED|0:0|' logs/sacct-130863.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
r=Path.cwd();s=json.loads((r/'results/export/summary.json').read_text());assert s['status']=='NEW_DOMAIN_ENCODER_FP32_NCNN630_IMAGE_PARITY_AND1260_DEVELOPMENT_DECISIONS_PASS'
assert s['measured_Torch_image_forwards']==s['measured_NCNN_image_forwards']==630
files=sorted([p for d in['results','logs','protocol']for p in(r/d).rglob('*')if p.is_file()]+[r/'export_job_id.txt'])
manifest=[{'file':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in files]
p=r/'result_manifest.json';assert not p.exists();p.write_text(json.dumps(manifest,indent=2)+'\n');files.append(p)
a=r/'new_encoder_ncnn_delivery_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz')as tar:
 for p in files:tar.add(p,arcname=p.relative_to(r).as_posix(),recursive=False)
print(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'archive':str(a),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'members':len(files),'manifest_files':len(manifest),'source_NCNN_param_bin_included':True}))
PY
