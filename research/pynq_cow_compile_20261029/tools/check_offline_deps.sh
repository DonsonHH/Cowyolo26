set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026
PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline env/bin/python - <<'PY'
import sys,json,importlib.util
print(json.dumps({'python':sys.executable,'offline_modules':{name:bool(importlib.util.find_spec(name)) for name in ['torch','ultralytics','onnx','onnxruntime','onnxslim','cv2']}}))
from ultralytics.engine.exporter import Exporter
import inspect
text=inspect.getsource(Exporter.export_onnx)
for line in text.splitlines():
    if any(w in line for w in ['onnxslim','check_requirements','opset','simplif']):print(line)
from pathlib import Path
root=Path('deployment_audit/wheelhouse');print('OFFLINE_WHEELS',[p.name for p in root.glob('*onnx*')])
PY
g++ --version | head -n1
