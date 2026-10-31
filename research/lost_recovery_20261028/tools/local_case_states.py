from pathlib import Path
import csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'input'))
from confirmation_counter import ConfirmationHandoffCounter
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    with (ROOT/'results/lost_recoveries_audit.csv').open(encoding='utf-8-sig',newline='') as f:allrows=list(csv.DictReader(f))
    selected=[r for r in allrows if int(r['source_frame'])>=8912 and r['actual_detection_ROI']=='True']
    assert len(selected)==4;cases=[]
    for seed in [26,27,28]:
        folder=ROOT/f'delivery/results/allow_lost_iou_seed{seed}';rows=[r for r in selected if int(r['seed'])==seed]
        counter=ConfirmationHandoffCounter();events=[];states={id(r):[] for r in rows}
        observations=load(folder/'observations.json')
        for o in observations:
            frame=o['source_frame'];p={int(k):v for k,v in o['confirmed_positions'].items()};t={int(k):v for k,v in o['tentative_positions'].items()}
            emitted=counter.update(frame/25,p,t,set(o['confirmed_IDs']))
            for e in emitted:
                e['source_frame']=frame
                if frame>=8912:events.append(e)
            for row in rows:
                target=int(row['track_ID']);at=int(row['source_frame'])
                if at-30<=frame<=at+30:
                    module=counter.counters.get(target);state=module.states.get(target) if module else None
                    states[id(row)].append({'source_frame':frame,'target_axis':p.get(target),'state':vars(state).copy() if state else None,
                        'target_emits_event':any(e['track_id']==target for e in emitted)})
        assert events==load(folder/'handoff_events.json')
        for row in rows:
            target=int(row['track_ID']);at=int(row['source_frame']);own=[e for e in events if e['track_id']==target]
            cases.append({'seed':seed,'target_ID':target,'recovery_source_frame':at,
               'last_observed_frame':int(row['last_observed_source_frame']),'gap_frames':int(row['observation_gap_source_frames']),
               'matching_cost':float(row['cost']),'actual_low_detection_score':float(row['confidence']),
               'target_events':own,'already_counted_before_recovery':any(e['source_frame']<at for e in own),
               'local_counter_states':states[id(row)],'source_component_replay_exact':True})
    output={'status':'ALL_FOUR_CURRENT_SCOPE_ROI_LOW_RECOVERIES_AND_CAUSAL_COUNTER_STATES_INSPECTED',
      'candidate_component_replays_exact':3,'update_traces_replayed':6525,'cases':cases,
      'physical_identity_correspondence_verified':False,'independent_accuracy':None,'new_inference':False}
    target=ROOT/'results/ROI_recovery_case_states.json';assert not target.exists();target.write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps({'cases':[{k:c[k] for k in ['seed','target_ID','recovery_source_frame','gap_frames','already_counted_before_recovery','target_events']} for c in cases]}))
if __name__=='__main__':main()
