set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('detector_factorial_20261029');baseline=Path('cows2021_adaptation_20261027/results/training')
rows=[]
for file in sorted((root/'results/training').glob('*/optimizer_step_batch_indices.json')):
    seed=int(file.parent.name.split('seed')[-1]);reference=baseline/('seed'+str(seed))/'optimizer_step_batch_indices.json'
    a=json.loads(file.read_text());b=json.loads(reference.read_text());different=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    rows.append({'condition':file.parent.name,'new_steps':len(a),'reference_steps':len(b),'parsed_schedules_equal':a==b,
       'different_indices_count':len(different),'first_difference':different[:3],'new_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
       'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'new_tail_bytes':repr(file.read_bytes()[-15:]),
       'reference_tail_bytes':repr(reference.read_bytes()[-15:]),'last_checkpoint_exists':(file.parent/'weights/last.pt').is_file()})
print(json.dumps({'status':'READONLY_SCHEDULE_HASH_DIAGNOSIS','conditions':rows}))
PY
