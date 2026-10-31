set -euo pipefail
sacct -j 130634 -X --format=JobID,State,ExitCode,Elapsed,AllocCPUS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
root=Path('pynq_mosaic192_compile_20261030')
state=subprocess.check_output(['sacct','-j','130634','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0'),state
s=json.loads((root/'results/qualification/summary.json').read_text())
assert s['all_native_CPU_parity_gates_pass'] and s['primary_ordered_vectors_byte_exact']==s['legacy_numpy_vectors_byte_exact']==8
files=[p for name in ['results','tools','protocol','reference','input','logs'] for p in sorted((root/name).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
files.append(root/'compiler_workspace/native_sources/native_queue_linux.so')
manifest=root/'qualification_manifest.json';assert not manifest.exists()
manifest.write_text(json.dumps([{'relative_file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],indent=2)+'\n')
a=root/'qualification_delivery_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 for p in [*files,manifest]:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'archive':str(a.resolve()),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'members':len(files)+1,'manifest_files':len(files)}))
PY
