from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'input'))
from confirmation_counter import ConfirmationHandoffCounter
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    summaries=[];frames=0
    for seed,tid in [(26,95),(27,57),(28,117)]:
        folder=ROOT/f'delivery/results/replay_v2/seed{seed}';candidate=ConfirmationHandoffCounter();disabled=ConfirmationHandoffCounter(retain_prior=False)
        events=[];old=[];states=[]
        for row in load(folder/'observations.json'):
            f=row['source_frame'];positions={int(k):v for k,v in row['confirmed_positions'].items()};tentative={int(k):v for k,v in row['tentative_positions'].items()}
            for module,out in [(candidate,events),(disabled,old)]:
                for e in module.update(f/25,positions,tentative,set(row['confirmed_ids'])):
                    e['source_frame']=f
                    if f>=8912:out.append(e)
            if f in [9305,9310,9315,9345]:
                a=candidate.counters.get(tid);b=disabled.counters.get(tid)
                states.append({'frame':f,'target_ID':tid,'handoff_state':vars(a.states[tid]).copy() if a and tid in a.states else None,
                    'disabled_state':vars(b.states[tid]).copy() if b and tid in b.states else None,'pending':candidate.pending.get(tid)})
            frames+=1
        assert events==load(folder/'handoff_events.json') and old==load(folder/'baseline_events.json')
        summaries.append({'seed':seed,'handoff_events':len(events),'disabled_events':len(old),'selected_states':states})
    out={'status':'WINDOWS_COMPONENT_REPLAY_AND_SELECTED_CAUSAL_STATES_EXACT','trace_frames':frames,'conditions':summaries,
         'new_detector_forwards':0,'training_updates':0,'source_accuracy_verified':False,'board_execution':False}
    path=ROOT/'results/local_causal_replay.json';assert not path.exists();path.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
if __name__=='__main__':main()
