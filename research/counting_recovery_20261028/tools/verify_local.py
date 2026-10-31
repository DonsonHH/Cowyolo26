from pathlib import Path,PurePosixPath
import csv,hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    r=load(ROOT/'results/compact_delivery_record.json');archive=ROOT/'results/compact_delivery.tar.gz'
    assert sha(archive)==r['sha256'] and archive.stat().st_size==r['bytes']
    dest=ROOT/'delivery';assert not dest.exists()
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==r['manifest_sha256']
        rows=json.loads(raw);expected={i['path']:i for i in rows};members=tf.getmembers()
        assert len(rows)==len(expected)==r['manifest_files'] and len(members)==r['archive_members']
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for member in members:
            name=PurePosixPath(member.name);assert member.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in member.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve())
            data=tf.extractfile(member).read()
            if member.name in expected:
                item=expected[member.name];assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
    summary=load(dest/'results/replay_v2/summary.json');check=load(dest/'results/independent_verification.json')
    assert check['source_summary_sha256']==sha(dest/'results/replay_v2/summary.json')
    assert check['protocol_sha256']==sha(ROOT/'protocol/recovery_v2.json')==summary['protocol_sha256']
    assert check['baseline_exact_regressions']==1 and len(check['conditions'])==10
    assert check['snapshot_full_decodes']==60
    extension=load(dest/'results/full640_confirmation/summary.json')
    assert check['extension_summary_sha256']==sha(dest/'results/full640_confirmation/summary.json')
    conditions=summary['conditions']+extension['conditions']
    assert summary['independent_source_accuracy'] is None and summary['new_training_updates']==0
    with (ROOT/'results/all_conditions.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['name','seed','imgsz','inference_Hz','crop_left','crop_right','confidence','stable_samples','predicted_down','predicted_up','raw_ROI_frames','tracked_ROI_frames','sampled_frames_in_scope']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for c in conditions:
            a=c['arm'];w.writerow({**{k:c[k] for k in ['name','seed','predicted_down','predicted_up','raw_ROI_frames','tracked_ROI_frames','sampled_frames_in_scope']},
                'imgsz':a['imgsz'],'inference_Hz':25/a['stride'],'crop_left':a['crop_x'][0],'crop_right':a['crop_x'][1],
                'confidence':a['confidence'],'stable_samples':a['stable_samples']})
    report={'status':'ALL_RECOVERY_DELIVERY_FILES_AND_TEN_CONDITIONS_LOCALLY_VERIFIED','files':len(rows),'bytes':r['bytes'],
        'archive_sha256':r['sha256'],'coordinate_rows_verified':check['coordinate_rows'],'snapshot_full_decodes':60,
        'baseline_regression':True,'new_training':False,'independent_source_accuracy':None,'board_execution':False,'whole_goal_complete':False}
    path=ROOT/'results/local_verification.json';assert not path.exists();path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report));print(json.dumps({'coverage_selected_arm':summary['selected_arm'],'all_results':[{k:c[k] for k in ['name','predicted_down','predicted_up','raw_ROI_frames','tracked_ROI_frames']} for c in conditions]}))
if __name__=='__main__':main()
