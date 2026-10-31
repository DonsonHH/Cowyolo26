set -euo pipefail
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
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='c03871b7072b996f6e3a10a9b2ac96b004f6a08c85edffc6c80ebde050a873cd'
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
