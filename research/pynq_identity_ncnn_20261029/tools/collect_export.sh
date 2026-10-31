set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130569,130572 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('pynq_identity_ncnn_20261029').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=subprocess.check_output(['sacct','-j','130572','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0')
s=json.loads((root/'results/export_v2/summary.json').read_text());assert s['real_image_forwards']=={'TorchCPU':132,'ncnnCPU':132} and s['all_retrieval_decisions_exact']
files=[p for folder in ['results','protocol','logs','tools','input'] for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
manifest=root/'export_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=root.parent/'pynq_identity_ncnn_20261029_export.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files+[manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
r={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
(root.parent/'pynq_identity_ncnn_20261029_export_transfer.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
