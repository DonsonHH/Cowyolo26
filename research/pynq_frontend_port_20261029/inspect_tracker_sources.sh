set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
import json,inspect,importlib,importlib.metadata,hashlib
import ultralytics
assert ultralytics.__version__=='8.4.63'
names=['ultralytics.trackers.byte_tracker','ultralytics.trackers.basetrack','ultralytics.trackers.utils.matching','ultralytics.trackers.utils.kalman_filter']
records=[]
for name in names:
    m=importlib.import_module(name);path=inspect.getsourcefile(m);text=open(path).read()
    records.append({'module':name,'path':path,'sha256':hashlib.sha256(text.encode()).hexdigest(),'source_text':text})
from ultralytics.utils.metrics import bbox_ioa
from ultralytics.utils.ops import xywh2ltwh,xyxy2xywh
for func in [bbox_ioa,xywh2ltwh,xyxy2xywh]:
    text=inspect.getsource(func);records.append({'function':func.__name__,'sha256':hashlib.sha256(text.encode()).hexdigest(),'source_text':text})
print(json.dumps({'status':'INSTALLED_FROZEN_BYTETRACK_USED_SOURCE_CAPTURE_READONLY','ultralytics':ultralytics.__version__,
  'lap_version':importlib.metadata.version('lap'),'scipy_version':importlib.metadata.version('scipy'),'sources':records,'model_or_hardware_forwards':0}))
PY
