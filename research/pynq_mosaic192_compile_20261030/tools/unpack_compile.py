from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
record=json.loads((ROOT/'evidence/compile_collection.txt').read_text(encoding='utf-8').splitlines()[-1])
a=ROOT/'qualification_delivery_v1.tar.gz';assert a.stat().st_size==record['bytes'] and sha(a)==record['sha256']
out=ROOT/'delivery';assert not out.exists();out.mkdir()
with tarfile.open(a) as tar:
    members=tar.getmembers();assert len(members)==record['members']
    for m in members:
        name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts
        f=out.joinpath(*name.parts).resolve();assert f.is_relative_to(out.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
files=json.loads((out/'qualification_manifest.json').read_text(encoding='utf-8'));assert len(files)==record['manifest_files']
for r in files:
    p=out/r['relative_file'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
r={'status':'NEW_MOSAIC192_COMPILE_ARTIFACTS_ARCHIVE_AND_FILE_HASHES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'archive_bytes':record['bytes'],'archive_sha256':record['sha256'],'members':len(members),'manifest_files':len(files),'whole_goal_complete':False}
p=ROOT/'results/transfer_verification.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r))
