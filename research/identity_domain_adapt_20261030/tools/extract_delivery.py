from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,json,tarfile

ROOT=Path(__file__).resolve().parents[1]
transfer=json.loads((ROOT/'evidence/result_transfer.json').read_text());archive=ROOT/'domain_delivery_v1.tar.gz'
assert archive.stat().st_size==transfer['bytes']and hashlib.sha256(archive.read_bytes()).hexdigest()==transfer['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==transfer['members']
 for member in members:
  relative=PurePosixPath(member.name);assert member.isfile()and not relative.is_absolute()and'..'not in relative.parts
  path=(out/member.name).resolve();assert path.is_relative_to(out.resolve())and not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
manifest=json.loads((out/'result_manifest.json').read_text());assert len(manifest)==transfer['manifest_files']
for row in manifest:
 path=out/row['file'];assert path.stat().st_size==row['bytes']and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
assert(out/'protocol/run_v1.json').read_bytes()==(ROOT/'protocol/run_v1.json').read_bytes()
record={'status':'COMPLETE_DOMAIN_TRAINING_AND_EVALUATION_ARCHIVE_ALL_FILES_HASH_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
        **transfer,'new_model_forwards_by_extraction':0,'whole_goal_complete':False}
p=ROOT/'results/transfer_verification.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
