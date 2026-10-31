set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
"$ROOT/env/bin/python" - <<'PY'
import importlib.metadata as m,json
out={}
for k in ['ultralytics','torch','torchvision','opencv-python','numpy','polars','scipy','matplotlib','psutil','requests','ultralytics-thop']:
 try:out[k]=m.version(k)
 except m.PackageNotFoundError:out[k]=None
print(json.dumps(out))
PY
curl --proxy http://127.0.0.1:27831 -fL --connect-timeout 10 --max-time 90 --retry 1 -o "$ROOT/models/yolo26n.pt.partial" 'https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt'
test "$(stat -c%s "$ROOT/models/yolo26n.pt.partial")" -gt 5000000
mv -n "$ROOT/models/yolo26n.pt.partial" "$ROOT/models/yolo26n.pt"
sha256sum "$ROOT/models/yolo26n.pt"
mkdir -p "$ROOT/data/opencows2020"
curl --proxy http://127.0.0.1:27831 -fL -C - --connect-timeout 10 --max-time 1200 --retry 2 -o "$ROOT/data/opencows2020/OpenCows2020.zip.partial" 'https://data.bris.ac.uk/datasets/10m32xl88x2b61zlkkgz3fml17/10m32xl88x2b61zlkkgz3fml17.zip' 2> "$ROOT/logs/opencows_download.log"
test "$(stat -c%s "$ROOT/data/opencows2020/OpenCows2020.zip.partial")" -eq 2272138852
mv -n "$ROOT/data/opencows2020/OpenCows2020.zip.partial" "$ROOT/data/opencows2020/OpenCows2020.zip"
printf 'OpenCows2020 full archive staged; hash verification will run under Slurm\n'
