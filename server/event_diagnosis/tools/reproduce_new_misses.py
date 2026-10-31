"""Red-capable exact replay of actual counters for the new20epoch checkpoints."""
from pathlib import Path
import csv,json,runpy,sys
BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'counting_eval_20261026/tools'))
from zone_counter import ZoneCounter


def main():
    matcher=runpy.run_path(str(BASE/'detector_training_20261027/tools/verify_results.py'))['matching']
    root=BASE/'detector_training_20261027/delivery/results/inference'
    reference=json.loads((root/'toros_reference_events.json').read_text(encoding='utf-8'))
    result=[]
    for seed in [26,27,28]:
        dest=root/f'epoch20_seed{seed}';trace=list(csv.DictReader((dest/'Toros_tracks.csv').open()))
        frames={}
        for r in trace:frames.setdefault(int(r['source_frame']),{})[int(r['track_id'])]=float(r['axis_position'])
        counter=ZoneCounter();events=[]
        for f in range(479):
            for event in counter.update(f/30,frames.get(f,{})):events.append({**event,'source_frame':f})
        assert events==json.loads((dest/'Toros_events.json').read_text(encoding='utf-8'))
        metrics=matcher(reference,events)
        result.append({'seed':seed,'actual_counter_replayed':True,'events':events,**metrics})
    status={'status':'REPRODUCED_FROZEN_MISSED_EVENTS' if any(r['TP']<6 for r in result) else 'NO_FROZEN_MISSES',
            'conditions':result,'expected_complete_reference_events':6,'exit2_means_symptom_reproduced':True}
    print(json.dumps(status),flush=True)
    raise SystemExit(2 if any(r['TP']<6 for r in result) else 0)


if __name__=='__main__':main()
