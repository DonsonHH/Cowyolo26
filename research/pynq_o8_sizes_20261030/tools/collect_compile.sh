set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130593 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('pynq_o8_sizes_20261030').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for size in [256,320]:
 s=json.loads((root/('s'+str(size))/'results/qualification/summary.json').read_text());assert len(s['CPU_integer_parity_vectors'])==8
 assert s['all_native_CPU_parity_gates_pass']==(size==256)
files=[p for name in ['s256/results','s320/results','s256/protocol','s320/protocol','logs','protocol'] for p in sorted((root/name).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
for case in ['s256','s320']:
 files.extend([root/case/'tools/compile_fixed_size.py',root/case/'tools/normalize_graph.py',root/case/'compiler_workspace/native_sources/native_queue_linux.so'])
manifest=root/'compile_result_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=root.parent/'pynq_o8_sizes_20261030_compile.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files+[manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
r={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
(root.parent/'pynq_o8_sizes_20261030_compile_transfer.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
