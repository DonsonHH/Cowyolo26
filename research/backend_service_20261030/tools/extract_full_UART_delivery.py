from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
uart=load(ROOT/'evidence/full_archive_UART_terminal.json');meta=load(ROOT/'metadata_recovery/transfer.json');archive=ROOT/'backend_service_delivery_v1.tar.gz'
assert uart['status']=='FULL_ORIGINAL_ARCHIVE_UART_COMPLETE_HASH_VERIFIED'
assert archive.stat().st_size==uart['received_binary_bytes']==meta['bytes']==20018871
assert sha(archive)==uart['sha256']==meta['sha256']=='b87a60784d7f414ae512855d3ed658613d8dc7c2e03cf6ec856d7d61856422a6'
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==meta['members']==179
 for member in members:
  path=PurePosixPath(member.name);assert member.isfile() and not path.is_absolute() and '..' not in path.parts
  file=out.joinpath(*path.parts).resolve();assert file.is_relative_to(out.resolve()) and not file.exists();file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
manifest=load(out/'result_manifest.json');assert len(manifest)==178
for row in manifest:
 file=out/row['file'];assert file.stat().st_size==row['bytes'] and sha(file)==row['sha256']
assert sha(out/'run_protocol.json')==sha(ROOT/'protocol/run_v1.json')
for row in load(out/'run_protocol.json')['payload_files']:assert sha(out/row['file'])==row['sha256']==sha(ROOT/'tools'/row['file'])
historical=ROOT/'metadata_recovery'
for row in manifest:
 prior=historical/row['file']
 if prior.exists():assert sha(prior)==sha(out/row['file'])
result={'status':'FULL_ORIGINAL179_MEMBER_UART_ARCHIVE_AND178_MANIFEST_FILES_RECEIVED_AND_HASH_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'source_full_archive_locally_received':True,'members':179,'manifest_files':178,'bytes':archive.stat().st_size,'sha256':sha(archive),
 'new_inference_or_experiment_rerun':False,'all_previous_metadata_recovery_files_same_as_original':True,'whole_goal_complete':False}
f=ROOT/'results/full_archive_transfer_verification_v2.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
