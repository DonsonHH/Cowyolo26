from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'evidence/transfer.json').read_text());archive=ROOT/'results_delivery.tar.gz'
assert archive.stat().st_size==m['bytes'] and sha(archive)==m['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==m['members']
 for entry in members:
  assert entry.isfile() and not entry.name.startswith('/') and '..' not in Path(entry.name).parts
  path=(out/entry.name).resolve();assert path.is_relative_to(out.resolve()) and not path.exists()
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(entry).read())
manifest=json.loads((out/'results/assembly_manifest.json').read_text());assert len(manifest)==m['manifest_files']
for row in manifest:
 f=out/row['relative_file'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
for relative in ['protocol/baseline_v1.json','protocol/baseline_v2_path_fix.json','input/validation_images.json','tools/finish_toros.py']:
 assert sha(ROOT/relative)==sha(out/relative)
record={'status':'SAFE136_MEMBERS_AND135_RESULT_FILE_HASHES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'members':len(members),'hashed_files':len(manifest)}
file=ROOT/'results/transfer_verification.json';assert not file.exists();file.parent.mkdir(exist_ok=True);file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
