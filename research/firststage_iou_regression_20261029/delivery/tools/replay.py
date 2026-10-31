"""Nine fixed caches, an exact-baseline gate, then nine one-factor controls."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,os,socket,sys,tarfile
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import YAML,IterableSimpleNamespace
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/firststage_iou_regression_20261029')
sys.path.insert(0,str(ROOT/'input'))
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
from firststage_tracker import FirstStagePureIoUTracker
from event_metrics import evaluate_events
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    assert not p.exists(),p
    p.write_text(json.dumps(value,indent=2)+'\n')
def read(p):
    with Path(p).open(newline='') as f:return list(csv.DictReader(f))
def norm(rows,framekey):
    return [{k:None if v in ['',None] else int(v) if k in [framekey,'track_id'] else float(v) for k,v in r.items()} for r in rows]
def json_normal(value):return json.loads(json.dumps(value))
def canonical_event(event,source_key):
    return {**{k:v for k,v in event.items() if k!=source_key},'frame0':event[source_key]}
def csvsave(path,rows,fields):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def bare_acceptance(row):return {k:row[k] for k in ['track_id','observation_time_s','confirmation_time_s','axis_position']}
def canonical_prior_obs(rows,scene,fps):
    result=[]
    for row in rows:
        frame=row['frame0'] if scene=='new_long' else row['source_frame'] if scene=='original_clip' else row['frame']
        active=row['confirmed_ids'] if scene=='original_clip' else row['confirmed_IDs']
        result.append({'frame0':frame,'time_s':frame/fps,'confirmed_positions':row['confirmed_positions'],
                       'confirmed_IDs':active,'tentative_positions':row['tentative_positions'],
                       'accepted_history':[bare_acceptance(x) for x in row['accepted_history']]})
    return result
def scope_events(events,spec):
    return [e for e in events if any(w['start_frame0']<=e['frame0']<w['end_frame0_exclusive'] for w in spec['windows'])]

def verify_baseline(spec,post,tracks,observations,baseline,events):
    scene=spec['scene'];folder=Path(spec['prior_remote_folder']);checks={}
    assert json_normal(observations)==canonical_prior_obs(load(folder/'observations.json'),scene,spec['fps'])
    checks['all_observations_tentative_and_acceptance_history_exact']=True
    if scene=='new_long':
        assert post==norm(read(folder/'post_tracker_boxes.csv'),'frame0')
        assert tracks==norm(read(folder/'tracks.csv'),'frame0')
        assert baseline==load(folder/'confirmed_only_events_all_history.json') and events==load(folder/'handoff_events_all_history.json')
        checks['all_full_image_and_ROI_boxes_exact']=True
    elif scene=='original_clip':
        old=norm(read(folder/'source_tracks.csv'),'source_frame')+norm(read(folder/'source_warmup_tracks.csv'),'source_frame')
        old=sorted(old,key=lambda r:r['source_frame'])
        expected=[{('frame0' if k=='source_frame' else k):v for k,v in r.items()} for r in old]
        assert tracks==expected
        assert scope_events(baseline,spec)==[canonical_event(e,'source_frame') for e in load(folder/'baseline_events.json')]
        assert scope_events(events,spec)==[canonical_event(e,'source_frame') for e in load(folder/'handoff_events.json')]
        checks['all_ROI_boxes_history_exact_full_image_IDs_exact']=True
        checks['all_nonROI_box_coordinates_had_prior_reference']=False
    else:
        cache=Path(spec['raw_path']).parent
        expected=[{('frame0' if k=='frame' else k):v for k,v in r.items()} for r in norm(read(cache/'post_tracker_boxes.csv'),'frame')]
        assert post==expected
        expected=[{('frame0' if k=='frame' else k):v for k,v in r.items()} for r in norm(read(cache/'tracks.csv'),'frame')]
        assert tracks==expected
        assert baseline==[canonical_event(e,'frame') for e in load(folder/'confirmed_only_events.json')]
        assert events==[canonical_event(e,'frame') for e in load(folder/'handoff_events.json')]
        checks['all_full_image_and_ROI_boxes_exact']=True
    checks['both_counter_event_paths_exact']=True
    return checks

def pair_iou(a,b):
    x=max(0.,min(a['x2'],b['x2'])-max(a['x1'],b['x1']))
    y=max(0.,min(a['y2'],b['y2'])-max(a['y1'],b['y1']))
    aa=max(0.,a['x2']-a['x1'])*max(0.,a['y2']-a['y1']);bb=max(0.,b['x2']-b['x1'])*max(0.,b['y2']-b['y1'])
    return x*y/(aa+bb-x*y+1e-7)

def run(spec,p,names,variant):
    name=spec['name']+'__'+variant;dest=ROOT/'results'/name;dest.mkdir(exist_ok=False)
    raw=defaultdict(list);cow=next(k for k,v in names.items() if v=='cow')
    for r in read(spec['raw_path']):
        raw[int(r[spec['raw_frame_key']])].append([*[float(r[k]) for k in ['x1','y1','x2','y2']],float(r['confidence']),cow])
    cfg=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml')
    tracker=(BYTETracker if variant=='original_fused' else FirstStagePureIoUTracker)(IterableSimpleNamespace(**cfg))
    base=ZoneCounter(**p['counter']);counter=ConfirmationHandoffCounter(**p['counter'])
    H,W=spec['height'],spec['width'];fps=spec['fps'];low,high=spec['perpendicular_ROI']
    image=np.zeros((H,W,3),np.uint8);post=[];tracks=[];observations=[];baseline=[];events=[];overlaps=[]
    for frame in range(0,spec['history_end_frame0_exclusive'],spec['stride']):
        time_s=frame/fps;arr=np.asarray(raw[frame],np.float32).reshape(-1,6)
        result=Results(orig_img=image,path='native_cached',names=names,boxes=torch.from_numpy(arr))
        output=tracker.update(result.boxes.cpu().numpy(),result.orig_img,feats=None)
        if len(output):result=result[output[:,-1].astype(int)];result.update(boxes=torch.as_tensor(output[:,:-1]))
        b=result.boxes;IDs=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b)
        positions={};active={tid for tid in IDs if tid is not None};tentative={};selected=[]
        for box,confidence,tid in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),IDs):
            x1,y1,x2,y2=box;cx=(x1+x2)/(2*W);cy=(y1+y2)/(2*H)
            row=dict(zip(['frame0','time_s','track_id','confidence','x1','y1','x2','y2'],[frame,time_s,tid,confidence,*box]));post.append(row)
            cross=cx if spec['axis']=='y' else cy;axis=cy if spec['axis']=='y' else cx
            if tid is None or not low<cross<high:continue
            positions[tid]=axis;selected.append(row)
            if spec['axis']=='y':tracks.append({**row,'axis_position':axis})
            else:tracks.append({'frame0':frame,'time_s':time_s,'track_id':tid,'axis_position':axis,'cy_norm':cy})
        for t in tracker.tracked_stracks:
            if t.is_activated:continue
            x1,y1,x2,y2=np.asarray(t.xyxy,np.float32).astype(float)
            cx,cy=(x1+x2)/(2*W),(y1+y2)/(2*H)
            if low<(cx if spec['axis']=='y' else cy)<high:tentative[int(t.track_id)]=cy if spec['axis']=='y' else cx
        for generated,dest_events in [(base.update(time_s,positions),baseline),(counter.update(time_s,positions,tentative,active),events)]:
            for e in generated:e['frame0']=frame;dest_events.append(e)
        observations.append({'frame0':frame,'time_s':time_s,'confirmed_positions':positions,'confirmed_IDs':sorted(active),
                             'tentative_positions':tentative,'accepted_history':counter.last_acceptances})
        for i,a in enumerate(selected):
            for bb in selected[i+1:]:
                overlap=pair_iou(a,bb)
                if overlap>=p['fixed_overlap_candidate_IoU']:
                    overlaps.append({'frame0':frame,'IDa':a['track_id'],'IDb':bb['track_id'],'IoU':overlap,
                                     'box_a':[a[k] for k in ['x1','y1','x2','y2']],'box_b':[bb[k] for k in ['x1','y1','x2','y2']]})
    checks=verify_baseline(spec,post,tracks,observations,baseline,events) if variant=='original_fused' else None
    fields=['frame0','time_s','track_id','confidence','x1','y1','x2','y2']
    csvsave(dest/'post_tracker_boxes.csv',post,fields)
    csvsave(dest/'tracks.csv',tracks,fields+['axis_position'] if spec['axis']=='y' else ['frame0','time_s','track_id','axis_position','cy_norm'])
    for file,value in [('observations.json',observations),('confirmed_only_events_all_history.json',baseline),('handoff_events_all_history.json',events),('ROI_overlap_candidates.json',overlaps)]:save(dest/file,value)
    windows=[]
    for window in spec['windows']:
        a,bb=window['start_frame0'],window['end_frame0_exclusive']
        for kind,all_events in [('confirmed_only',baseline),('confirmation_handoff',events)]:
            selected=[e for e in all_events if a<=e['frame0']<bb]
            record={'window':window['name'],'counter':kind,'down':sum(e['direction']=='A->B' for e in selected),
                    'up':sum(e['direction']=='B->A' for e in selected),'events':selected,'formal_event_metrics':None}
            if spec['formal_event_scoring_allowed']:
                record['formal_event_metrics']=evaluate_events(spec['reference_events'],selected,spec['event_tolerance_s'])
            if spec['scene']=='original_clip':record['human_down_total']=12;record['absolute_down_total_error']=abs(record['down']-12)
            windows.append(record)
    record={'name':name,'source':spec['name'],'scene':spec['scene'],'model':spec['model'],'variant':variant,
            'checkpoint_sha256':spec['weights']['sha256'],'observation_ticks':len(observations),'post_tracker_rows':len(post),'ROI_rows':len(tracks),
            'all_history_down':sum(e['direction']=='A->B' for e in events),'all_history_up':sum(e['direction']=='B->A' for e in events),
            'baseline_checks':checks,'window_counters':windows,'ROI_overlap_pairs_by_tick':len(overlaps),
            'ROI_ticks_with_overlap_candidate':len({r['frame0'] for r in overlaps}),
            'effective_tracker_config':cfg,'reference_authority':spec['reference_authority'],'new_detector_forwards':0,'new_training_updates':0}
    save(dest/'summary.json',record)
    print(json.dumps({k:v for k,v in record.items() if k not in ['effective_tracker_config','window_counters']}),flush=True)
    return record

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(2)
    p=load(ROOT/'protocol/regression_v1.json');assert ultralytics.__version__=='8.4.63'
    mapping={'installed_track.py':'trackers/track.py','installed_byte_tracker.py':'trackers/byte_tracker.py','installed_bytetrack.yaml':'cfg/trackers/bytetrack.yaml'}
    for r in p['installed_source']:assert sha(Path(ultralytics.__path__[0])/mapping[r['file']])==r['sha256']
    assert sha(Path(ultralytics.__path__[0])/'trackers/utils/matching.py')==p['matching_source_sha256']
    for name,digest in p['input_modules'].items():assert sha(ROOT/'input'/name)==digest
    assert all(s['reference_events']==load(ROOT/'input/publisher_event_summary.json')['events'] for s in p['sources'] if s['scene']=='toros_used_reverse')
    names={}
    for s in p['sources']:
        for f in s['files']:assert Path(f['path']).stat().st_size==f['bytes'] and sha(f['path'])==f['sha256']
        assert sha(s['weights']['path'])==s['weights']['sha256']
        if s['weights']['sha256'] not in names:
            model=YOLO(s['weights']['path']);names[s['weights']['sha256']]=model.names;del model
    (ROOT/'results').mkdir(exist_ok=False)
    originals=[run(s,p,names[s['weights']['sha256']],'original_fused') for s in p['sources']]
    assert len(originals)==9 and all(r['baseline_checks']['both_counter_event_paths_exact'] for r in originals)
    save(ROOT/'results/baseline_gate.json',{'status':'NINE_FIXED_CACHES_ORIGINAL_OUTPUTS_EXACT_BEFORE_ANY_CANDIDATE',
         'conditions':[r['name'] for r in originals],'protocol_sha256':sha(ROOT/'protocol/regression_v1.json')})
    controls=[run(s,p,names[s['weights']['sha256']],'firststage_pure_IoU') for s in p['sources']]
    paired=[]
    for a,b in zip(originals,controls):
        diffs=[]
        for wa,wb in zip(a['window_counters'],b['window_counters']):
            assert wa['window']==wb['window'] and wa['counter']==wb['counter']
            signature=lambda w:Counter((e['frame0'],e['direction']) for e in w['events'])
            old,new=signature(wa),signature(wb)
            diffs.append({'window':wa['window'],'counter':wa['counter'],'before_down_up':[wa['down'],wa['up']],
                          'after_down_up':[wb['down'],wb['up']],
                          'time_direction_multiset_added':list((new-old).elements()),'time_direction_multiset_removed':list((old-new).elements()),
                          'original_metrics':wa['formal_event_metrics'],'candidate_metrics':wb['formal_event_metrics']})
        paired.append({'source':a['source'],'scene':a['scene'],'model':a['model'],'window_differences':diffs,
                       'ROI_overlap_ticks_before_after':[a['ROI_ticks_with_overlap_candidate'],b['ROI_ticks_with_overlap_candidate']],
                       'ID_numbers_not_correspondences_between_variants':True})
    summary={'status':'NINE_EXACT_BASELINES_AND_NINE_FIRSTSTAGE_ONLY_IOU_CONTROLS_COMPLETE',
             'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/regression_v1.json'),
             'conditions':originals+controls,'paired_results':paired,'full_tracker_runs':18,'counter_paths':36,
             'total_tracker_updates':sum(r['observation_ticks'] for r in originals+controls),
             'candidate_adopted':False,'new_independent_test':False,'new_detector_forwards':0,'new_training_updates':0,
             'new_long_reference_scores_computed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    assert summary['total_tracker_updates']==p['expected_full_tracker_updates']==31166
    save(ROOT/'results/summary.json',summary)
    files=[]
    for folder in ['results','input','protocol','tools']:
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file():files.append({'file':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)})
    save(ROOT/'delivery_manifest.json',{'files':files});archive=ROOT/'regression_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for r in files:tf.add(ROOT/r['file'],arcname=r['file'])
        tf.add(ROOT/'delivery_manifest.json',arcname='delivery_manifest.json')
    print(json.dumps({'status':summary['status'],'files':len(files)+1,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive)}),flush=True)
if __name__=='__main__':main()
