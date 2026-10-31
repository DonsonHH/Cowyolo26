"""Replay unchanged detector boxes through reference-free ByteTrack variants."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,sys,time
import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');PH=ROOT/'phase4_tracker';OLD=ROOT/'phase2';CAP=ROOT/'phase3_diagnosis/results/capture'
(PH/'cache/ultralytics/Ultralytics').mkdir(parents=True,exist_ok=True)
os.environ['YOLO_CONFIG_DIR']=str(PH/'cache/ultralytics');os.environ['YOLO_AUTOINSTALL']='false'
import ultralytics
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.engine.results import Boxes
from ultralytics.utils import YAML,IterableSimpleNamespace
sys.path.insert(0,str(OLD/'tools'))
from zone_counter import ZoneCounter
from event_metrics import evaluate_events

OUT=PH/'results/replay';OUT.mkdir(parents=True,exist_ok=False)
protocol=json.loads((PH/'protocol/tracker_replay_v1.json').read_text())
config_path=Path(ultralytics.__file__).parent/'cfg/trackers/bytetrack.yaml'
config=YAML.load(config_path)
(OUT/'installed_bytetrack.yaml').write_text(config_path.read_text())
frozen=json.loads((CAP/'summary.json').read_text())
reference=json.loads((OLD/'results/author_gt_audit/summary.json').read_text())['events']
gt=defaultdict(list)
for r in np.loadtxt(OLD/'data/mendeley_counting/extracted/Ground Truth/gt.txt',delimiter=',',ndmin=2):gt[int(r[0])].append(r)

def ids_at_frame(frame,boxes):
    rows=gt[frame]
    if not rows or not len(boxes):return {}
    a=np.array([[max(0,r[2]),max(0,r[3]),min(1920,r[2]+r[4]),min(1080,r[3]+r[5])] for r in rows]);b=boxes[:,:4]
    lt=np.maximum(a[:,None,:2],b[None,:,:2]);rb=np.minimum(a[:,None,2:],b[None,:,2:]);inter=np.maximum(rb-lt,0).prod(2)
    iou=inter/np.maximum((a[:,2:]-a[:,:2]).prod(1)[:,None]+(b[:,2:]-b[:,:2]).prod(1)[None,:]-inter,1e-12)
    ii,jj=linear_sum_assignment(np.where(iou>=.5,-100000-iou,0))
    return {int(boxes[j,4]):int(rows[i][1]) for i,j in zip(ii,jj) if iou[i,j]>=.5}

all_runs=[];started=time.perf_counter()
for model in ['generic','pilot']:
    path=CAP/model/'raw_detector_boxes.csv';raw=defaultdict(list)
    for r in csv.DictReader(path.open()):raw[int(r['frame'])].append([float(r[k]) for k in ['x1','y1','x2','y2','confidence']]+[19. if model=='generic' else 0.])
    source_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    for case in protocol['controls']:
        effective={**config,**case['changes']};tracker=BYTETracker(args=IterableSimpleNamespace(**effective))
        counter=ZoneCounter();events=[];track_rows=[];geom_event_ids=[];hist=defaultdict(list)
        dest=OUT/model/case['name'];dest.mkdir(parents=True)
        for frame in range(479):
            data=np.asarray(raw[frame],dtype=np.float32).reshape(-1,6)
            output=tracker.update(Boxes(data,(1080,1920)).numpy())
            if not len(output):output=np.empty((0,8),dtype=np.float32)
            positions={};mapping=ids_at_frame(frame,output)
            for b in output:
                x1,y1,x2,y2,tid,confidence,cls,idx=map(float,b)
                cx=(x1+x2)/3840;cy=(y1+y2)/2160;tid=int(tid)
                if .1<cy<.95:
                    positions[tid]=cx
                    track_rows.append({'frame':frame,'time_s':frame/30,'track_id':tid,'axis_position':cx,'cy_norm':cy})
                if tid in mapping:hist[mapping[tid]].append((frame,tid))
            for e in counter.update(frame/30,positions):
                e['frame']=frame;events.append(e);geom_event_ids.append(mapping.get(e['track_id']))
        if case['name']=='baseline':
            assert events==next(r for r in frozen if r['model']==model)['events'],'Standalone replay failed frozen-event equivalence'
        metrics=evaluate_events(reference,events,2.)
        support=[]
        for p in metrics['pairs']:
            i,j=p['reference_index'],p['prediction_index']
            support.append({'reference_index':i,'prediction_index':j,'expected_reference_id':reference[i]['track_id'],
                            'mapped_reference_id_at_prediction':geom_event_ids[j],
                            'reference_id_supported':reference[i]['track_id']==geom_event_ids[j]})
        changes=sum(sum(t1!=t0 and f1-f0<=30 for (f0,t0),(f1,t1) in zip(rows,rows[1:])) for rows in hist.values())
        row={'model':model,'variant':case['name'],'changes':case['changes'],'effective_config':effective,
             'job_id':os.environ['SLURM_JOB_ID'],'source_raw_boxes_sha256':source_sha,'processed_frames':479,
             'events':events,'event_metrics':metrics,'geometric_event_reference_ids':geom_event_ids,
             'matched_event_reference_support':support,'diagnostic_matched_id_changes':int(changes),
             'baseline_equivalent':case['name']=='baseline','scope':protocol['scope']}
        (dest/'summary.json').write_text(json.dumps(row,indent=2))
        for filename,rows,fields in [('events.csv',events,['time_s','track_id','direction','frame']),('tracks.csv',track_rows,['frame','time_s','track_id','axis_position','cy_norm'])]:
            with (dest/filename).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        all_runs.append(row)
        print(json.dumps({'model':model,'variant':case['name'],'TP':metrics['TP'],'FP':metrics['FP'],'FN':metrics['FN'],'id_supported_pairs':sum(r['reference_id_supported'] for r in support),'matched_pairs':len(support),'diagnostic_matched_id_changes':changes}),flush=True)
summary={'job_id':os.environ['SLURM_JOB_ID'],'ultralytics_version':ultralytics.__version__,'runs':all_runs,'elapsed_s':time.perf_counter()-started,'protocol':protocol}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
