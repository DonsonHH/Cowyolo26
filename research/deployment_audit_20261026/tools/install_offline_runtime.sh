set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/deployment_audit
mkdir -p "$ROOT/results"
test ! -e "$ROOT/wheelhouse"
test ! -e "$ROOT/dependencies_offline"
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/deployment_audit')
bundle=root/'export_wheels.tar';record=json.loads((root/'export_wheels_record.json').read_text())
assert bundle.stat().st_size==record['bytes'] and hashlib.sha256(bundle.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(bundle) as archive:archive.extractall(root,filter='data')
rows=json.loads((root/'wheelhouse/pypi_manifest.json').read_text())
for row in rows:
    path=root/'wheelhouse'/row['filename']
    assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
print('Transferred official wheel bundle hashes verified',len(rows))
PY
/share/home/renly/projects/idcoo_research_20261026/env/bin/python -m pip --isolated --disable-pip-version-check --no-input install --no-index --find-links "$ROOT/wheelhouse" --target "$ROOT/dependencies_offline" onnx==1.19.0 onnxruntime==1.23.2 numpy==2.2.6
PYTHONPATH="$ROOT/dependencies_offline" /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from importlib.metadata import version
import os,signal,json,onnx,onnxruntime,numpy,time
root=Path('/share/home/renly/projects/idcoo_research_20261026/deployment_audit')
assert (onnx.__version__,onnxruntime.__version__,numpy.__version__)==('1.19.0','1.23.2','2.2.6')
record={'status':'OFFLINE_TARGET_IMPORT_PASS','dependencies_path':str(root/'dependencies_offline'),'versions':{name:version(name) for name in ['onnx','onnxruntime','numpy','protobuf','ml_dtypes','flatbuffers','packaging','sympy','typing_extensions']}}
# End only the now-unneeded task download helper after an equivalent runtime
# has been prepared successfully. It has no Slurm allocation and no results.
pid=int((root/'logs/runtime_stage_pid.txt').read_text());proc=Path('/proc')/str(pid)
record['original_slow_download_pid']=pid;record['original_helper_terminated']=False
if proc.exists():
    assert proc.stat().st_uid==os.getuid()
    cmd=(proc/'cmdline').read_bytes().split(b'\0')
    assert str(root/'dependencies').encode() in cmd and b'pip' in cmd
    os.kill(pid,signal.SIGTERM);record['original_helper_terminated']=True
(root/'results/runtime_ready.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
PY
