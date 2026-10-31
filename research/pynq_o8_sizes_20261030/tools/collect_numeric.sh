set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130606,130609,130610 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('pynq_o8_sizes_20261030').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=subprocess.check_output(['sacct','-j','130610','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0')
s=json.loads((root/'results/ordered_reference/summary.json').read_text());assert s['all24_ordered_raw_bytes_exact']
files=[p for folder in ['results/probe320','results/probe320_causal','results/ordered_reference'] for p in sorted((root/folder).rglob('*')) if p.is_file()]
files.extend(root/r for r in ['protocol/ordered_float_reference_v2.json','tools/ordered_float_reference.py','tools/ordered_hybrid_executor.py','tools/check_ordered_reference.py','tools/probe320.py','tools/probe320_causal.py',
 'logs/probe-130606.out','logs/probe-130606.err','logs/causal-130609.out','logs/causal-130609.err','logs/ordered-130610.out','logs/ordered-130610.err'])
manifest=root/'numeric_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],indent=2)+'\n')
archive=root.parent/'pynq_o8_sizes_20261030_numeric.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files+[manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
r={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
(root.parent/'pynq_o8_sizes_20261030_numeric_transfer.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
