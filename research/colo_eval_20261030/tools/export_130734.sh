set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/colo_eval_20261030
sacct -j 130734 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P > logs/sacct-130734.txt
grep -q '130734|cow-colo-fixed9|COMPLETED|0:0|' logs/sacct-130734.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
root=Path.cwd();summary=json.loads((root/'results/evaluation/summary.json').read_text());assert summary['actual_source_image_forwards']==450 and summary['actual_network_forward_calls']==45
assert summary['Slurm_job_id']=='130734' and len(summary['metrics'])==72
paths=sorted([p for directory in ['results','logs','protocol'] for p in (root/directory).rglob('*') if p.is_file()]+[root/'submission.json',root/'submitted_job_id.txt'])
for p in paths:assert not p.is_symlink() and p.is_relative_to(root)
manifest=[{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
f=root/'result_manifest.json';assert not f.exists();f.write_text(json.dumps(manifest,indent=2)+'\n');paths.append(f)
archive=root/'colo_delivery_130734.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for p in paths:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':len(paths),'manifest_files':len(manifest),'job_completed_0_0':True}))
PY
