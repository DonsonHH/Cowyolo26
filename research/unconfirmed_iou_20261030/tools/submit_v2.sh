set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130637,130638 -X --format=JobID,State,ExitCode,Elapsed -P
cd /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json,subprocess
for job in ['130637','130638']:
 assert subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('FAILED|1:0')
old=Path('results/control');files=sorted(p for p in old.rglob('*') if p.is_file())
assert len(list(old.glob('*/baseline_trace.json.gz')))==91
manifest=Path('protocol/failed_baselines_preserved.json');assert not manifest.exists()
manifest.write_text(json.dumps([{'file':p.as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],indent=2)+'\n')
a=Path('control_inputs_v2.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='c46efd53a5a2f5e0e6ed4e46e3aa6bab4cf07dc17f3379c6fd075e705ed787f7'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
print('RETAIN91_BASELINES;REPRODUCE_HARDWARE_SAMPLER_ORDER;IDS_EVENTS_STILL_EXACT_REQUIRED')
PY
sbatch --parsable tools/control_v2.slurm
