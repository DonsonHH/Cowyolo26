set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026
mkdir -p pynq_cow_compile_20261029/wheelhouse
env/bin/python -m pip --isolated --disable-pip-version-check --no-input download --index-url https://pypi.org/simple --only-binary=:all: --no-deps --dest pynq_cow_compile_20261029/wheelhouse onnxslim==0.1.71
env/bin/python -m pip --isolated --disable-pip-version-check --no-input install --no-index --find-links pynq_cow_compile_20261029/wheelhouse --no-deps --target pynq_cow_compile_20261029/dependencies onnxslim==0.1.71
PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/dependencies:/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline env/bin/python - <<'PY'
import importlib.metadata,json,hashlib
from pathlib import Path
import onnx,onnxruntime,onnxslim,numpy
root=Path('pynq_cow_compile_20261029');p=root/'runtime_staging.json';assert not p.exists()
record={'status':'OWN_COMPILE_ONNXSLIM_TARGET_AND_PREEXISTING_OFFLINE_ONNX_IMPORTS_PASS',
 'versions':{name:importlib.metadata.version(name) for name in ['onnx','onnxruntime','onnxslim','numpy','torch','ultralytics']},
 'module_files':{module.__name__:module.__file__ for module in [onnx,onnxruntime,onnxslim,numpy]},
 'new_wheels':[{'file':w.name,'bytes':w.stat().st_size,'sha256':hashlib.sha256(w.read_bytes()).hexdigest()} for w in (root/'wheelhouse').glob('*.whl')],
 'active_training_environment_modified':False}
p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
