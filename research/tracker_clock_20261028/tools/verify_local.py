from pathlib import Path,PurePosixPath
import csv,hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    record=load(ROOT/'results/delivery_record.json');archive=ROOT/'results/delivery.tar.gz';dest=ROOT/'delivery'
    assert not dest.exists() and sha(archive)==record['sha256'] and archive.stat().st_size==record['bytes']
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==record['manifest_sha256']
        items=json.loads(raw);expected={r['path']:r for r in items};members=tf.getmembers()
        assert len(items)==len(expected)==record['manifest_files']==46 and len(members)==record['archive_members']==47
        assert {r.name for r in members}==set(expected)|{'delivery_manifest.json'}
        for member in members:
            name=PurePosixPath(member.name);assert member.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in member.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());value=tf.extractfile(member).read()
            if member.name in expected:
                item=expected[member.name];assert len(value)==item['bytes'] and hashlib.sha256(value).hexdigest()==item['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value);assert sha(path)==hashlib.sha256(value).hexdigest()
    p=load(ROOT/'protocol/clock_v1.json');summary=load(dest/'results/summary.json');check=load(dest/'results/independent_verification.json')
    assert check['protocol_sha256']==summary['protocol_sha256']==sha(ROOT/'protocol/clock_v1.json')==sha(dest/'protocol/clock_v1.json')
    assert check['summary_sha256']==sha(dest/'results/summary.json') and len(check['conditions'])==len(summary['conditions'])==7
    assert check['flow_rows_verified']==8705 and len(check['comparisons'])==2
    assert all(c['event_times_and_directions_exact_without_ID'] and not c['events_exact_with_ID'] for c in check['comparisons'])
    old=ROOT.parent/'counting_recovery_20261028/delivery'
    for source in p['sources']:
        rel=source['remote_folder'].split('/counting_recovery_20261028/',1)[1]
        for item in source['files']:assert sha(old/rel/item['name'])==item['sha256']
    with (ROOT/'results/all_conditions.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['name','inference_Hz','track_buffer','nominal_lost_budget_s','stable_samples','predicted_down','predicted_up','ROI_track_IDs','ROI_track_rows','history_rows','exact_prior_replay_required']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in summary['conditions']:writer.writerow({k:row[k] for k in fields})
    out={'status':'ALL46_CLOCK_DELIVERY_FILES_AND_PRIOR_INPUT_HASHES_LOCALLY_VERIFIED',
         'files':46,'archive_sha256':record['sha256'],'conditions':7,'exact_replays':5,'independent_event_replays':7,
         'native_flow_rows':8705,'both_controls_preserve_event_times_directions':True,
         'both_controls_change_IDs_and_tracks':True,'detector_forwards':0,'training_updates':0,
         'independent_source_accuracy_verified':False,'board_execution':False,'whole_goal_complete':False}
    target=ROOT/'results/local_verification.json';assert not target.exists();target.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
if __name__=='__main__':main()
