"""Unpack only an archive with exact terminal-collection SHA and file hashes."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lines=(ROOT/'evidence/collection_v2.txt').read_text(encoding='utf-8').splitlines()
row=json.loads(next(s for s in reversed(lines) if s.startswith('{')))
archive=ROOT/'results_delivery_v2.tar.gz'
assert archive.stat().st_size==row['bytes'] and sha(archive)==row['sha256']
dest=ROOT/'delivery';assert not dest.exists();dest.mkdir()
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==row['files']
    for m in members:
        name=PurePosixPath(m.name)
        assert m.isfile() and not name.is_absolute() and '..' not in name.parts
        target=dest.joinpath(*name.parts).resolve();assert target.is_relative_to(dest.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
count=0
for path in [dest/'results/artifact_manifest.json',dest/'results/failed_v1_artifact_manifest.json']:
    for record in json.loads(path.read_text(encoding='utf-8')):
        f=dest/record['file'];assert f.stat().st_size==record['bytes'] and sha(f)==record['sha256'];count+=1
result={'status':'TERMINAL_JOBS_ARCHIVE_AND_SUCCESS_AND_FAILED_OUTPUT_HASHES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'members':len(members),'artifact_hash_entries_checked':count,
    'original_failed_outputs_collected':True,'whole_goal_complete':False}
out=ROOT/'results/transfer_verification.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
