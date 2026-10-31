set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
id -un
hostname
printf '%s\n' "$HOME"
sinfo -o 'PARTITION|AVAIL|TIMELIMIT|NODES|STATE|NODELIST|GRES'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130559,130563,130564 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
import inspect,importlib,json,hashlib
from pathlib import Path
parts=[]
for name in ['ultralytics.trackers.utils.stracks','ultralytics.trackers.utils.matching','ultralytics.trackers.utils.kalman_filter']:
 m=importlib.import_module(name);p=Path(inspect.getsourcefile(m));s=p.read_text()
 parts.append({'module':name,'path':str(p),'source_text':s,'sha256':hashlib.sha256(s.encode()).hexdigest()})
import ultralytics
p=Path(ultralytics.__file__).parent/'cfg/trackers/bytetrack.yaml';s=p.read_text()
parts.append({'config':str(p),'source_text':s,'sha256':hashlib.sha256(s.encode()).hexdigest()})
print('SOURCE_JSON_BEGIN')
print(json.dumps({'status':'ADDITIONAL_FROZEN_TRACKER_DEPENDENCIES','sources':parts,'network_or_hardware_forwards':0}))
print('SOURCE_JSON_END')
PY
