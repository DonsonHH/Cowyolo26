set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130531,130539 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('pynq_cow_compile_20261029').resolve();q=root/'results/qualification_v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=subprocess.check_output(['sacct','-j','130539','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0')
s=json.loads((q/'summary.json').read_text());assert s['all_native_CPU_parity_gates_pass'] and s['maximum_box_parity_error']==s['maximum_score_parity_error']==0
files=[p for folder in ['results','protocol','logs','tools'] for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
files.extend([root/'runtime_staging.json',root/'compiler_workspace_v2/native_sources/native_queue_linux.so'])
manifest=root/'qualification_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'relative_file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=root.parent/'pynq_cow_compile_20261029_qualification.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in [*files,manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
record={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
file=root.parent/'pynq_cow_compile_20261029_qualification_transfer.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
