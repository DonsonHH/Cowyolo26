from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=load(ROOT/'evidence/quality_transfer.json');archive=ROOT/'quality_delivery.tar.gz'
assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==meta['members']
 for m in members:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  target=(out/m.name).resolve();assert target.is_relative_to(out.resolve()) and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
manifest=load(out/'quality_manifest.json');assert len(manifest)==meta['manifest_files']
for row in manifest:
 path=out/row['file'];assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
for relative in ['protocol/eval_v1.json','protocol/eval_v2.json','protocol/execution_v1.json','protocol/execution_v2.json',
 'tools/evaluate_quality.py','tools/evaluate_quality_v2.py','tools/frozen_input.py']:
 assert sha(out/relative)==sha(ROOT/relative)
result={'status':'ALL4506_QUALITY_MEMBERS_AND4505_MANIFEST_HASHES_EXACT','created_UTC':datetime.now(timezone.utc).isoformat(),
 'bytes':archive.stat().st_size,'sha256':sha(archive),'archive_members':len(members),'manifest_files':len(manifest),'failed_v1_outputs_preserved':True}
file=ROOT/'results/quality_transfer_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
