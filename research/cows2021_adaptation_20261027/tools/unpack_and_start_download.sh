set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
test ! -e "$stage"
test -s "$project/cows2021_adaptation_20261027.staging_metadata.tar.gz"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess,sys,os
project=Path('/share/home/renly/projects/idcoo_research_20261026')
archive=project/'cows2021_adaptation_20261027.staging_metadata.tar.gz'
assert archive.stat().st_size==5756386
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='0b7b8f4a356f5a31ff28ca1505a86840742ed4219683164fc67b44403cde02fd'
stage=project/'cows2021_adaptation_20261027'
stage.mkdir(exist_ok=False)
with tarfile.open(archive) as tf:
    for member in tf:
        assert member.isfile() and (stage/member.name).resolve().is_relative_to(stage)
    tf.extractall(stage,filter='data')
entries=json.loads((stage/'input/staging_file_hashes.json').read_text())
for row in entries:
    p=stage/row['path'];assert p.is_file() and p.stat().st_size==row['bytes']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
assert len(json.loads((stage/'input/image_fetch_manifest.json').read_text())['items'])==8380
(stage/'results').mkdir(exist_ok=True)
(stage/'logs').mkdir()
source=stage/'tools/fetch_images.py'
compile(source.read_text(),str(source),'exec')
args=[str(project/'env/bin/python'),'-u',str(source),'--attempt','01']
with (stage/'logs/download-attempt-01.log').open('xb') as log:
    process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                             cwd=stage,start_new_session=True)
record={'PID':process.pid,'host':'mu01','command':args,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'metadata_files_verified':len(entries),'download_attempt':'01','model_training_started':False}
(stage/'results/download_launch_01.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record),flush=True)
PY
