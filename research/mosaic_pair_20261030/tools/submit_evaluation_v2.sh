set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
assert subprocess.check_output(['sacct','-j','130628','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('FAILED|1:0')
assert subprocess.check_output(['sacct','-j','130629','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('COMPLETED|0:0')
assert hashlib.sha256(Path('results/all_six_checkpoints_frozen.json').read_bytes()).hexdigest()=='a591fdc3522eb0b94140f0aaab90de552b6d7bc2f1ab34dc3960d8d502beb793'
assert not list(Path('results/evaluation').rglob('*')) and not Path('results/evaluation_v2').exists()
a=Path('evaluation_inputs_v2.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='71f402916b3434d55305a804ce2939166d95e7dea0e2008b5260f595f5ddb355'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
print('STRICT_EQUALITY_RETAINED;ONLY_MISSING_METADATA_KEY_REPAIRED;SIX_WEIGHTS_UNCHANGED')
PY
sbatch --parsable tools/evaluate_v2.slurm
