set -euo pipefail
id -un
hostname
printenv HOME
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from importlib.util import find_spec
from importlib.metadata import version,PackageNotFoundError
import json,sys
result={}
for name in ['numpy','protobuf','ml_dtypes','flatbuffers','onnx','onnxruntime','sympy','packaging']:
    try:result[name]=version(name)
    except PackageNotFoundError:result[name]=None
print(json.dumps({'python':sys.version,'packages':result}))
PY
sed -n '/def export_onnx/,/def export_openvino/p' /share/home/renly/projects/idcoo_research_20261026/env/lib/python3.13/site-packages/ultralytics/engine/exporter.py | head -n 110
