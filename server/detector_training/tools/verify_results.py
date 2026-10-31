"""Independent event state and exhaustive6-event matching, without algorithm imports."""
from pathlib import Path
from collections import defaultdict
import csv,functools,hashlib,json,math

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replay(rows,ticks,fps):
    states={};byframe=defaultdict(list);events=[]
    for row in rows:byframe[int(row['source_frame'])].append(row)
    for frame in ticks:
        positions={int(r['track_id']):float(r['axis_position']) for r in byframe.get(frame,[])}
        for tid,state in states.items():
            if tid not in positions:state['candidate']=None;state['streak']=0
        for tid,p in positions.items():
            if not 0<=p<=1:continue
            s=states.setdefault(tid,{'origin':None,'candidate':None,'streak':0,'last':-1e30})
            if frame/fps-s['last']>2:s.update(origin=None,candidate=None,streak=0)
            s['last']=frame/fps;zone='A' if p<.4 else 'B' if p>.6 else None
            if zone is None:s.update(candidate=None,streak=0);continue
            s['streak']=s['streak']+1 if zone==s['candidate'] else 1;s['candidate']=zone
            if s['streak']>=3 and s['origin']!=zone:
                if s['origin'] is not None:events.append({'time_s':frame/fps,'track_id':tid,'direction':s['origin']+'->'+zone,'source_frame':frame})
                s['origin']=zone
    return events


def matching(reference,predicted):
    # DP over prediction index and used reference mask. Independent of SciPy.
    n=len(reference);assert n==6
    @functools.lru_cache(None)
    def solve(j,mask):
        if j==len(predicted):return (0,0.,())
        best=solve(j+1,mask)
        for i,r in enumerate(reference):
            delta=abs(float(r['time_s'])-float(predicted[j]['time_s']))
            if mask&(1<<i) or delta>2:continue
            count,error,pairs=solve(j+1,mask|(1<<i))
            candidate=(count+1,error+delta,((i,j),)+pairs)
            if (candidate[0],-candidate[1])>(best[0],-best[1]):best=candidate
        return best
    _,_,pairs=solve(0,0)
    correct=sum(reference[i]['direction']==predicted[j]['direction'] for i,j in pairs)
    return {'TP':correct,'FP':len(predicted)-correct,'FN':len(reference)-correct,
            'temporally_matched':len(pairs),'wrong_direction_matches':len(pairs)-correct}


def main():
    delivery=ROOT/'delivery'
    manifest=json.loads((delivery/'delivery_manifest.json').read_text())
    for row in manifest:
        path=delivery/row['path'];assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],row['path']
    training=delivery/'results/training'
    summary=json.loads((training/'summary.json').read_text())
    assert summary['status']=='COMPLETED_PUBLIC_LABEL_TRAINING_3SEEDS_20EPOCHS'
    frozen=json.loads((training/'all_checkpoints_frozen_before_video.json').read_text())
    assert not frozen['video_or_external_inference_performed']
    assert [c['seed'] for c in frozen['conditions']]==[26,27,28]
    for condition in frozen['conditions']:
        seed=condition['seed'];path=training/f'seed{seed}/weights/last.pt'
        assert sha(path)==condition['checkpoint_sha256']
        rows=list(csv.DictReader((training/f'seed{seed}/results.csv').open()))
        assert len(rows)==20 and [int(r['epoch']) for r in rows]==list(range(1,21))
        assert all(math.isfinite(float(v)) for r in rows for v in r.values())
    inputs=json.loads((training/'input_audit.json').read_text())
    assert inputs['split_counts']=={'train':5913,'val':370,'dev_test':741,'quarantine_duplicate_of_holdout':19}
    assert {r['split'] for r in inputs['rows']}=={'train','val'} and len(inputs['rows'])==6283
    assert not inputs['raw_source_video_opened'] and not inputs['dev_test_forward_performed']
    inference=delivery/'results/inference';results=json.loads((inference/'summary.json').read_text())
    assert results['training_freeze_sha256']==sha(training/'all_checkpoints_frozen_before_video.json')
    reference=json.loads((inference/'toros_reference_events.json').read_text())
    checks=[]
    for condition in results['conditions']:
        name=condition['name'];dest=inference/name
        for scene in ['source','Toros']:
            trace=list(csv.DictReader((dest/f'{scene}_tracks.csv').open()))
            if scene=='source':trace=list(csv.DictReader((dest/'source_warmup_tracks.csv').open()))+trace
            ticks=range(0,10874,5) if scene=='source' else range(479)
            expected=json.loads((dest/f'{scene}_events.json').read_text())
            actual=replay(trace,ticks,25 if scene=='source' else 30)
            if scene=='source':actual=[r for r in actual if r['source_frame']>=8912]
            assert actual==expected,(name,scene,actual,expected)
            row={'model':name,'scene':scene,'events':len(actual),'event_replay':'PASS'}
            if scene=='Toros':
                independently=matching(reference,actual)
                assert all(condition['Toros_event_metrics'][k]==v for k,v in independently.items())
                row.update(independently)
            checks.append(row)
    assert len(checks)==10
    result={'status':'MANIFEST_CHECKPOINT_TRAINING_AND_10_EVENT_REPLAYS_PASS','manifest_files':len(manifest),
            'seeds_completed':[26,27,28],'epochs_each':20,'training_val_audited_rows':6283,'checks':checks,
            'source_independent_accuracy_verified':False,'board_verified':False,'full_goal_complete':False}
    (ROOT/'results/independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
