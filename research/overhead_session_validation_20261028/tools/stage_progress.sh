set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
"$PROJECT/env/bin/python" - <<'PY'
from pathlib import Path
import json
p=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_session_validation_20261028')
print(json.dumps({'files':[{'path':f.relative_to(p).as_posix(),'bytes':f.stat().st_size} for f in sorted((p/'data').rglob('*')) if f.is_file()],
                  'manifest_exists':(p/'evidence/fetch_manifest.json').exists(),
                  'font_exists':Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf').is_file(),
                  'prepared_labels_exists':(p.parent/'cows2021_adaptation_20261027/results/labels_v1/prepared_image_label_manifest.json').exists()}))
PY
