set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
import json,inspect,PIL
from PIL import ImageOps
print(json.dumps({'Pillow':PIL.__version__,'pad_source':inspect.getsource(ImageOps.pad),'contain_source':inspect.getsource(ImageOps.contain)}))
PY
