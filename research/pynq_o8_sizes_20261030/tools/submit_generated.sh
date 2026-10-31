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
import tarfile,json,hashlib
root=Path('pynq_o8_sizes_20261030');archive=Path('pynq_o8_sizes_20261030_inputs.tar.gz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='0ee152d9e54a19cca3fafefeb5efcceb71174f0d78dbd3c9cf7976a2be2d6ea9' and not root.exists()
root.mkdir();(root/'logs').mkdir()
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
for name in ['s256','s320']:
 p=json.loads((root/name/'protocol/compile_v1.json').read_text());assert hashlib.sha256(Path(p['source_checkpoint']).read_bytes()).hexdigest()==p['source_checkpoint_sha256']
 for row in p['workspace_files']:assert hashlib.sha256((root/name/'compiler_workspace'/row['relative_file']).read_bytes()).hexdigest()==row['sha256']
 (root/name/'results').mkdir();(root/name/'logs').mkdir()
print('TWO_FIXED_COW_SIZES_AND_ALL_O8_COMPILER_FILES_FROZEN')
PY
sbatch --parsable pynq_o8_sizes_20261030/tools/compile.slurm
