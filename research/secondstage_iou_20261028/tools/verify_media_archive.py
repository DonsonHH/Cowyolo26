from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=load(ROOT/'results/media_delivery_record.json');archive=ROOT/'results/media_delivery.tar.gz';dest=ROOT/'media_delivery';assert not dest.exists()
assert sha(archive)==r['sha256'] and archive.stat().st_size==r['bytes']
with tarfile.open(archive,'r:gz') as tf:
    raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==r['manifest_sha256']
    rows=json.loads(raw);expected={x['path']:x for x in rows};members=tf.getmembers()
    assert len(rows)==len(expected)==r['manifest_files']==25 and len(members)==r['archive_members']==26
    assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
    for m in members:
        name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
        path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
        if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
render=load(dest/'results/render_verification.json');assert render['local_verification_sha256']==sha(ROOT/'results/local_verification.json')
assert len(render['files'])==3 and all(f['strict_decode']=='PASS' and f['frames']==1962 for f in render['files'])
out={'status':'ALL25_MEDIA_ARCHIVE_FILES_LOCALLY_VERIFIED','files':25,'archive_sha256':r['sha256'],'videos':3,'new_inference':False}
target=ROOT/'results/media_archive_verification.json';assert not target.exists();target.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
