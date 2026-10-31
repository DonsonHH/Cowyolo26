from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,json,tarfile

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((ROOT/'evidence/board_result_transfer.json').read_text());a=ROOT/'identity_pair_delivery_v1.tar.xz'
assert a.stat().st_size==v['bytes']and sha(a)==v['sha256'];out=ROOT/'board_delivery';out.mkdir(exist_ok=False)
with tarfile.open(a)as tar:
 members=tar.getmembers();assert len(members)==v['members']
 for row in members:
  rel=PurePosixPath(row.name);assert row.isfile()and not rel.is_absolute()and'..'not in rel.parts
  p=(out/row.name).resolve();assert p.is_relative_to(out.resolve())and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(row).read())
rows=json.loads((out/'result_manifest.json').read_text());assert len(rows)==v['manifest_files']
for row in rows:assert sha(out/row['file'])==row['sha256']and(out/row['file']).stat().st_size==row['bytes']
assert sha(out/'run_protocol.json')==sha(ROOT/'protocol/run_v1.json')
plan=json.loads((ROOT/'protocol/run_v1.json').read_text())
for row in plan['payload_files']:assert sha(out/row['file'])==sha(ROOT/'payload'/row['file'])==row['sha256']
result={'status':'FULL_ORIGINAL_IDENTITY_PAIR_ARCHIVE_ALL_MEMBERS_AND_MANIFEST_FILES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),'archive_bytes':v['bytes'],'archive_sha256':v['sha256'],'manifest_files':len(rows),'archive_members':len(members),'new_model_forwards':0};p=ROOT/'results/board_archive_verification.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
