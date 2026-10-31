set -e
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
scontrol show node gpu02 -o
find /share/home/renly/miniconda3/envs /share/home/renly/.venvs /share/home/renly/.local/venvs -maxdepth 1 -type d 2>/dev/null || true
python - <<'PY'
import importlib.metadata as m, importlib.util, json
names=['torch','torchvision','opencv-python','numpy','pillow','imageio','imageio-ffmpeg','ultralytics','scipy','onnxruntime']
versions={}
for n in names:
 try:versions[n]=m.version(n)
 except m.PackageNotFoundError:versions[n]=None
print(json.dumps(versions))
PY
python /share/home/renly/projects/idcoo_research_20261026/tools/stage_catalog.py
