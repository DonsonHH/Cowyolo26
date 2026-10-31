from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=load(ROOT/'evidence/transfer.json');archive=ROOT/'results_delivery.tar.gz';assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==meta['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        file=(out/member.name).resolve();assert file.is_relative_to(out.resolve()) and not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
rows=load(out/'assembly_manifest.json');assert len(rows)==meta['manifest_files']
for row in rows:
    file=out/row['relative_file'];assert file.stat().st_size==row['bytes'] and sha(file)==row['sha256']
for relative in ['protocol/crop_v1.json','protocol/execution_v1.json','tools/run_crop.py']:
    assert sha(ROOT/relative)==sha(out/relative)
result={'status':'ALL_FIXED_CROP_RESULT_MEMBERS_AND_FILE_HASHES_EXACT','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'archive_sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(members),'hashed_files':len(rows)}
file=ROOT/'results/transfer_verification.json';file.parent.mkdir(exist_ok=True);assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
