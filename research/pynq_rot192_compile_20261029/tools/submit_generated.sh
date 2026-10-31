set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
id -un
hostname
printf '%s
' "$HOME"
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
project=Path('/share/home/renly/projects/idcoo_research_20261026');root=project/'pynq_rot192_compile_20261029';archive=project/'pynq_rot192_compile_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='55f0ed4796fd5ccd493cb05cca39bc7c3fec6b4c434be959c844db3675b41fdf'
live=subprocess.check_output(['sinfo','-h','-p','cu','-o','%a'],text=True)
assert 'up' in live.split()
assert not root.exists();root.mkdir();(root/'logs').mkdir();(root/'results').mkdir()
with tarfile.open(archive) as tar:
 for item in tar.getmembers():
  assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
  target=(root/item.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
p=json.loads((root/'protocol/compile_v1.json').read_text())
for row in p['workspace_files']:assert hashlib.sha256((root/'compiler_workspace'/row['relative_file']).read_bytes()).hexdigest()==row['sha256']
for key,relative in [('compile_script_sha256','tools/compile_rot192.py'),('normalization_script_sha256','tools/normalize_graph.py')]:assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==p[key]
assert hashlib.sha256(Path(p['source_checkpoint']).read_bytes()).hexdigest()==p['source_checkpoint_sha256']
print('FROZEN_NEW_ROT192_COW_MODEL_AND60_VERIFIED_COMPILER_FILES_STAGED')
PY
sbatch --parsable pynq_rot192_compile_20261029/tools/compile.slurm
