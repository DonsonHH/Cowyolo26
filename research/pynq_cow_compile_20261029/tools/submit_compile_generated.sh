set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
command -v g++
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,importlib.util
root=Path('/share/home/renly/projects/idcoo_research_20261026');archive=root/'pynq_cow_compile_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='2c85bc8601295187e2b801773548cd2e8827944672510ebaf6fae025ca86dab6'
out=root/'pynq_cow_compile_20261029';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    for item in tar.getmembers():
        assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
        target=(out/item.name).resolve();assert target.is_relative_to(out.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
for row in json.loads((out/'staging_manifest.json').read_text()):
    p=out/row['relative_file'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
for module in ['torch','onnx','onnxruntime','onnxslim','cv2']:assert importlib.util.find_spec(module),module
(out/'logs').mkdir(exist_ok=False)
print('SOURCE_SNAPSHOT_HASHES_EXACT_CPU_ONLY_COMPILATION_GATE;NO_BOARD_ACTION')
PY
sbatch --parsable pynq_cow_compile_20261029/tools/compile.slurm
