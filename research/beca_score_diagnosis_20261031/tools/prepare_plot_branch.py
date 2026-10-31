from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
remote="/share/home/renly/projects/idcoo_research_20261026/beca_score_diagnosis_20261031"
batch=f"""#!/bin/bash
#SBATCH --job-name=cow-beca-score-plot
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:03:00
#SBATCH --output={remote}/logs/plot-%j.out
#SBATCH --error={remote}/logs/plot-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR={remote}/mplconfig
cd {remote}
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/plot_states.py
"""
slurm=ROOT/"tools/plot.slurm";assert not slurm.exists();slurm.write_text(batch,encoding="utf-8")
files=[ROOT/"tools/plot_states.py",slurm,ROOT/"results/score_diagnosis_v1.json"]
archive=ROOT/"score_plot_input_v1.tar.gz";assert not archive.exists()
with tarfile.open(archive,"w:gz")as tar:
    for p in files:tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
sha=hashlib.sha256(archive.read_bytes()).hexdigest()
script=f"""set -euo pipefail
cd {remote}
test ! -e plot_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,tarfile
r=Path.cwd();p=r/'score_plot_input_v1.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='{sha}'
with tarfile.open(p)as tar:
 assert len(tar.getmembers())==3
 for member in tar.getmembers():
  rel=PurePosixPath(member.name);assert member.isfile()and not rel.is_absolute()and'..'not in rel.parts
  dest=(r/member.name).resolve();assert dest.is_relative_to(r)and not dest.exists()
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(member).read())
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/plot.slurm)
printf '%s\\n' "$job_id" > plot_job_id.txt
printf 'BECA_SCORE_PLOT_JOB_ID=%s\\n' "$job_id"
"""
path=ROOT/"tools/stage_submit_plot.sh";assert not path.exists();path.write_text(script,encoding="utf-8")
path=ROOT/"tools/create_server_directory.sh";assert not path.exists()
path.write_text(f"set -euo pipefail\ntest ! -e {remote}\nmkdir {remote}\nmkdir {remote}/logs\n",encoding="utf-8")
out=ROOT/"results/plot_input_bundle.json";assert not out.exists()
out.write_text(json.dumps({"created_UTC":datetime.now(timezone.utc).isoformat(),"bytes":archive.stat().st_size,"sha256":sha,
                           "members":3,"new_model_forwards":0},indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"bytes":archive.stat().st_size,"sha256":sha,"members":3}))
