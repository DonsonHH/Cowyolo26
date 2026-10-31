from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
sha=lambda data:hashlib.sha256(data).hexdigest()
def main():
    record=json.loads((ROOT/'evidence/delivery_record.json').read_text());archive=ROOT/'regression_delivery.tar.gz';dest=ROOT/'delivery'
    assert archive.stat().st_size==record['archive_bytes'] and sha(archive.read_bytes())==record['archive_sha256']
    assert not dest.exists()
    with tarfile.open(archive,'r:gz') as tf:
        rows=json.loads(tf.extractfile('delivery_manifest.json').read())['files'];expected={r['file']:r for r in rows};members=tf.getmembers()
        assert len(expected)==len(rows)==140 and len(members)==record['files']==141
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            target=dest.joinpath(*name.parts).resolve();assert target.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and sha(data)==expected[m.name]['sha256']
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target.read_bytes())==sha(data)
    print(json.dumps({'status':'ALL141_ARCHIVE_MEMBERS_SAFELY_EXTRACTED_AND_HASHED','manifest_files':140,'archive_sha256':record['archive_sha256']}))
if __name__=='__main__':main()
