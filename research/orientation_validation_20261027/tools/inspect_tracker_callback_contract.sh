set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
import inspect,json,hashlib
from pathlib import Path
from ultralytics.engine.model import Model
from ultralytics.engine.results import Results
from ultralytics.trackers.track import register_tracker,on_predict_postprocess_end
rows=[]
for obj in [Model.track,register_tracker,on_predict_postprocess_end,Results.__init__]:
    source=inspect.getsource(obj)
    p=Path(inspect.getfile(obj))
    rows.append({'object':obj.__qualname__,'module_path':str(p),'module_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':source})
print(json.dumps(rows),flush=True)
PY
