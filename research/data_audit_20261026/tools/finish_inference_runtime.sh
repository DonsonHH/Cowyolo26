set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
python - <<'PY'
import os,signal,pathlib,time
p=pathlib.Path('/proc/4159233/cmdline')
if p.exists():
 data=p.read_bytes()
 if b'/projects/idcoo_research_20261026/env/bin/python\x00-m\x00pip\x00install' not in data:raise SystemExit('Unexpected process; refusing to interrupt')
 os.kill(4159233,signal.SIGTERM)
 for _ in range(30):
  if not p.exists():break
  time.sleep(.2)
 if p.exists():raise SystemExit('Installer still active; no concurrent mutation')
 print('Stopped own optional-dependency download before installation; log retained')
PY
"$ROOT/env/bin/python" -m pip install --disable-pip-version-check --no-input --no-deps 'matplotlib==3.11.2' 'lap==0.5.13' contourpy cycler fonttools kiwisolver pyparsing > "$ROOT/logs/install_inference_only.log" 2>&1
"$ROOT/env/bin/python" - <<'PY'
import importlib.util,importlib.metadata as m,json
packages=['ultralytics','matplotlib','lap','torch','cv2','numpy','scipy','psutil','requests','yaml','PIL']
print(json.dumps({k:bool(importlib.util.find_spec(k)) for k in packages}))
PY
"$ROOT/env/bin/python" -m pip freeze > "$ROOT/logs/runtime_inference_freeze.txt"
