set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
find /share/home/renly/projects/idcoo_research_20261026 -maxdepth 3 -name pyvenv.cfg -type f -print
for candidate in /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/miniconda3/envs/pid310_gpu/bin/python; do
    if [ -x "$candidate" ]; then "$candidate" - <<'PY'
import sys,importlib.util,json
print(json.dumps({'python':sys.executable,'version':sys.version.split()[0],
 'modules':{name:bool(importlib.util.find_spec(name)) for name in ['torch','ultralytics','onnx','onnxruntime','onnxslim','cv2']}}))
PY
    fi
done
