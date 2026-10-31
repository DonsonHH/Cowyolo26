from pathlib import Path
import tarfile,json,hashlib,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=sorted(p for p in (ROOT/'compiler_workspace_v2').rglob('*') if p.is_file())
files.extend(ROOT/r for r in ['protocol/compile_resume_v2.json','tools/resume_compile_v2.py','tools/normalize_graph.py','tools/compile_resume_v2.slurm'])
archive=ROOT/'resume_v2_inputs.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in files:tar.add(file,arcname=file.relative_to(ROOT).as_posix(),recursive=False)
(ROOT/'evidence/resume_v2_input_transfer.json').write_text(json.dumps({'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)},indent=2)+'\n')
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py';subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/pynq_cow_compile_resume_v2_inputs.tar.gz'],check=True)
script=ROOT/'tools/submit_resume_v2_generated.sh';assert not script.exists()
text='''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130531 --format=JobID,State,ExitCode,Elapsed -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029');archive=root.parent/'pynq_cow_compile_resume_v2_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
state=subprocess.check_output(['sacct','-j','130531','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('FAILED|1:0')
assert (root/'results/qualification/cow_allconv_int8.onnx').is_file()
assert not (root/'compiler_workspace_v2').exists() and not (root/'results/qualification_v2').exists()
with tarfile.open(archive) as tar:
    for item in tar.getmembers():
        assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
        target=(root/item.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
protocol=json.loads((root/'protocol/compile_resume_v2.json').read_text())
for r in protocol['workspace_files']:
    p=root/'compiler_workspace_v2'/r['relative_file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
for key,relative in [('normalization_script_sha256','tools/normalize_graph.py'),('resume_script_sha256','tools/resume_compile_v2.py')]:assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==protocol[key]
print('ORIGINAL_FAILED_OUTPUTS_PRESERVED;EXACT_STRUCTURAL_REWRITES_GATE_BEFORE_NEW_COMPILE;NO_RECALIBRATION')
PY
sbatch --parsable pynq_cow_compile_20261029/tools/compile_resume_v2.slurm
'''.replace('DIGEST',sha(archive))
script.write_text(text,newline='\n');subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/resume_v2_submit.txt')],check=True)
