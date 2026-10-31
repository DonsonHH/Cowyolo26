set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
mkdir -p "$ROOT/yolo_settings"
"$ROOT/env/bin/python" -m pip install --disable-pip-version-check --no-input 'ultralytics==8.4.63' 'lap>=0.5.12' > "$ROOT/logs/install_runtime_dependencies.log" 2>&1
"$ROOT/env/bin/python" -m pip check > "$ROOT/logs/runtime_pip_check.txt" || true
"$ROOT/env/bin/python" -m pip freeze > "$ROOT/logs/runtime_freeze.txt"
"$ROOT/env/bin/python" - <<'PY'
import importlib.util,json
print(json.dumps({k:bool(importlib.util.find_spec(k)) for k in ['ultralytics','matplotlib','polars','lap','cv2','torch']}))
PY
