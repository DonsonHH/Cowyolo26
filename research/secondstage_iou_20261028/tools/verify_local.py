from pathlib import Path,PurePosixPath
from collections import defaultdict
import ast,copy,csv,hashlib,json,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def read(p):return list(csv.DictReader(Path(p).open(newline='',encoding='utf-8')))
def normalized(rows):return [{k:int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]
def iou(a,b):
    a=np.asarray(a,np.float32).astype(float);b=np.asarray(b,np.float32).astype(float)
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=max(0,a[2]-a[0])*max(0,a[3]-a[1])+max(0,b[2]-b[0])*max(0,b[3]-b[1])-inter
    return inter/(union+1e-7)
def counter(frames):
    states={};events=[]
    for frame in range(0,10874,5):
        now=frame/25;positions=frames.get(frame,{})
        for tid,s in states.items():
            if tid not in positions:s['candidate']=None;s['n']=0
        for tid,y in positions.items():
            s=states.setdefault(tid,{'last':-1e30,'origin':None,'candidate':None,'n':0})
            if now-s['last']>2:s.update(origin=None,candidate=None,n=0)
            s['last']=now;zone='A' if y<.4 else 'B' if y>.6 else None
            if zone is None:s.update(candidate=None,n=0);continue
            s['n']=s['n']+1 if s['candidate']==zone else 1;s['candidate']=zone
            if s['n']<3 or s['origin']==zone:continue
            old=s['origin'];s['origin']=zone
            if old and frame>=8912:events.append({'time_s':now,'track_id':tid,'direction':old+'->'+zone,'source_frame':frame})
    return events
def scope_check():
    before=ast.parse((PROJECT/'counting_recovery_20261028/evidence/installed_byte_tracker.py').read_text(encoding='utf-8'))
    cls=next(c for c in before.body if isinstance(c,ast.ClassDef) and c.name=='BYTETracker')
    method=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_second_association'))
    removed=0
    for n in ast.walk(method):
        if hasattr(n,'body') and isinstance(n.body,list):
            matches=[x for x in n.body if isinstance(x,ast.If) and ast.unparse(x.test)=='self.args.fuse_score']
            removed+=len(matches);n.body=[x for x in n.body if x not in matches]
    after=ast.parse((ROOT/'tools/secondstage_tracker.py').read_text(encoding='utf-8'))
    cls=next(c for c in after.body if isinstance(c,ast.ClassDef) and c.name=='SecondStageIoUTracker')
    methods=[n for n in cls.body if isinstance(n,ast.FunctionDef)]
    assert removed==1 and len(methods)==1 and ast.dump(method,include_attributes=False)==ast.dump(methods[0],include_attributes=False)
def main():
    target=ROOT/'results/local_verification.json';assert not target.exists()
    record=load(ROOT/'results/replay_delivery_record.json');archive=ROOT/'results/replay_delivery.tar.gz';dest=ROOT/'delivery';assert not dest.exists()
    assert sha(archive)==record['sha256'] and archive.stat().st_size==record['bytes']
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==record['manifest_sha256']
        manifest=json.loads(raw);expected={r['path']:r for r in manifest};members=tf.getmembers()
        assert len(expected)==len(manifest)==record['manifest_files']==71 and len(members)==record['archive_members']==72
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
    p=load(ROOT/'protocol/secondstage_v1.json');s=load(dest/'results/summary.json');assert s['protocol_sha256']==sha(ROOT/'protocol/secondstage_v1.json')
    assert s['candidate_module_sha256']==sha(ROOT/'tools/secondstage_tracker.py')==p['candidate_module_sha256']
    scope_check();assert load(dest/'results/candidate_green_tests.json')['gate_passed']
    assert load(dest/'results/candidate_green_tests.json')['tests']==9
    cost_entries=0;decisions=0;matches=0;maxerror=0.;track_rows=0;condition_records=[]
    for c in s['conditions']:
        folder=dest/'results'/c['name'];source=next(r for r in p['sources'] if r['seed']==c['seed'])
        previous=PROJECT/'counting_recovery_20261028/delivery/results/replay_v2'/source['name']
        if not previous.exists():previous=PROJECT/'counting_recovery_20261028/delivery/results/full640_confirmation'/source['name']
        raw=defaultdict(list)
        for r in read(previous/'pretracker_boxes.csv'):raw[int(r['frame'])].append(r)
        rows=normalized(read(folder/'source_warmup_tracks.csv')+read(folder/'source_tracks.csv'));positions=defaultdict(dict)
        for r in rows:
            assert .34<(r['x1']+r['x2'])/5120<.75 and r['axis_position']==(r['y1']+r['y2'])/2880
            positions[r['source_frame']][r['track_id']]=r['axis_position']
        track_rows+=len(rows);all_ids=defaultdict(set)
        for r in read(folder/'all_posttracker_boxes.csv'):
            if r['track_id']!='':all_ids[int(r['source_frame'])].add(int(r['track_id']))
        obs=load(folder/'observations.json');assert [r['source_frame'] for r in obs]==list(range(0,10874,5))
        expanded={f:dict(row) for f,row in positions.items()};known=set();last_tentative={}
        for r in obs:
            f=r['source_frame'];active=set(r['confirmed_IDs']);tentative={int(k):v for k,v in r['tentative_positions'].items()}
            assert {int(k):v for k,v in r['confirmed_positions'].items()}==positions.get(f,{}) and active==all_ids.get(f,set())
            admitted=[]
            for tid in sorted(active-known):
                if tid in last_tentative:
                    y=last_tentative[tid];expanded.setdefault(f-5,{})[tid]=y
                    admitted.append({'track_id':tid,'observation_time_s':(f-5)/25,'confirmation_time_s':f/25,'axis_position':y,'observation_source_frame':f-5,'confirmation_source_frame':f})
            assert r['accepted_history']==admitted;known.update(active);last_tentative=tentative
        ordinary=counter(positions);handoff=counter(expanded)
        assert ordinary==load(folder/'confirmed_only_events.json') and handoff==load(folder/'handoff_events.json')
        assert c['predicted_down']==sum(e['direction']=='A->B' for e in handoff) and c['predicted_up']==sum(e['direction']=='B->A' for e in handoff)
        if c['variant']=='installed_baseline':
            assert normalized(read(folder/'source_tracks.csv'))==normalized(read(previous/'source_tracks.csv'))
            assert normalized(read(folder/'source_warmup_tracks.csv'))==normalized(read(previous/'source_warmup_tracks.csv'))
            assert ordinary==load(previous/'source_events.json')
            assert handoff==load(PROJECT/f'confirmation_handoff_20261028/delivery/results/replay_v2/seed{c["seed"]}/handoff_events.json')
        n_matches=0;ds=load(folder/'secondstage_decisions.json');assert len(ds)==c['nonempty_secondstage_decisions']
        for d in ds:
            decisions+=1;f=d['source_frame'];low=[r for r in raw[f] if .1<float(r['confidence'])<.25]
            assert len(low)==len(d['low_detections']) and not set(d['eligible_IDs'])&set(d['lost_IDs_excluded'])
            for j,box in enumerate(d['low_detections']):
                assert box['stage_local_index']==j and box['confidence']==float(low[j]['confidence'])
                assert np.allclose(box['xyxy'],[float(low[j][k]) for k in ['x1','y1','x2','y2']],atol=.0005,rtol=0)
            for i,a in enumerate(d['eligible_xyxy']):
                for j,b in enumerate(d['low_detections']):
                    overlap=iou(a,b['xyxy']);cost=1-overlap*b['confidence'] if d['score_fusion_in_secondstage'] else 1-overlap
                    err=max(abs(overlap-d['IoUs'][i][j]),abs(cost-d['costs'][i][j]));maxerror=max(maxerror,err)
                    assert err<1e-6;cost_entries+=1
            pairs=d['applied_pairs'];assert len({r['row_index'] for r in pairs})==len(pairs)==len({r['low_stage_index'] for r in pairs})
            for pair in pairs:
                i,j=pair['row_index'],pair['low_stage_index'];assert pair['track_ID']==d['eligible_IDs'][i]
                assert pair['confidence']==d['low_detections'][j]['confidence'] and pair['cost']==d['costs'][i][j] and pair['cost']<=.5
            if c['variant']=='installed_baseline':assert not pairs and d['score_fusion_in_secondstage']
            else:assert not d['score_fusion_in_secondstage']
            n_matches+=len(pairs)
        assert n_matches==c['applied_low_stage_matches_all_history'];matches+=n_matches
        condition_records.append({'condition':c['name'],'independent_event_paths':2,'handoff_events':len(handoff),'low_matches':n_matches})
    comparisons=[]
    for seed in [26,27,28]:
        a=load(dest/f'results/installed_baseline_seed{seed}/handoff_events.json');b=load(dest/f'results/secondstage_iou_seed{seed}/handoff_events.json')
        without_ID=lambda rows:[{k:v for k,v in e.items() if k!='track_id'} for e in rows]
        comparisons.append({'seed':seed,'baseline_events':len(a),'candidate_events':len(b),
            'event_times_and_directions_exact_without_ID':without_ID(a)==without_ID(b),'full_event_records_exact':a==b})
    out={'status':'ALL71_DELIVERY_FILES_TWELVE_EVENT_PATHS_AND_SECONDSTAGE_COSTS_VERIFIED',
      'protocol_sha256':sha(ROOT/'protocol/secondstage_v1.json'),'summary_sha256':sha(dest/'results/summary.json'),
      'candidate_module_sha256':sha(ROOT/'tools/secondstage_tracker.py'),'files':71,'conditions':condition_records,
      'event_paths':12,'full_baseline_regressions':3,'trace_updates':6*2175,'ROI_track_rows_with_history':track_rows,
      'secondstage_nonempty_decisions':decisions,'secondstage_cost_entries':cost_entries,'maximum_cost_or_IoU_difference':maxerror,
      'applied_low_stage_matches_all_history':matches,'comparisons':comparisons,
      'single_score_fusion_block_AST_change_verified':True,'firststage_and_lost_eligibility_unchanged':True,
      'independent_source_accuracy':None,'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    target.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
if __name__=='__main__':main()
