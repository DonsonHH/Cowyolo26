"""Describe incomplete predicted tracks; no human identity or event truth is inferred."""
from pathlib import Path
from collections import defaultdict
import csv, hashlib, json
ROOT=Path(__file__).resolve().parents[1]

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    summaries=[ROOT/'delivery/results/replay_v2/summary.json',ROOT/'delivery/results/full640_confirmation/summary.json']
    conditions=[(p.parent,c) for p in summaries for c in load(p)['conditions']]
    results=[];alltracks=[]
    for parent,c in conditions:
        folder=parent/c['name'];tracks=defaultdict(list)
        with (folder/'source_tracks.csv').open(newline='',encoding='utf-8') as f:
            for row in csv.DictReader(f):
                tracks[int(row['track_id'])].append({k:float(v) for k,v in row.items()})
        events=load(folder/'source_events.json');counted={e['track_id'] for e in events}
        stride=c['arm']['stride'];stable=c['arm']['stable_samples'];details=[]
        for tid,rows in sorted(tracks.items()):
            rows.sort(key=lambda r:r['source_frame']);runs={'A':0,'B':0};zone=None;streak=0;prev=None
            for row in rows:
                y=row['axis_position'];current='A' if y<.4 else 'B' if y>.6 else None
                streak=streak+1 if current and current==zone and prev is not None and row['source_frame']==prev+stride else int(current is not None)
                if current:runs[current]=max(runs[current],streak)
                zone=current;prev=row['source_frame']
            item={'condition':c['name'],'track_id':tid,'counted':tid in counted,'observations':len(rows),
                  'first_frame':int(rows[0]['source_frame']),'last_frame':int(rows[-1]['source_frame']),
                  'first_y':rows[0]['axis_position'],'min_y':min(r['axis_position'] for r in rows),
                  'max_y':max(r['axis_position'] for r in rows),'max_consecutive_A':runs['A'],'max_consecutive_B':runs['B'],
                  'both_stable_consecutive_in_scope':min(runs.values())>=stable,
                  'largest_gap_frames':max((b['source_frame']-a['source_frame'] for a,b in zip(rows,rows[1:])),default=0)}
            details.append(item);alltracks.append(item)
        uncounted=[r for r in details if not r['counted']]
        fixed=[]
        with (folder/'pretracker_boxes.csv').open(newline='',encoding='utf-8') as f:
            raw=list(csv.DictReader(f))
        for frame in [8912,9345,9420,9550,9700,10873]:
            sample=frame-frame%stride
            rows=[r for r in raw if int(r['frame'])==sample]
            roi=[r for r in rows if .34<(float(r['x1'])+float(r['x2']))/5120<.75]
            fixed.append({'source_frame':frame,'last_inference_frame':sample,'raw_ROI_boxes':len(roi),
                          'tracked_ROI_boxes':sum(any(int(r['source_frame'])==sample for r in values) for values in tracks.values())})
        results.append({'condition':c['name'],'tracked_IDs':len(tracks),'predicted_events':len(events),
                        'uncounted_IDs':len(uncounted),'uncounted_without_3_or_11_consecutive_A_in_scope':sum(r['max_consecutive_A']<stable for r in uncounted),
                        'uncounted_without_3_or_11_consecutive_B_in_scope':sum(r['max_consecutive_B']<stable for r in uncounted),
                        'uncounted_tracklets':uncounted,'fixed_frame_output_counts':fixed})
    target=ROOT/'results/recovery_tracklet_diagnosis.json';assert not target.exists()
    record={'summary_sha256':[sha(p) for p in summaries],'conditions':results,
            'counts_describe_predicted_IDs_not_number_of_real_cows':True,
            'streaks_are_scope_only_warmup_not_included':True,
            'fragmentation_or_detection_failure_not_independently_attributed':True,
            'independent_source_accuracy':None,'training_or_new_inference':False}
    target.write_text(json.dumps(record,indent=2),encoding='utf-8')
    with (ROOT/'results/recovery_tracklets.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(alltracks[0]));writer.writeheader();writer.writerows(alltracks)
    print(json.dumps([{k:r[k] for k in ['condition','tracked_IDs','predicted_events','uncounted_IDs','uncounted_without_3_or_11_consecutive_A_in_scope','uncounted_without_3_or_11_consecutive_B_in_scope']} for r in results]))
if __name__=='__main__':main()
