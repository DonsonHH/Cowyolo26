from pathlib import Path,PurePosixPath
from collections import defaultdict
import csv,hashlib,json,math,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(Path(p).open(newline='',encoding='utf-8')))
def iou(box,other):
    a=np.asarray(box,np.float32).astype(float);b=np.asarray(other,np.float32).astype(float)
    x0=max(a[0],b[0]);y0=max(a[1],b[1]);x1=min(a[2],b[2]);y1=min(a[3],b[3])
    intersect=max(0,x1-x0)*max(0,y1-y0)
    union=max(0,a[2]-a[0])*max(0,a[3]-a[1])+max(0,b[2]-b[0])*max(0,b[3]-b[1])-intersect
    return intersect/(union+1e-7)
def main():
    record=load(ROOT/'results/exit_probe_delivery_record.json');archive=ROOT/'results/exit_probe_delivery.tar.gz';dest=ROOT/'exit_probe_delivery'
    assert not dest.exists() and sha(archive)==record['sha256'] and archive.stat().st_size==record['bytes']
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==record['manifest_sha256']
        rows=json.loads(raw);expected={r['path']:r for r in rows};members=tf.getmembers()
        assert len(rows)==len(expected)==record['manifest_files']==9 and len(members)==record['archive_members']==10
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
    p=load(ROOT/'protocol/exit_probe_v1.json');folder=dest/'results/exit_probe';summary=load(folder/'summary.json');trace=load(folder/'association_trace.json')
    assert sha(ROOT/'protocol/exit_probe_v1.json')==sha(dest/'protocol/exit_probe_v1.json')==summary['protocol_sha256']
    assert sha(ROOT/'tools/exit_probe.py')==sha(dest/'tools/exit_probe.py') and summary['full_tracks_history_events_exact']
    assert len(trace)==11 and [r['source_frame'] for r in trace]==p['probe_frames']
    old=PROJECT/'counting_recovery_20261028/delivery/results/full640_confirmation/full640_5hz_seed28'
    rawframes=defaultdict(list);axes={}
    for r in read(old/'pretracker_boxes.csv'):rawframes[int(r['frame'])].append([*[float(r[k]) for k in ['x1','y1','x2','y2']],float(r['confidence']),0])
    for r in read(old/'source_tracks.csv'):
        if int(r['track_id'])==117:axes[int(r['source_frame'])]=float(r['axis_position'])
    metric_rows=0;maxerr=0.;brief=[]
    for t in trace:
        f=t['source_frame'];assert t['raw_boxes']==rawframes[f] and t['target_axis']==axes.get(f)
        assert t['target_confirmed_output']==t['target_output_in_ROI']
        high=[(i,r) for i,r in enumerate(rawframes[f]) if r[4]>=t['high_threshold']]
        low=[(i,r) for i,r in enumerate(rawframes[f]) if t['low_threshold']<r[4]<t['high_threshold']]
        assert [d['input_detection_index'] for d in t['first_high_detections']]==[i for i,r in high]
        assert [d['input_detection_index'] for d in t['second_low_detections']]==[i for i,r in low]
        for d,(i,r) in zip(t['first_high_detections'],high):
            assert d['confidence']==r[4] and np.allclose(d['xyxy'],r[:4],rtol=0,atol=.0005)
        target=t['first_target_predicted'];costs=[]
        for d,actual in zip(t['first_high_detections'],t['first_target_costs']):
            expectedcost=1-iou(target['xyxy'],d['xyxy'])*d['confidence']
            error=abs(expectedcost-actual);maxerr=max(maxerr,error);assert error<1e-6;metric_rows+=1;costs.append(actual)
        firstmatched=any(m['stage']=='first' for m in t['target_applied_matches'])
        secondbox=t['target_after']['xyxy'] if firstmatched else target['xyxy']
        for d,actual_iou,actual_cost in zip(t['second_low_detections'],t['second_diagnostic_target_IoUs'],t['second_diagnostic_target_costs']):
            expected_iou=iou(secondbox,d['xyxy']);expectedcost=1-expected_iou*d['confidence']
            error=max(abs(expected_iou-actual_iou),abs(expectedcost-actual_cost));maxerr=max(maxerr,error)
            assert error<1e-6 and actual_cost>.75;metric_rows+=1
        for match in t['target_applied_matches']:
            d=match['detection'];index=d['input_detection_index'];assert d['confidence']==rawframes[f][index][4]
            assert np.allclose(d['xyxy'],rawframes[f][index][:4],atol=.0005,rtol=0)
        assert t['second_target_eligible']==(117 in t['second_eligible_IDs'])
        if target['state']==2 and 117 in t['first_unmatched_IDs']:assert not t['second_target_eligible']
        best=min(range(len(costs)),key=costs.__getitem__) if costs else None
        brief.append({'source_frame':f,'raw_ROI_boxes':sum(.34<(r[0]+r[2])/5120<.75 for r in rawframes[f]),
           'target_state_before_first':target['state'],'best_first_cost':costs[best] if best is not None else None,
           'best_first_detection_index':t['first_high_detections'][best]['input_detection_index'] if best is not None else None,
           'target_first_unmatched':117 in t['first_unmatched_IDs'],'low_detection_scores':[d['confidence'] for d in t['second_low_detections']],
           'low_diagnostic_costs':t['second_diagnostic_target_costs'],'target_second_eligible':t['second_target_eligible'],
           'actual_target_matches':[{'stage':m['stage'],'index':m['detection']['input_detection_index'],'score':m['detection']['confidence']} for m in t['target_applied_matches']],
           'target_state_after':t['target_after']['state'],'target_y':t['target_axis'],'outside_ROI_only':t['target_confirmed_output'] and not t['target_output_in_ROI']})
    grid=load(folder/'low_score_cost_grid.json');costs=np.asarray(grid['installed_fused_costs']);independent=1-np.asarray(grid['IoUs'])[:,None]*np.asarray(grid['detection_scores'])[None,:]
    assert np.max(abs(costs-independent))<1e-6 and np.min(costs)>.75 and grid['matches']==[]
    assert summary['unchanged_original_down_events']==11 and summary['target_output_frames']==[9340,9345,9350,9355,9375]
    out={'status':'NINE_PROBE_FILES_ELEVEN_FRAMES_AND_ASSOCIATION_COSTS_INDEPENDENTLY_VERIFIED',
        'files':9,'protocol_sha256':summary['protocol_sha256'],'trace_frames':11,'real_cost_entries_verified':metric_rows,
        'maximum_cost_or_IoU_difference':maxerr,'synthetic_cost_pairs':25,'all_low_fused_costs_over_secondstage_limit':True,
        'trace_summary':brief,'source_full_original_replay_exact':True,'original_seed28_predictions':11,
        'physical_box_to_cow_correspondence_independently_established':False,'new_detector_forwards':0,
        'training_updates':0,'independent_source_accuracy':None,'board_execution':False,'whole_goal_complete':False}
    target=ROOT/'results/exit_probe_local_verification.json';assert not target.exists();save=lambda p,v:Path(p).write_text(json.dumps(v,indent=2),encoding='utf-8')
    save(target,out);print(json.dumps(out))
if __name__=='__main__':main()
