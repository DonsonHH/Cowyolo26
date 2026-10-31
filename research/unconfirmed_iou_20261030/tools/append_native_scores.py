"""Repair a scene-name metadata link without changing any cached result."""
from pathlib import Path
from datetime import datetime,timezone
import json,gzip,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/control_v2'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=load(ROOT/'protocol/control_v2.json');ref=load(PROJECT/'pynq_mosaic192_eval_20261030/protocol/eval_v1.json')['videos'][1]['reference_events']
caches=[r for r in p['caches'] if r['id'].startswith('native_toros')]
assert len(caches)==2 and all(r['formal_event_scoring_allowed'] and r['reference_events'] is None for r in caches)
protocol={'status':'SCENE_ALIAS_REFERENCE_LINK_CORRECTION_FOR_EXISTING_PUBLISHED_TOROS_SCORES','created_UTC':datetime.now(timezone.utc).isoformat(),
    'scene_actual':'toros_used_reverse','scene_metadata_builder_looked_for':'toros','cache_ids':[r['id'] for r in caches],
    'reference_events':ref,'event_tolerance_s':2.,'original_metrics_sha256':sha(OUT/'metrics.json'),
    'original_score_None_entries_kept':True,'changed_raw_detector_tracker_or_counter_outputs':False,'new_tracker_updates':0,'new_independent_test':False}
f=ROOT/'protocol/native_reference_link_v1.json';assert not f.exists();f.write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
def score(reference,events):
    best=(-1,float('inf'));winners=[]
    def search(i,used,pairs,cost):
        nonlocal best,winners
        if i==len(reference):
            v=(len(pairs),cost)
            if v[0]>best[0] or v[0]==best[0] and cost<best[1]-1e-10:best=v;winners=[pairs]
            elif v[0]==best[0] and abs(cost-best[1])<=1e-10:winners.append(pairs)
            return
        search(i+1,used,pairs,cost)
        for j,e in enumerate(events):
            error=abs(e['time_s']-reference[i]['time_s'])
            if j not in used and error<=2:search(i+1,used|{j},pairs+[(i,j)],cost+error)
    search(0,set(),[],0.)
    pairs=winners[0];correct=sum(reference[i]['direction']==events[j]['direction'] for i,j in pairs)
    return {'TP':correct,'FP':len(events)-correct,'FN':len(reference)-correct,'temporally_matched':best[0],
        'time_error_sum':best[1],'pairs':pairs,'number_of_temporally_optimal_assignments':len(winners)}
rows=[]
for c in caches:
    w=c['windows'][0]
    for variant,file in [('baseline','baseline_trace.json.gz'),('unconfirmed_pure_IoU','unconfirmed_pure_IoU_trace.json.gz')]:
        trace=gz(OUT/c['id']/file)
        for counter in ['confirmed_only_events','handoff_events']:
            events=[e for e in trace[counter] if w['start']<=e['frame0']<w['end']]
            rows.append({'cache':c['id'],'variant':variant,'counter':counter,'events':events,'formal_event_metrics':score(ref,events)})
assert sha(OUT/'metrics.json')==protocol['original_metrics_sha256']
r={'status':'EIGHT_NATIVE_TOROS_PUBLISHED_EVENT_SCORES_ADDED_WITHOUT_TRACKER_RERUN','created_UTC':datetime.now(timezone.utc).isoformat(),
    'protocol_sha256':sha(f),'rows':rows,'original_metrics_file_unchanged':True,'new_model_forwards':0,'new_tracker_updates':0,'new_independent_test':False,'whole_goal_complete':False}
f=ROOT/'results/native_Toros_score_appendix.json';assert not f.exists();f.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':r['status'],'handoff_TP_FP_FN':[[x['cache'],x['variant'],[x['formal_event_metrics'][k] for k in ['TP','FP','FN']]] for x in rows if x['counter']=='handoff_events']}))
