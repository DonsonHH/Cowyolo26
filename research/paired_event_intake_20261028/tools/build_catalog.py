"""Extend the immutable historical catalog with all three current counter pairs."""
from pathlib import Path
from collections import Counter
import copy,csv,hashlib,json,math
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_row(row):
    for key in ['events','summary','protocol']:
        path=Path(row[f'{key}_path'])
        if not path.resolve().is_relative_to(PROJECT.resolve()) or sha(path)!=row[f'{key}_sha256']:
            raise ValueError(f'Changed or out-of-workspace {key} artifact: {row["condition_id"]}')
    events=load(row['events_path'])
    for e in events:
        if type(e['source_frame']) is not int or not 8912<=e['source_frame']<=10873:raise ValueError('Invalid prediction frame')
        if type(e['time_s']) not in [int,float] or not math.isfinite(e['time_s']) or e['time_s']!=e['source_frame']/25:raise ValueError('Prediction time/frame mismatch')
        if e['direction'] not in ['A->B','B->A']:raise ValueError('Invalid prediction direction')
    counts=Counter(e['direction'] for e in events)
    if len(events)!=row['predicted_events'] or counts['A->B']!=row['predicted_A_to_B'] or counts['B->A']!=row['predicted_B_to_A']:
        raise ValueError('Prediction count/catalog mismatch')
    return events
def main():
    out=ROOT/'results/frozen_prediction_catalog_v2.json';assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True)
    oldpath=PROJECT/'evaluation_intake_20261028/results/frozen_prediction_catalog.json';old=load(oldpath)
    assert len(old['conditions'])==17
    records=copy.deepcopy(old['conditions']);aliases=copy.deepcopy(old['exact_prior_event_aliases']);pairs=[]
    h=PROJECT/'confirmation_handoff_20261028';hp=h/'protocol/handoff_v1.json';p=load(hp)
    recovery=PROJECT/'counting_recovery_20261028';rp=recovery/'protocol/recovery_v2.json'
    r=load(rp);paired_summary=h/'delivery/results/replay_v2/summary.json';summ=load(paired_summary)
    for seed in [26,27,28]:
        w=next(w for w in p['weights'] if w['seed']==seed)
        checkpoint=PROJECT/f'cows2021_adaptation_20261027/delivery/results/training/seed{seed}/weights/last.pt'
        assert sha(checkpoint)==w['sha256']
        name=f'full640_5hz_seed{seed}';base=recovery/'delivery/results/replay_v2'/name
        if not base.exists():base=recovery/'delivery/results/full640_confirmation'/name
        bs=load(base/'summary.json');new=h/f'delivery/results/replay_v2/seed{seed}';ns=next(c for c in summ['conditions'] if c['seed']==seed)
        contract={'orientation':'clockwise90','imgsz':640,'stride':5,'crop_x':[0,2560],'confidence':.2,
                  'roi_x':[.34,.75],'gate_y':[.4,.6],'stable_samples':3,'maximum_gap_s':2.,
                  'tracker':'bytetrack.yaml','ultralytics':'8.4.63','base_counter_sha256':p['frozen_base_counter_sha256']}
        ids=[]
        for mode,folder,summary,protocol,events,down,up in [
          ('confirmed_only',base,base/'summary.json',rp,base/'source_events.json',bs['predicted_down'],bs['predicted_up']),
          ('confirmation_handoff',new,paired_summary,hp,new/'handoff_events.json',ns['handoff_down'],ns['handoff_up'])]:
            cid=f'counting_recovery_20261028/{name}' if mode=='confirmed_only' else f'confirmation_handoff_20261028/seed{seed}'
            pipeline={**contract,'counter_variant':mode,'retain_previous_tentative_observation':mode=='confirmation_handoff'}
            if mode=='confirmation_handoff':pipeline['handoff_module_sha256']=p['handoff_module_sha256']
            canonical=json.dumps(pipeline,sort_keys=True,separators=(',',':')).encode()
            row={'condition_id':cid,'title':f'Full640 5Hz seed{seed}: {mode}','checkpoint_sha256':w['sha256'],
                 'seed':seed,'orientation':'clockwise90','source_sha256':old['source_sha256'],
                 'source_frame_scope':[8912,10873],'history_start':0,'summary_path':str(summary),'summary_sha256':sha(summary),
                 'protocol_path':str(protocol),'protocol_sha256':sha(protocol),'events_path':str(events),'events_sha256':sha(events),
                 'pipeline_contract':pipeline,'pipeline_contract_sha256':hashlib.sha256(canonical).hexdigest(),
                 'predicted_A_to_B':down,'predicted_B_to_A':up,'predicted_events':down+up,'source_accuracy_verified':False}
            records.append(row);ids.append(cid)
        for filename in ['baseline_events.json','disabled_events.json']:
            assert load(new/filename)==load(base/'source_events.json')
            aliases.append({'historical_condition':f'confirmation_handoff_20261028/seed{seed}/{filename}',
                'canonical_condition':ids[0],'normalized_events_equal':True,'historical_events_path':str(new/filename),
                'historical_events_sha256':sha(new/filename),'reason':'original and disabled-wrapper events exactly reproduce same full640 baseline'})
        pairs.append({'seed':seed,'baseline_condition_id':ids[0],'candidate_condition_id':ids[1],
                      'baseline_predicted_events':bs['predicted_down']+bs['predicted_up'],
                      'candidate_predicted_events':ns['handoff_down']+ns['handoff_up'],
                      'candidate_selection_did_not_use_independent_reference':True})
    assert len(records)==len({r['condition_id'] for r in records})==23
    assert records[:17]==old['conditions']
    for row in records:validate_row(row)
    result={'status':'23_FROZEN_CONDITIONS_WITH_THREE_CURRENT_COUNTER_PAIRS_INDEXED',
        'previous_catalog_path':str(oldpath),'previous_catalog_sha256':sha(oldpath),'historical_records_preserved':17,
        'source_sha256':old['source_sha256'],'frame_scope_inclusive':[8912,10873],'FPS':25,
        'conditions':records,'paired_comparisons':pairs,'exact_prior_event_aliases':aliases,
        'legacy_preview_comparisons':old['legacy_preview_comparisons'],
        'condition_identity_rule':'Unique condition_id; same checkpoint+orientation may legitimately differ in input scale and counter handoff',
        'selection_rule':'Preserve all17 historical records; append allthree current full640 baselines and allthree handoff candidates. No truth-based selection.',
        'other_development_controls_retained_in_original_phase_archives':True,'new_reference_received':False,
        'new_inference':False,'source_count_accuracy_verified':False,'whole_goal_complete':False}
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    fields=['condition_id','seed','orientation','predicted_A_to_B','predicted_B_to_A','predicted_events','checkpoint_sha256']
    with out.with_suffix('.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in records)
    print(json.dumps({'conditions':23,'preserved':17,'pairs':pairs,'independent_accuracy':None}))
if __name__=='__main__':main()
