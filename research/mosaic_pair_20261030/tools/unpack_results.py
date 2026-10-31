from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
text=(ROOT/'evidence/collection.txt').read_text(encoding='utf-8');record=json.loads(next(s for s in reversed(text.splitlines()) if s.startswith('{')))
archive=ROOT/'paired_results_delivery_v1.tar.gz';assert sha(archive)==record['sha256'] and archive.stat().st_size==record['bytes']
dest=ROOT/'delivery';assert not dest.exists();dest.mkdir()
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==record['files']
    for m in members:
        name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts
        p=dest.joinpath(*name.parts).resolve();assert p.is_relative_to(dest.resolve()) and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
files=json.loads((dest/'results/final_transfer_manifest.json').read_text(encoding='utf-8'))
for row in files:
    p=dest/row['file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['file']
result={'status':'ALL_SIX_CHECKPOINTS_TRAINING_RECORDS_RAW_EVALUATION_AND_MEDIA_HASHES_VERIFIED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'archive_bytes':record['bytes'],'archive_sha256':record['sha256'],'members':len(members),
    'artifact_hash_entries_checked':len(files),'all6_training_main_jobs_completed':True,'training_stderr_all_clean':False,
    'failed_evaluation_and_teardown_messages_preserved':True,'whole_goal_complete':False}
out=ROOT/'results/transfer_verification.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
