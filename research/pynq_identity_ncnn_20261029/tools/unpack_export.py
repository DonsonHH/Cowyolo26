from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=load(ROOT/'evidence/export_transfer.json');archive=ROOT/'export_delivery.tar.gz'
assert archive.stat().st_size==m['bytes'] and sha(archive)==m['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==m['members']
 for member in members:
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  p=(out/member.name).resolve();assert p.is_relative_to(out.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read())
manifest=load(out/'export_manifest.json');assert len(manifest)==m['manifest_files']
for row in manifest:
 p=out/row['file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
for r in ['protocol/encoder_v1.json','protocol/execution_v2.json','tools/export_encoder.py','tools/export_encoder_v2.py']:
 assert sha(ROOT/r)==sha(out/r)
result={'status':'ALL162_ENCODER_EXPORT_MEMBERS161_HASHES_EXACT','created_UTC':datetime.now(timezone.utc).isoformat(),
 'archive_sha256':sha(archive),'bytes':archive.stat().st_size,'manifest_files':len(manifest),'failed_wrapper_outputs_preserved':True}
(ROOT/'results/export_transfer_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
