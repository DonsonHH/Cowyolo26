"""Independent exhaustive associations and grouped-region event recomputation.

Uses only stdlib, no server counter/scorer, numpy or scipy.
"""
from pathlib import Path
from collections import defaultdict
from functools import lru_cache
import csv,hashlib,json

TOP=Path(__file__).resolve().parents[1]
ROOT=TOP/'delivery'
OLD=TOP.parent/'counting_eval_20261026'
summary=json.loads((ROOT/'results/layers/diagnostic_summary.json').read_text())
gt=defaultdict(list)
for row in csv.reader((OLD/'delivery/counting_evaluation/annotations/publisher_gt_original.txt').open()):
    r=list(map(float,row));gt[int(r[0])].append(dict(id=int(r[1]),box=[r[2],r[3],r[2]+r[4],r[3]+r[5]]))

def load(path):
    frames=defaultdict(list)
    for r in csv.DictReader(path.open()):
        frames[int(r['frame'])].append({'id':int(r['track_id']) if r.get('track_id') else None,
                                     'box':[float(r[k]) for k in ['x1','y1','x2','y2']]})
    return frames

def centre(box):return (box[0]+box[2])/3840,(box[1]+box[3])/2160

def observed(frames):
    return {f:{r['id']:centre(r['box'])[0] for r in rows if r['id'] is not None and .1<centre(r['box'])[1]<.95} for f,rows in frames.items()}

def events(frames):
    tracks=defaultdict(list)
    for f,items in frames.items():
        for identity,x in items.items():
            if 0<=x<=1:tracks[identity].append((f,'A' if x<.4 else 'B' if x>.6 else 'M'))
    result=[]
    for identity,rows in tracks.items():
        groups=[]
        for f,z in sorted(rows):
            if groups and groups[-1][-1][0]+1==f and groups[-1][0][1]==z:groups[-1].append((f,z))
            else:groups.append([(f,z)])
        origin=None;last=None
        for run in groups:
            if last is not None and run[0][0]-last>60:origin=None
            last=run[-1][0]
            if run[0][1]=='M' or len(run)<3:continue
            z=run[0][1]
            if origin is not None and z!=origin:
                f=run[2][0];result.append({'track_id':identity,'frame':f,'time_s':f/30,'direction':origin+'->'+z})
            origin=z
    return sorted(result,key=lambda r:(r['frame'],r['track_id']))

def iou(a,b):
    def clip(x):return [max(0,x[0]),max(0,x[1]),min(1920,x[2]),min(1080,x[3])]
    a,b=clip(a),clip(b)
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=max(0,a[2]-a[0])*max(0,a[3]-a[1])+max(0,b[2]-b[0])*max(0,b[3]-b[1])-inter
    return inter/max(union,1e-10)

def associate(gs,ps,threshold):
    weights=[[iou(g['box'],p['box']) for p in ps] for g in gs]
    @lru_cache(None)
    def search(i,used):
        if i==len(gs):return 0,0.,()
        best=search(i+1,used)
        for j in range(len(ps)):
            if used&(1<<j) or weights[i][j]<threshold:continue
            n,c,pairs=search(i+1,used|(1<<j));candidate=(n+1,c+weights[i][j],((i,j),)+pairs)
            if candidate[:2]>best[:2]:best=candidate
        return best
    return search(0,0)[2]

reference=events(observed(gt))
assert reference==summary['reference_events']
verified=[];hashes=[]
for model in ['epoch20_seed26','epoch20_seed27','epoch20_seed28']:
    frames={}
    for name,file in [('raw','raw_detector_boxes.csv'),('post','post_tracker_boxes.csv')]:
        path=ROOT/f'results/capture/{model}/{file}'
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==summary['inputs_sha256'][f'results/capture/{model}/{file}']
        hashes.append({'path':str(path.relative_to(ROOT)),'sha256':digest})
        frames[name]=load(path)
    cases={('actual_pipeline',None):events(observed(frames['post'])),
           ('reference_boxes_reference_ids',None):reference}
    for threshold in [.5,.3]:
        values={name:defaultdict(dict) for name in ['raw_boxes_reference_ids','post_boxes_reference_ids','reference_boxes_tracker_ids']}
        for f in range(479):
            for kind in ['raw','post']:
                for i,j in associate(gt[f],frames[kind][f],threshold):
                    g,p=gt[f][i],frames[kind][f][j];gx,gy=centre(g['box']);px,py=centre(p['box'])
                    if .1<py<.95:values['raw_boxes_reference_ids' if kind=='raw' else 'post_boxes_reference_ids'][f][g['id']]=px
                    if kind=='post' and p['id'] is not None and .1<gy<.95:values['reference_boxes_tracker_ids'][f][p['id']]=gx
        for name,points in values.items():cases[(name,threshold)]=events(points)
    for (name,threshold),found in cases.items():
        expected=next(r for r in summary['interventions'] if r['model']==model and r['condition']==name and r['association_iou']==threshold)
        assert found==sorted(expected['events'],key=lambda r:(r['frame'],r['track_id'])),(model,name,threshold)
        verified.append({'model':model,'condition':name,'association_iou':threshold,'events':len(found),'exact_event_equality':True})
result={'status':'PASS','implementation':'stdlib exhaustive per-frame IoU assignment and independent grouped-region visits',
        'verified_capture_files':hashes,'verified_conditions':verified,
        'scope':'Reference-assisted diagnostic arithmetic, not new generalisation or board performance'}
(TOP/'results/independent_diagnosis_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'status':result['status'],'capture_files':len(hashes),'conditions':len(verified),'counts':verified},indent=2))
