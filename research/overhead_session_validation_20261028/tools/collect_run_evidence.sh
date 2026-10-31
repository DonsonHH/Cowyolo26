set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/overhead_session_validation_20261028"
"$PROJECT/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,sys,platform
import torch,ultralytics,cv2,numpy,PIL
root=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_session_validation_20261028')
package=Path(ultralytics.__path__[0]);items=[]
for name in ['trackers/byte_tracker.py','trackers/track.py','trackers/utils/matching.py','cfg/trackers/bytetrack.yaml']:
    p=package/name;b=p.read_bytes();items.append({'relative_path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
result={'status':'POST_RUN_ENVIRONMENT_AND_INSTALLED_TRACKER_SOURCES_READ_ONLY_CAPTURED',
        'python':sys.version,'platform':platform.platform(),'torch':torch.__version__,'ultralytics':ultralytics.__version__,
        'cv2':cv2.__version__,'numpy':numpy.__version__,'PIL':PIL.__version__,'installed_files':items,
        'time_scope':'Read after completed jobs; compare hashes to prior captured sources, not a new pre-run freeze.',
        'no_new_model_forward_or_decode':True}
print(json.dumps(result))
PY
sacct -j 130304,130305 --format=JobID,JobName%22,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS,AllocTRES%80
