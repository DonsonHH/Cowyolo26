from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    record=json.loads((ROOT/'evidence/delivery_record.json').read_text());archive=ROOT/'RF_stream_delivery.tar.gz';dest=ROOT/'delivery'
    assert not dest.exists() and archive.stat().st_size==record['archive_bytes'] and sha(archive.read_bytes())==record['archive_sha256']
    with tarfile.open(archive,'r:gz') as tf:
        rows=json.loads(tf.extractfile('delivery_manifest.json').read())['files'];expected={r['file']:r for r in rows};members=tf.getmembers()
        assert len(rows)==len(expected)==214 and len(members)==record['files']==215
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and sha(data)==expected[m.name]['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path.read_bytes())==sha(data)
    print(json.dumps({'manifest_files':214,'archive_members':215,'sha256':record['archive_sha256']}))
if __name__=='__main__':main()
