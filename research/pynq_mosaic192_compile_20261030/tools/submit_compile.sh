set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json
a=Path('pynq_mosaic192_compile_20261030_compile_inputs_v1.tar.gz');root=Path('pynq_mosaic192_compile_20261030');assert not root.exists() and hashlib.sha256(a.read_bytes()).hexdigest()=='0b5fe0641bf596c8f8bd16a650bbddfa6356158bb3223bfa0f014bc42738cdf3'
root.mkdir()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
for name in ['results','logs','evidence']:(root/name).mkdir(exist_ok=True)
p=json.loads((root/'protocol/compile_v1.json').read_text())
for r in p['workspace_files']:assert hashlib.sha256((root/'compiler_workspace'/r['relative_file']).read_bytes()).hexdigest()==r['sha256']
assert hashlib.sha256(Path(p['source_checkpoint']).read_bytes()).hexdigest()==p['source_checkpoint_sha256']
print('SAME60_COMPILER_FILES128_TRAIN_INPUTS_ORDERED_PRIMARY_AND_LEGACY_REFERENCE_FROZEN')
PY
sbatch --parsable pynq_mosaic192_compile_20261030/tools/compile.slurm
