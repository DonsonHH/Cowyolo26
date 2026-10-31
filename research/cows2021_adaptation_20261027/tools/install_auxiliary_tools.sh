set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
project=Path('/share/home/renly/projects/idcoo_research_20261026')
root=project/'cows2021_adaptation_20261027'
archive=project/'cows2021_adaptation_20261027.auxiliary_tools_v1.tar.gz'
assert archive.stat().st_size==7092
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='70f1cfad9e57be12eaa508ff483842698d95198dbca90a062cbae3a1d7639b5d'
with tarfile.open(archive) as tf:
    for member in tf:
        p=root/member.name
        assert member.isfile() and p.resolve().is_relative_to(root) and not p.exists()
    tf.extractall(root,filter='data')
records=json.loads((root/'results/auxiliary_tools_v1.json').read_text())
for row in records:
    path=root/row['path']
    assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    if path.suffix=='.py':compile(path.read_text(),str(path),'exec')
print(json.dumps({'auxiliary_tools':len(records),'hashes_and_Python_syntax_verified':True,'submitted_jobs':0}))
PY
ps -p 2794954 -o pid,lstart,etime,state,args
test ! -f "$stage/results/download_attempt_01/progress.json" || cat "$stage/results/download_attempt_01/progress.json"
