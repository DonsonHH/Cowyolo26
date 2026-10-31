from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
record=load(ROOT/'evidence/transfer.json');archive=ROOT/'results_delivery.tar.gz'
assert archive.stat().st_size==record['bytes'] and sha(archive)==record['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==record['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        target=(out/member.name).resolve();assert target.is_relative_to(out.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read())
rows=load(out/'assembly_manifest.json');assert len(rows)==record['manifest_files']
for row in rows:
    file=out/row['relative_file'];assert file.stat().st_size==row['bytes'] and sha(file)==row['sha256']
for relative in ['protocol/training_v4.json','protocol/formal_execution_v1.json','protocol/evaluation_v1.json','tools/train_condition.py','tools/evaluate.py']:
    assert sha(ROOT/relative)==sha(out/relative)
assert sha(out/'results/all_checkpoints_frozen.json')==sha(ROOT/'evidence/all_checkpoints_frozen.json')
result={'status':'ALL_FORMAL_TRAINING_AND_EVALUATION_ARCHIVE_MEMBERS_AND_HASHES_VERIFIED',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'members':len(members),'hashed_files':len(rows)}
file=ROOT/'results/transfer_verification.json';file.parent.mkdir(exist_ok=True);assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
