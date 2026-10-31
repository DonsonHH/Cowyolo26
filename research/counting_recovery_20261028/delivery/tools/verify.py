"""Independent eventstate replay and crop/rotation fourcorner verification."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,os
import numpy as np
from PIL import Image
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def read(path):return list(csv.DictReader(Path(path).open(newline='')))
def normalized(rows):return [{k:None if v in [None,''] else int(v) if k in ['source_frame','track_id'] else float(v) for k,v in row.items()} for row in rows]

def independent_events(rows,stride,required):
    seen=defaultdict(dict)
    for r in rows:seen[int(r['source_frame'])][int(r['track_id'])]=float(r['axis_position'])
    state={};events=[]
    for frame in range(0,10874,stride):
        positions=seen.get(frame,{})
        for identity,s in state.items():
            if identity not in positions:s['candidate']=None;s['run']=0
        for identity,pos in positions.items():
            s=state.setdefault(identity,{'last':-1e20,'origin':None,'candidate':None,'run':0})
            if frame/25-s['last']>2:s.update(origin=None,candidate=None,run=0)
            s['last']=frame/25
            region='A' if pos<.4 else 'B' if pos>.6 else None
            if region is None:s.update(candidate=None,run=0);continue
            s['run']=s['run']+1 if s['candidate']==region else 1;s['candidate']=region
            if s['run']<required or s['origin']==region:continue
            old=s['origin'];s['origin']=region
            if old is not None and frame>=8912:events.append({'time_s':frame/25,'track_id':identity,'direction':old+'->'+region,'source_frame':frame})
    return events

def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname()!='mu01'
    summary_path=ROOT/'results/replay_v2/summary.json';summary=load(summary_path)
    protocol=ROOT/'protocol/recovery_v2.json';p=load(protocol);assert summary['protocol_sha256']==sha(protocol)
    assert len(summary['conditions'])==8
    extension_path=ROOT/'results/full640_confirmation/summary.json';extension=load(extension_path)
    assert extension['protocol_sha256']==sha(protocol) and len(extension['conditions'])==2
    conditions=summary['conditions']+extension['conditions']
    assert len({r['name'] for r in conditions})==10
    records=[];coordinates=0;images=0;baseline=0
    for condition in conditions:
        folder=summary_path.parent/condition['name']
        if not folder.exists():folder=extension_path.parent/condition['name']
        arm=condition['arm'];stride=arm['stride'];stable=arm['stable_samples']
        assert arm in p['arms'];left,right=arm['crop_x']
        rows=read(folder/'source_warmup_tracks.csv')+read(folder/'source_tracks.csv')
        for r in rows:
            f=int(r['source_frame']);assert f%stride==0 and 0<=f<=10873
            cx=(float(r['x1'])+float(r['x2']))/5120;cy=(float(r['y1'])+float(r['y2']))/2880
            assert .34<cx<.75 and float(r['axis_position'])==cy
        events=independent_events(rows,stride,stable);assert events==load(folder/'source_events.json')
        if stride==1:assert independent_events(rows,stride,3)==load(folder/'dense_3sample_diagnostic_events.json')
        if arm['name']=='baseline_full320_5hz':
            prior=ROOT/f'input/baseline_seed{condition["seed"]}'
            assert events==load(prior/'source_events.json')
            assert normalized(read(folder/'source_tracks.csv'))==normalized(read(prior/'source_tracks.csv'))
            assert normalized(read(folder/'source_warmup_tracks.csv'))==normalized(read(prior/'source_warmup_tracks.csv'))
            baseline+=1
        raw=read(folder/'pretracker_boxes.csv');framecounts=Counter();raw_roi=set();maxerror=0.
        for r in raw:
            u1,v1,u2,v2=[float(r[k]) for k in ['u1','v1','u2','v2']]
            # Fourcorner method independent of vectorcoordinate assignment.
            points=[(v+left,1440-u) for u,v in [(u1,v1),(u1,v2),(u2,v1),(u2,v2)]]
            xs,ys=zip(*points);expected=np.array([min(xs),min(ys),max(xs),max(ys)],np.float64)
            actual=np.array([float(r[k]) for k in ['x1','y1','x2','y2']],np.float64)
            assert np.array_equal(expected.astype(np.float32).astype(float),actual)
            assert float(r['confidence'])>=arm['confidence']
            f=int(r['frame']);assert f%stride==0
            framecounts[f]+=1;maxerror=max(maxerror,float(np.max(np.abs(expected-actual))));coordinates+=1
            if f>=8912 and .34<(actual[0]+actual[2])/5120<.75:raw_roi.add(f)
        seams=load(folder/'seam_checks.json');assert [r['frame'] for r in seams]==list(range(0,10874,stride))
        assert all(r['native_H']==1440 and r['native_W']==2560 and r['raw_boxes']==framecounts[r['frame']] and
                   r['crop_left']==left and r['crop_right']==right and r['restored_before_tracker'] for r in seams)
        tracked={int(r['source_frame']) for r in rows if int(r['source_frame'])>=8912}
        assert len(raw_roi)==condition['raw_ROI_frames'] and len(tracked)==condition['tracked_ROI_frames']
        assert condition['predicted_down']==sum(e['direction']=='A->B' for e in events)
        assert condition['predicted_up']==sum(e['direction']=='B->A' for e in events)
        assert maxerror==condition['max_inverse_rounding_error']
        for f in [8912,9345,9420,9550,9700,10873]:
            with Image.open(folder/f'f{f}.jpg') as image:image.load();assert image.size==(1280,720)
            images+=1
        records.append({'condition':condition['name'],'predicted_down':condition['predicted_down'],
                        'predicted_up':condition['predicted_up'],'raw_ROI_frames':len(raw_roi),
                        'tracked_ROI_frames':len(tracked),'event_replay_exact':True,'coordinate_rows':len(raw)})
    pilot=summary['conditions'][:6];eligible=[r for r in pilot if r['arm']['stride']==5]
    chosen=max(eligible,key=lambda r:(r['raw_ROI_frames'],-r['arm']['imgsz'],r['arm']['name']))
    assert chosen['arm']==summary['selected_arm']
    assert [r['seed'] for r in summary['conditions'] if r['arm']==chosen['arm']]==[26,27,28]
    result={'status':'ALL10_EVENT_REPLAYS_NATIVE_COORDINATES_AND_FROZEN_BASELINE_INDEPENDENTLY_VERIFIED',
        'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(protocol),'source_summary_sha256':sha(summary_path),
        'extension_summary_sha256':sha(extension_path),
        'conditions':records,'baseline_exact_regressions':baseline,'coordinate_rows':coordinates,'snapshot_full_decodes':images,
        'selection_uses_raw_ROI_coverage_not_target_count':True,'selected_arm':chosen['arm'],
        'independent_source_accuracy':None,'new_training_updates':0,'board_execution':False,'whole_goal_complete':False}
    target=ROOT/'results/independent_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
