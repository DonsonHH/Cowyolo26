from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=load(ROOT/'evidence/data_transfer.json');archive=ROOT/'data_delivery.tar.gz'
assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==meta['members']
    for m in members:
        assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
        target=(out/m.name).resolve();assert target.is_relative_to(out.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
rows=load(out/'results/assembly_manifest.json');assert len(rows)==meta['manifest_files']
for r in rows:
    f=out/r['relative_file'];assert f.stat().st_size==r['bytes'] and sha(f)==r['sha256']
for f in ['protocol/roi_v1.json','protocol/media_and_pixel_v1.json','tools/run_roi.py','tools/verify_pixels.py']:
    assert sha(out/f)==sha(ROOT/f)
record={'status':'ALL_ROI_DATA_MEMBERS_AND_HASHES_EXACT','created_UTC':datetime.now(timezone.utc).isoformat(),
        'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'members':len(members),'hashed_files':len(rows)}
file=ROOT/'results/data_transfer_verification.json';file.parent.mkdir(exist_ok=True);assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
