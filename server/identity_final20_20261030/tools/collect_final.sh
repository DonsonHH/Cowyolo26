set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030
job_id=$(cat evaluation_job_id.txt)
sacct -j "$job_id" --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2 > "logs/sacct-${job_id}.txt"
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
r=Path.cwd();s=json.loads((r/'results/evaluation/summary.json').read_text());assert s['status']=='BOTH_FROZEN_ENCODERS90_FINAL_ID_IMAGES180_FORWARDS8_FIXED_POLICIES_AND20_PAIRED_ID_CONTRASTS_COMPLETE'
assert s['actual_model_image_forwards']==180 and s['actual_network_calls']==16
job=(r/'evaluation_job_id.txt').read_text().strip();assert('|COMPLETED|0:0|')in(r/'logs'/('sacct-'+job+'.txt')).read_text()
files=sorted([p for name in['input','protocol','results','evidence','tools','logs']for p in(r/name).rglob('*')if p.is_file()and'__pycache__'not in p.parts]+[r/'evaluation_job_id.txt'])
rows=[{'file':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in files];manifest=r/'result_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps(rows,indent=2)+'\n')
archive=r/'final20_delivery_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as tar:
 for p in files+[manifest]:tar.add(p,arcname=p.relative_to(r).as_posix(),recursive=False)
print(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':len(files)+1,'manifest_files':len(files),'all90_original_JPEGs_included':True}))
PY
