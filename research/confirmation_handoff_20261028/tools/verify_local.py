from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    r=load(ROOT/'results/delivery_record.json');archive=ROOT/'results/delivery.tar.gz';dest=ROOT/'delivery'
    assert not dest.exists() and sha(archive)==r['sha256'] and archive.stat().st_size==r['bytes']
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==r['manifest_sha256']
        rows=json.loads(raw);expected={x['path']:x for x in rows};members=tf.getmembers()
        assert len(rows)==len(expected)==r['manifest_files'] and len(members)==r['archive_members']
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
    summary=load(dest/'results/replay_v2/summary.json');check=load(dest/'results/independent_verification.json')
    assert check['source_summary_sha256']==sha(dest/'results/replay_v2/summary.json')
    assert check['protocol_sha256']==sha(ROOT/'protocol/handoff_v1.json')==summary['protocol_sha256']
    assert check['module_sha256']==sha(ROOT/'tools/confirmation_counter.py')==summary['module_sha256']
    assert len(check['checks'])==3 and all(x['independent_event_paths']==3 for x in check['checks'])
    assert check['trace_frames']==6525 and check['accepted_history']==41
    assert [x['baseline_down'] for x in summary['conditions']]==[11,10,11]
    assert [x['handoff_down'] for x in summary['conditions']]==[12,11,11]
    assert all(not x['removed_events'] for x in summary['conditions'])
    for x in load(dest/'results/render_verification.json')['files']:
        assert sha(dest/x['path'])==x['sha256'] and x['frames']==1962 and x['fps']==25 and x['strict_decode']=='PASS'
    out={'status':'HANDOFF_DELIVERY_NINE_COUNTER_PATHS_AND_THREE_PREVIEWS_LOCALLY_VERIFIED',
      'files':len(rows),'archive_sha256':r['sha256'],'baseline_predictions':[11,10,11],'handoff_predictions':[12,11,11],
      'counter_paths':9,'trace_frames':6525,'accepted_history':41,'source_accuracy_verified':False,
      'new_detector_forwards':0,'training_updates':0,'board_execution':False,'whole_goal_complete':False}
    target=ROOT/'results/local_verification.json';assert not target.exists();target.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
if __name__=='__main__':main()
