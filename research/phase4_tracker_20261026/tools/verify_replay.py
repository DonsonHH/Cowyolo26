"""Independent event reconstruction and exhaustive temporal assignment."""
from pathlib import Path
from collections import defaultdict
from functools import lru_cache
import csv,hashlib,json,tarfile

ROOT=Path(__file__).resolve().parents[1]
bundle=ROOT/'results/tracker_delivery.tar.gz'
digest=hashlib.sha256(bundle.read_bytes()).hexdigest()
assert digest=='9a918bc12dea032b82ed0cc0b9526218e493dd47be18e79f76b07b0f00e07066'
dest=ROOT/'delivery'
if not dest.exists():
    dest.mkdir()
    with tarfile.open(bundle) as tf:tf.extractall(dest,filter='data')
manifest=json.loads((dest/'results/delivery_manifest.json').read_text())
for r in manifest:
    p=dest/r['path'];assert p.resolve().is_relative_to(dest.resolve())
    assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
summary=json.loads((dest/'results/replay/summary.json').read_text())
protocol=json.loads((ROOT/'protocol/tracker_replay_v1.json').read_text())
assert summary['protocol']==protocol
reference=json.loads((ROOT.parent/'counting_eval_20261026/source_review/author_gt_summary.json').read_text())['events']
frozen=json.loads((ROOT.parent/'counting_eval_20261026/results/external_inference_summaries.json').read_text())
verified=[]
for run in summary['runs']:
    expected=next(r['changes'] for r in protocol['controls'] if r['name']==run['variant'])
    baseline=next(r['effective_config'] for r in summary['runs'] if r['model']==run['model'] and r['variant']=='baseline')
    actual_changes={k:v for k,v in run['effective_config'].items() if baseline[k]!=v}
    assert run['changes']==expected==actual_changes
    source=ROOT.parent/f"phase3_diagnosis_20261026/results/capture/{run['model']}/raw_detector_boxes.csv"
    assert hashlib.sha256(source.read_bytes()).hexdigest()==run['source_raw_boxes_sha256']
    tracks=defaultdict(list)
    for r in csv.DictReader((dest/f"results/replay/{run['model']}/{run['variant']}/tracks.csv").open()):
        x=float(r['axis_position'])
        if 0<=x<=1:tracks[int(r['track_id'])].append((int(r['frame']),'A' if x<.4 else 'B' if x>.6 else 'M'))
    events=[]
    for tid,rows in tracks.items():
        groups=[]
        for f,z in rows:
            if groups and groups[-1][-1][0]+1==f and groups[-1][0][1]==z:groups[-1].append((f,z))
            else:groups.append([(f,z)])
        last=None;origin=None
        for group in groups:
            if last is not None and group[0][0]-last>60:origin=None
            last=group[-1][0]
            if group[0][1]=='M' or len(group)<3:continue
            z=group[0][1]
            if origin is not None and z!=origin:
                f=group[2][0];events.append({'track_id':tid,'frame':f,'time_s':f/30,'direction':origin+'->'+z})
            origin=z
    events.sort(key=lambda r:(r['frame'],r['track_id']))
    assert events==sorted(run['events'],key=lambda r:(r['frame'],r['track_id']))
    if run['variant']=='baseline':
        old=next(r for r in frozen if r['model']==run['model'] and r['video']=='Toros')
        assert events==old['events']
    @lru_cache(None)
    def search(i,used):
        if i==len(reference):return 0,0.,()
        best=search(i+1,used)
        for j,pred in enumerate(events):
            error=abs(pred['time_s']-reference[i]['time_s'])
            if used&(1<<j) or error>2:continue
            n,c,pairs=search(i+1,used|(1<<j));candidate=n+1,c+error,((i,j),)+pairs
            if (candidate[0],-candidate[1])>(best[0],-best[1]):best=candidate
        return best
    count,error,pairs=search(0,0)
    tp=sum(reference[i]['direction']==events[j]['direction'] for i,j in pairs)
    fp,fn=len(events)-tp,len(reference)-tp
    assert (tp,fp,fn)==tuple(run['event_metrics'][k] for k in ['TP','FP','FN'])
    verified.append({'model':run['model'],'variant':run['variant'],'TP':tp,'FP':fp,'FN':fn,
                     'event_reconstruction':'PASS','metric_recalculation':'PASS',
                     'spatially_supported_temporal_pairs':sum(r['reference_id_supported'] for r in run['matched_event_reference_support'])})
result={'status':'PASS','bundle_sha256':digest,'manifest_files_verified':len(manifest),'conditions':verified,
        'one_variable_per_variant_and_frozen_raw_input_verified':True,
        'scope':'Independent stored-track arithmetic; tracker implementation replay equivalence is separately gated, reference spatial support is a diagnostic threshold not definitive identity truth'}
(ROOT/'results/independent_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
