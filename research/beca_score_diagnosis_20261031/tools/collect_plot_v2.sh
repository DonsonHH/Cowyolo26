set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/beca_score_diagnosis_20261031
job_id=$(cat plot_v2_job_id.txt)
squeue -j "$job_id" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sacct -j "$job_id" --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2 > "logs/sacct-$job_id.txt"
cat "logs/sacct-$job_id.txt"
tail -n 8 "logs/plot-$job_id.out"
tail -n 16 "logs/plot-$job_id.err"
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
r=Path.cwd();job=(r/'plot_v2_job_id.txt').read_text().strip()
assert '|COMPLETED|0:0|'in(r/'logs'/('sacct-'+job+'.txt')).read_text()
assert (r/'logs'/('plot-'+job+'.err')).stat().st_size==0
assert (r/'results/figures_v2/threshold_score_overlap.png').is_file()
files=sorted([p for folder in['tools','results','logs']for p in(r/folder).rglob('*')if p.is_file()]+[r/'plot_v2_job_id.txt'])
manifest=r/'plot_v2_manifest.json';assert not manifest.exists()
manifest.write_text(json.dumps([{'file':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in files],indent=2)+'\n')
archive=r/'score_plot_delivery_v2.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as tar:
 for p in files+[manifest]:tar.add(p,arcname=p.relative_to(r).as_posix(),recursive=False)
print(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'archive':str(archive),'bytes':archive.stat().st_size,
                  'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':len(files)+1}))
PY
