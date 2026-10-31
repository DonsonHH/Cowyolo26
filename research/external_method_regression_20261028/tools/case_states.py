from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'input'))
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    output=[]
    for variant in ['installed','secondstage_iou','allow_lost_iou']:
        folder=ROOT/f'delivery/results/pilot_{variant}';ordinary=ZoneCounter();handoff=ConfirmationHandoffCounter();events0=[];events1=[];states=[]
        for row in load(folder/'observations.json'):
            f=row['frame'];p={int(k):v for k,v in row['confirmed_positions'].items()};t={int(k):v for k,v in row['tentative_positions'].items()}
            for counter,target in [(ordinary,events0),(handoff,events1)]:
                if counter is ordinary:emitted=counter.update(f/30,p)
                else:emitted=counter.update(f/30,p,t,set(row['confirmed_IDs']))
                for e in emitted:e['frame']=f;target.append(e)
            if 100<=f<=135:
                a=ordinary.states.get(1);module=handoff.counters.get(1);b=module.states.get(1) if module else None
                states.append({'frame':f,'track_ID':1,'observed_axis':p.get(1),'confirmed_only_state':vars(a).copy() if a else None,
                    'handoff_state':vars(b).copy() if b else None})
        assert events0==load(folder/'confirmed_only_events.json') and events1==load(folder/'handoff_events.json')
        output.append({'variant':variant,'full_component_replay_exact':True,'events_for_target_ID':[e for e in events1 if e['track_id']==1],
             'low_matches_for_target_ID':[r for r in load(folder/'low_matches.json') if r['track_id']==1],'states':states})
    value={'status':'THREE_WINDOWS_COMPONENT_REPLAYS_AND_NEW_MATCH_STATE_CASE_EXACT',
      'model':'pilot','target_ID':1,'reference_publisher_ID':1,'reference_event_frame':110,'new_prediction_event_frame':125,
      'association_case_cannot_prove_physicalID_identity_by_number':True,'conditions':output,
      'new_inference':False,'new_independent_test':False}
    path=ROOT/'results/pilot_case_states.json';assert not path.exists();path.write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps([{'variant':c['variant'],'events':c['events_for_target_ID'],'states':[s for s in c['states'] if s['frame'] in [110,112,120,121,122,123,124,125]]} for c in output]))
if __name__=='__main__':main()
