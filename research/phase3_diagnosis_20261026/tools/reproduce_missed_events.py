"""Replay frozen real tracker positions through the actual frozen counter.

Exit 2 means the known missed-event symptom is present. This is a diagnostic
regression harness, not a requirement to tune the test clip to six predictions.
"""
from pathlib import Path
from collections import defaultdict
import argparse,csv,hashlib,json,sys

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT.parent/'counting_eval_20261026'
sys.path.insert(0,str(FROZEN/'tools'))
from zone_counter import ZoneCounter

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',choices=['pilot','generic'],default='pilot')
    parser.add_argument('--expected-complete',type=int,default=6)
    args=parser.parse_args()
    path=ROOT/'inputs'/f'{args.model}_Toros_tracks.csv'
    byframe=defaultdict(dict)
    for row in csv.DictReader(path.open()):
        byframe[int(row['frame'])][int(row['track_id'])]=float(row['axis_position'])
    counter=ZoneCounter();events=[]
    for frame in range(479):
        for event in counter.update(frame/30,byframe[frame]):
            event['frame']=frame;events.append(event)
    saved=json.loads((FROZEN/'results/external_inference_summaries.json').read_text())
    baseline=next(r for r in saved if r['model']==args.model and r['video']=='Toros')
    assert events==baseline['events'],'Replay differs from preserved inference'
    passed=len(events)==args.expected_complete
    record={'status':'PASS' if passed else 'REPRODUCED_MISSED_EVENTS',
            'model':args.model,'expected_complete_events':args.expected_complete,
            'observed_events':len(events),'events':events,
            'tracks_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'counter_sha256':hashlib.sha256((FROZEN/'tools/zone_counter.py').read_bytes()).hexdigest(),
            'scope':'Replay of real saved tracker positions; symptom check, not an independent test score'}
    (ROOT/'results').mkdir(exist_ok=True)
    (ROOT/'results'/f'replay_{args.model}.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record,indent=2))
    return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
