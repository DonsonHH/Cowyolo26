"""Reproduce the frozen undercount and classify incomplete predicted tracks."""
from pathlib import Path
from collections import defaultdict
import argparse,csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'counting_eval_20261026/tools'))
from zone_counter import ZoneCounter

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rough-min',type=int);args=parser.parse_args()
    out=ROOT/'results';out.mkdir(parents=True,exist_ok=True)
    reports=[]
    for seed in [26,27,28]:
        folder=PROJECT/f'orientation_video_20261027/delivery/results/inference/clockwise90_seed{seed}'
        rows=[]
        for name in ['source_warmup_tracks.csv','source_tracks.csv']:
            with (folder/name).open(encoding='utf-8',newline='') as handle:
                rows.extend(csv.DictReader(handle))
        frames=defaultdict(list);tracks=defaultdict(list)
        for row in rows:
            row={k:int(v) if k in ['source_frame','track_id'] else float(v) for k,v in row.items()}
            frames[row['source_frame']].append(row)
            if row['source_frame']>=8912:tracks[row['track_id']].append(row)
        counter=ZoneCounter();events=[]
        for frame in range(0,10874,5):
            for event in counter.update(frame/25,{r['track_id']:r['axis_position'] for r in frames[frame]}):
                event['source_frame']=frame
                if frame>=8912:events.append(event)
        assert events==json.loads((folder/'source_events.json').read_text())
        counted={e['track_id'] for e in events}
        details=[]
        for tid,items in sorted(tracks.items()):
            consecutive={'A':0,'B':0};current=None;streak=0;previous=None
            for row in items:
                p=row['axis_position'];zone='A' if p<.4 else 'B' if p>.6 else None
                if zone is not None and zone==current and previous is not None and row['source_frame']==previous+5:streak+=1
                else:streak=1 if zone else 0
                if zone:consecutive[zone]=max(consecutive[zone],streak)
                current=zone;previous=row['source_frame']
            details.append({'track_id':tid,'observations':len(items),'first_frame':items[0]['source_frame'],
                'last_frame':items[-1]['source_frame'],'min_y':min(r['axis_position'] for r in items),
                'max_y':max(r['axis_position'] for r in items),'max_A_consecutive':consecutive['A'],'max_B_consecutive':consecutive['B'],
                'predicted_event':tid in counted,'has_both_stable_regions':all(v>=3 for v in consecutive.values()),
                'largest_observation_gap_frames':max((b['source_frame']-a['source_frame'] for a,b in zip(items,items[1:])),default=0)})
        reports.append({'seed':seed,'frozen_predicted_events':len(events),'tracked_IDs_in_scope':len(tracks),
            'uncounted_tracklets':[r for r in details if not r['predicted_event']], 'all_tracklets':details})
    result={'status':'FROZEN_8_6_8_EVENTS_EXACTLY_REPLAYED','scope_inclusive':[8912,10873],
        'user_feedback':'User reportsmorethan8, approximatelyteens; exactcount/eventtimesnotprovided',
        'feedback_is_not_final_ground_truth':True,'conditions':reports,'new_model_inference':False}
    target=out/'cached_diagnosis.json'
    if not target.exists():target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'predictions':[r['frozen_predicted_events'] for r in reports],
        'tracklets':[r['tracked_IDs_in_scope'] for r in reports],
        'uncompleted':[r['uncounted_tracklets'] for r in reports]}))
    if args.rough_min is not None:
        minimum=reports[0]['frozen_predicted_events']>=args.rough_min
        print(json.dumps({'coarse_user_feedback_screen':'PASS' if minimum else 'FAIL','minimum_for_smoke_screen':args.rough_min,
            'diagnostic_only_not_count_accuracy_or_optimization_target':True}))
        raise SystemExit(0 if minimum else 1)

if __name__=='__main__':main()
