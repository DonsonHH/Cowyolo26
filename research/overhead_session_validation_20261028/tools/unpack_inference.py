from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'inference_delivery.tar.gz';assert p.stat().st_size==29103448 and hashlib.sha256(p.read_bytes()).hexdigest()=='99e64498f89bf90f807bae77a6244bf8a3d1a80cbff669232328473bba092656'
out=ROOT/'inference_delivery';out.mkdir(exist_ok=False)
with tarfile.open(p) as t:
    members=t.getmembers()
    for m in members:
        n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
    t.extractall(out,filter='data')
s=json.loads((out/'results/inference/summary.json').read_text(encoding='utf-8'))
assert len(s['conditions'])==8 and s['new_model_forwards']==216
for r in s['conditions']:
    p=out/'results/inference'/r['sequence']/r['model']/'predictions.mp4'
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['movie_sha256']
record={'status':'EIGHT_CONDITIONS_ARCHIVE_AND_VIDEO_HASHES_VERIFIED','archive_files':len(members),'conditions':8,'new_forwards':216,'full_video_decode_pending':True}
(ROOT/'evidence/inference_archive_verification.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
