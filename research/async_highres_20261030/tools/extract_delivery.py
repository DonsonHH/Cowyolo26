from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import json,tarfile,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
c=load(ROOT/'evidence/collection_terminal_read.json');r=json.loads(c['stdout']);assert c['exit_code']==0 and not r['proc_exists']
m=r['terminal']['transfer'];assert r['terminal']['status']=='RESULT_ARCHIVE_COMPLETE'
a=ROOT/'async_highres_delivery_v1.tar.gz';assert a.stat().st_size==m['bytes'] and sha(a)==m['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(a) as tar:
 members=tar.getmembers();assert len(members)==m['members']
 for item in members:
  name=PurePosixPath(item.name);assert item.isfile() and not name.is_absolute() and '..' not in name.parts
  f=out.joinpath(*name.parts).resolve();assert f.is_relative_to(out.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(item).read())
for row in load(out/'result_manifest.json'):
 f=out/row['file'];assert f.is_relative_to(out) and f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
for relative,local in [('run_protocol.json','protocol/run_v1.json'),('board_async_repeats.py','tools/board_async_repeats.py'),('background_selected_worker.py','tools/background_selected_worker.py'),('causal_selector.py','tools/causal_selector.py')]:assert sha(out/relative)==sha(ROOT/local)
for row in load(out/'run_protocol.json')['payload_files']:assert sha(out/row['file'])==row['sha256']==sha(ROOT/'tools'/row['file'])
f=ROOT/'results/transfer_verification.json';assert not f.exists();f.write_text(json.dumps({'status':'ALL_ARCHIVE_MEMBERS_AND_MANIFEST_HASHES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),**m},indent=2)+'\n',encoding='utf-8')
print(json.dumps(m))
