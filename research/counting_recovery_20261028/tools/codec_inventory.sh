set -euo pipefail
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
import importlib.util,json
print(json.dumps({m:bool(importlib.util.find_spec(m)) for m in ['av','imageio_ffmpeg','imageio','torchcodec']}))
PY
module -t avail ffmpeg 2>&1 || true
test ! -d /share/apps || find /share/apps -maxdepth 3 -name ffmpeg -type f 2>/dev/null
