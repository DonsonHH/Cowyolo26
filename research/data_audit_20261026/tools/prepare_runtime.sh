set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
mkdir -p "$ROOT/logs" "$ROOT/models"
python -m venv --system-site-packages "$ROOT/env"
"$ROOT/env/bin/python" -m pip install --no-deps ultralytics==8.4.63 ultralytics-thop==2.0.18 > "$ROOT/logs/install_runtime.log" 2>&1
"$ROOT/env/bin/python" - <<'PY'
import importlib.util,importlib.metadata as m,json
print(json.dumps({k:(m.version(k) if importlib.util.find_spec(k.replace('-','_')) else None) for k in ('ultralytics','torch','torchvision','cv2','numpy','polars','scipy','matplotlib','psutil','requests')}))
PY
curl --noproxy '*' -fL --connect-timeout 10 --max-time 45 -o "$ROOT/models/yolo26n.pt.partial" 'https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt'
test "$(stat -c%s "$ROOT/models/yolo26n.pt.partial")" -gt 5000000
mv -n "$ROOT/models/yolo26n.pt.partial" "$ROOT/models/yolo26n.pt"
sha256sum "$ROOT/models/yolo26n.pt"
