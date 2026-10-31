"""Reference-assisted interventions for error attribution, not deployed accuracy."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,sys
import numpy as np
from scipy.optimize import linear_sum_assignment
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026')
PH=ROOT/'phase3_diagnosis';OLD=ROOT/'phase2';OUT=PH/'results/layers'
OUT.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(OLD/'tools'))
from zone_counter import ZoneCounter
from event_metrics import evaluate_events

rawgt=np.loadtxt(OLD/'data/mendeley_counting/extracted/Ground Truth/gt.txt',delimiter=',',ndmin=2)
gt=defaultdict(list)
for r in rawgt:
    gt[int(r[0])].append({'track_id':int(r[1]),'x1':float(r[2]),'y1':float(r[3]),
                        'x2':float(r[2]+r[4]),'y2':float(r[3]+r[5])})
reference=json.loads((OLD/'results/author_gt_audit/summary.json').read_text())['events']
target_ids=[r['track_id'] for r in reference]

def read_boxes(path):
    rows=defaultdict(list)
    for r in csv.DictReader(path.open()):
        r={k:(None if not v else int(v)) if k in ['frame','track_id'] else float(v) for k,v in r.items()}
        rows[r['frame']].append(r)
    return rows

def positions(rows, idkey='track_id'):
    found={}
    for r in rows:
        if r.get(idkey) is None:continue
        cx=(r['x1']+r['x2'])/3840;cy=(r['y1']+r['y2'])/2160
        if .1<cy<.95:found[r[idkey]]=cx
    return found

def event_replay(frames):
    counter=ZoneCounter();events=[]
    for frame in range(479):
        for e in counter.update(frame/30,frames.get(frame,{})):
            e['frame']=frame;events.append(e)
    return events

def assignment(a,b,threshold):
    if not a or not b:return []
    def box(r):return [max(0,r['x1']),max(0,r['y1']),min(1920,r['x2']),min(1080,r['y2'])]
    aa=np.array([box(r) for r in a]);bb=np.array([box(r) for r in b])
    lt=np.maximum(aa[:,None,:2],bb[None,:,:2]);rb=np.minimum(aa[:,None,2:],bb[None,:,2:])
    inter=np.maximum(0,rb-lt).prod(2)
    iou=inter/np.maximum((aa[:,2:]-aa[:,:2]).prod(1)[:,None]+(bb[:,2:]-bb[:,:2]).prod(1)[None,:]-inter,1e-10)
    ii,jj=linear_sum_assignment(np.where(iou>=threshold,-100000-iou,0))
    return [(int(i),int(j),float(iou[i,j])) for i,j in zip(ii,jj) if iou[i,j]>=threshold]

control=event_replay({f:positions(rows) for f,rows in gt.items()})
assert control==reference
results=[];assignments=[];per_reference=[]
for model in ['generic','pilot']:
    raw=read_boxes(PH/f'results/capture/{model}/raw_detector_boxes.csv')
    post=read_boxes(PH/f'results/capture/{model}/post_tracker_boxes.csv')
    actual=event_replay({f:positions(rows) for f,rows in post.items()})
    capture=json.loads((PH/f'results/capture/{model}/summary.json').read_text())
    assert actual==capture['events']
    results.append({'model':model,'condition':'actual_pipeline','association_iou':None,
                    'events':actual,'metrics':evaluate_events(reference,actual,2.),'reference_assisted':False})
    for threshold in [.5,.3]:
        frames={name:defaultdict(dict) for name in ['raw_boxes_reference_ids','post_boxes_reference_ids','reference_boxes_tracker_ids']}
        log=[]
        for f in range(479):
            for kind,prediction in [('raw',raw[f]),('post',post[f])]:
                for i,j,iou in assignment(gt[f],prediction,threshold):
                    g,p=gt[f][i],prediction[j]
                    gp=(g['x1']+g['x2'])/3840;pp=(p['x1']+p['x2'])/3840
                    cy=(p['y1']+p['y2'])/2160;gcy=(g['y1']+g['y2'])/2160
                    name='raw_boxes_reference_ids' if kind=='raw' else 'post_boxes_reference_ids'
                    if .1<cy<.95:frames[name][f][g['track_id']]=pp
                    if kind=='post' and p.get('track_id') is not None and .1<gcy<.95:
                        frames['reference_boxes_tracker_ids'][f][p['track_id']]=gp
                    row={'model':model,'association_iou':threshold,'kind':kind,'frame':f,
                         'reference_id':g['track_id'],'tracker_id':p.get('track_id'),
                         'iou':iou,'reference_cx':gp,'prediction_cx':pp,'confidence':p['confidence']}
                    log.append(row);assignments.append(row)
        for name,values in frames.items():
            events=event_replay(values)
            results.append({'model':model,'condition':name,'association_iou':threshold,
                            'events':events,'metrics':evaluate_events(reference,events,2.),'reference_assisted':True})
        for rid in target_ids:
            details=[r for r in log if r['reference_id']==rid]
            predids=sorted({r['tracker_id'] for r in details if r['kind']=='post' and r['tracker_id'] is not None})
            outcome={'model':model,'reference_id':rid,'association_iou':threshold,
                     'reference_event_frame':next(r['frame'] for r in reference if r['track_id']==rid),
                     'reference_visible_frames':sum(any(g['track_id']==rid for g in rows) for rows in gt.values()),
                     'matched_raw_frames':sum(r['kind']=='raw' for r in details),
                     'matched_post_frames':sum(r['kind']=='post' for r in details),
                     'associated_tracker_ids':predids}
            for condition in ['raw_boxes_reference_ids','post_boxes_reference_ids']:
                outcome[condition+'_events']=[r for r in event_replay(frames[condition]) if r['track_id']==rid]
            per_reference.append(outcome)
        if threshold==.5:
            fig,axes=plt.subplots(6,1,figsize=(13,14),layout='constrained')
            for ax,rid in zip(axes,target_ids):
                gpoints=[(f,(g['x1']+g['x2'])/3840) for f,rows in gt.items() for g in rows if g['track_id']==rid]
                ax.plot(*zip(*gpoints),color='black',linewidth=1.3,label='publisher centre')
                d=[r for r in log if r['reference_id']==rid and r['kind']=='raw']
                if d:ax.scatter([r['frame'] for r in d],[r['prediction_cx'] for r in d],s=5,c='red',alpha=.35,label='raw detector centre')
                d=[r for r in log if r['reference_id']==rid and r['kind']=='post' and r['tracker_id'] is not None]
                if d:ax.scatter([r['frame'] for r in d],[r['prediction_cx'] for r in d],s=12,c=[r['tracker_id'] for r in d],cmap='tab20',label='post tracker; colours=track ID')
                for y in [.4,.6]:ax.axhline(y,c='orange',ls='--',lw=.9)
                ax.set(title=f'{model}: publisher ID {rid}',ylabel='normalised x',ylim=(-.02,1.02))
            axes[0].legend(loc='upper right',fontsize=7);axes[-1].set_xlabel('Original frame (30 fps)')
            fig.savefig(OUT/f'{model}_reference_centres.png',dpi=140);plt.close(fig)
for model in ['generic','pilot']:
    results.append({'model':model,'condition':'reference_boxes_reference_ids','association_iou':None,
                    'events':control,'metrics':evaluate_events(reference,control,2.),'reference_assisted':True})
summary={'job_id':os.environ['SLURM_JOB_ID'],'reference_events':reference,'interventions':results,
         'per_reference':per_reference,'interpretation':'Reference-assisted diagnostic controls only; actual_pipeline is the preserved reference-free algorithm, not proof of board deployment. Temporal F1 may associate neighbouring events; reference-ID details are retained for intervention interpretation.',
         'inputs_sha256':{str(p.relative_to(PH)):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((PH/'results/capture').rglob('*.csv'))}}
(OUT/'diagnostic_summary.json').write_text(json.dumps(summary,indent=2))
for name,rows in [('frame_assignments.csv',assignments),('per_reference.csv',per_reference)]:
    with (OUT/name).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
flat=[{'model':r['model'],'condition':r['condition'],'association_iou':r['association_iou'],
       'reference_assisted':r['reference_assisted'],**{k:r['metrics'][k] for k in ['reference_events','predicted_events','TP','FP','FN','f1']}} for r in results]
with (OUT/'interventions.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
print(json.dumps({'job_id':os.environ['SLURM_JOB_ID'],'interventions':flat},indent=2),flush=True)
