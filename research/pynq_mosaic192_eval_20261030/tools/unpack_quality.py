from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
meta=json.loads((ROOT/'evidence/quality_collection.txt').read_text(encoding='utf-8').splitlines()[-1])
a=ROOT/'quality_delivery_v1.tar.gz';assert a.stat().st_size==meta['bytes'] and sha(a)==meta['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(a) as tar:
    members=tar.getmembers();assert len(members)==meta['members']
    for m in members:
        name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts
        f=out.joinpath(*name.parts).resolve();assert f.is_relative_to(out.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
rows=json.loads((out/'quality_manifest.json').read_text(encoding='utf-8'));assert len(rows)==meta['manifest_files']
for row in rows:
    p=out/row['file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
for relative in ['protocol/eval_v1.json','protocol/execution_v1.json','tools/evaluate_quality.py','tools/frozen_input.py']:assert sha(out/relative)==sha(ROOT/relative)
r={'status':'MOSAIC192_QUALITY_ARCHIVE_ALL2696_MEMBERS_AND2695_HASHES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'bytes':a.stat().st_size,'sha256':sha(a),'archive_members':len(members),'manifest_files':len(rows),'whole_goal_complete':False}
f=ROOT/'results/quality_transfer_verification.json';assert not f.exists();f.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r))
