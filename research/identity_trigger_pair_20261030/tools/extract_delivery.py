from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((ROOT/'evidence/board_result_transfer.json').read_text());a=ROOT/'trigger_pair_delivery_v1.tar.xz'
assert a.stat().st_size==meta['bytes']and sha(a)==meta['sha256'];out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(a)as tar:
 members=tar.getmembers();assert len(members)==meta['members']
 for row in members:
  rel=PurePosixPath(row.name);assert row.isfile()and not rel.is_absolute()and'..'not in rel.parts
  p=(out/row.name).resolve();assert p.is_relative_to(out.resolve())and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(row).read())
rows=json.loads((out/'result_manifest.json').read_text());assert len(rows)==meta['manifest_files']
for row in rows:assert(out/row['file']).stat().st_size==row['bytes']and sha(out/row['file'])==row['sha256']
assert sha(out/'run_protocol.json')==sha(ROOT/'protocol/run_v1.json')
p=json.loads((ROOT/'protocol/run_v1.json').read_text())
for row in p['payload_files']:assert sha(out/row['file'])==sha(ROOT/'payload'/row['file'])==row['sha256']
v={'status':'TRIGGER_PAIR_FULL_ORIGINAL_ARCHIVE_AND_ALL_CODE_RESULT_MANIFESTS_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),'archive_bytes':meta['bytes'],'archive_SHA256':meta['sha256'],'members':len(members),'manifest_files':len(rows),'new_model_forwards':0};p=ROOT/'results/archive_verification.json';assert not p.exists();p.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]));print(json.dumps(v))
