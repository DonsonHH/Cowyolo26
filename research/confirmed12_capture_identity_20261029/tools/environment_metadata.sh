set -euo pipefail
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
import importlib.metadata as metadata,sys,json,platform
print(json.dumps({'python':sys.version,'platform':platform.platform(),
 'packages':{name:metadata.version(name) for name in ['torch','torchvision','opencv-python','numpy','Pillow']},
 'scope':'Read-only current environment metadata after functional replay; no benchmark or model forward.'},indent=2))
PY
