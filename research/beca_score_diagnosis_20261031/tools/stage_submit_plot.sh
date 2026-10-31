set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/beca_score_diagnosis_20261031
test ! -e plot_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,tarfile
r=Path.cwd();p=r/'score_plot_input_v1.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='d46988fbd3c1e66ff081c5da30cb76198ac8baaccaa8decda3a9758a9b0feb15'
with tarfile.open(p)as tar:
 assert len(tar.getmembers())==3
 for member in tar.getmembers():
  rel=PurePosixPath(member.name);assert member.isfile()and not rel.is_absolute()and'..'not in rel.parts
  dest=(r/member.name).resolve();assert dest.is_relative_to(r)and not dest.exists()
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(member).read())
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/plot.slurm)
printf '%s\n' "$job_id" > plot_job_id.txt
printf 'BECA_SCORE_PLOT_JOB_ID=%s\n' "$job_id"
