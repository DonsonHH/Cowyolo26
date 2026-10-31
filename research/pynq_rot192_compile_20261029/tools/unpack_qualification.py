from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=load(ROOT/'evidence/qualification_transfer.json');archive=ROOT/'qualification_delivery.tar.gz'
assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==meta['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        target=(out/member.name).resolve();assert target.is_relative_to(out.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read())
rows=load(out/'qualification_manifest.json');assert len(rows)==meta['manifest_files']
for r in rows:
    p=out/r['relative_file'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
for relative in ['protocol/compile_v1.json','tools/compile_rot192.py','tools/normalize_graph.py']:
    assert sha(out/relative)==sha(ROOT/relative)
file=ROOT/'results/qualification_transfer_verification.json';file.parent.mkdir(exist_ok=True);assert not file.exists()
record={'status':'ALL53_MEMBERS_AND52_FILE_HASHES_EXACT','created_host_UTC':datetime.now(timezone.utc).isoformat(),
       'archive_sha256':sha(archive),'members':len(members),'hashed_files':len(rows),'bytes':archive.stat().st_size}
file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
