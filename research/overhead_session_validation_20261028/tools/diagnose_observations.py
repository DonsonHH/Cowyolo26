"""Independent event extraction and descriptive coverage, without event GT or tuning."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def runs(values,ordered):
    best=0;current=0
    for n in ordered:
        current=current+1 if n in values else 0;best=max(best,current)
    return best

def extract_independent(obs):
    # Rebuild eligible immediately preceding tentative observations from raw state
    # ledger, then use a per-ID sequence scan; do not import either counter module.
    histories=defaultdict(list);seen_confirmed=set();previous_tentative={};previous_time=None;created=set();admissions=[]
    for o in obs:
        current={int(k):v for k,v in o['confirmed_positions'].items()};active=set(o['confirmed_IDs'])
        for ID in sorted(active):
            if ID not in created and (ID in current or ID in previous_tentative):
                created.add(ID)
                if ID not in seen_confirmed and ID in previous_tentative and o['time_s']-previous_time<=2:
                    histories[ID].append((previous_time,previous_tentative[ID],None))
                    admissions.append({'ID':ID,'observation_time_s':previous_time,'confirmation_time_s':o['time_s'],'axis_position':previous_tentative[ID]})
        for ID in created:histories[ID].append((o['time_s'],current.get(ID),o['frame0']))
        seen_confirmed.update(active);previous_time=o['time_s'];previous_tentative={int(k):v for k,v in o['tentative_positions'].items() if int(k) not in seen_confirmed}
    events=[];details=[]
    for ID,history in histories.items():
        origin=None;run=[];last_real=None;stable=[]
        for t,pos,frame in history:
            if pos is None:run=[];continue
            if last_real is None or t-last_real>2:origin=None;run=[]
            last_real=t;zone='A' if pos<.4 else 'B' if pos>.6 else None
            if zone is None:run=[];continue
            if not run or run[-1][1]!=zone:run=[]
            run.append((t,zone))
            if len(run)<3 or origin==zone:continue
            stable.append({'zone':zone,'time_s':t,'frame0':frame})
            if origin is not None:
                assert frame is not None
                events.append({'time_s':float(t),'track_id':ID,'direction':origin+'->'+zone,'frame0':frame})
            origin=zone
        points=[(t,p,f) for t,p,f in history if p is not None and f is not None]
        details.append({'track_ID':ID,'confirmed_ROI_samples':len(points),'first_frame0':min(f for t,p,f in points) if points else None,
                        'last_frame0':max(f for t,p,f in points) if points else None,
                        'min_axis':min(p for t,p,f in points) if points else None,'max_axis':max(p for t,p,f in points) if points else None,
                        'stable_zone_transitions':stable,'zone_sequence':[{'frame0':f,'zone':'A' if p<.4 else 'B' if p>.6 else 'M'} for t,p,f in points]})
    events.sort(key=lambda e:(e['frame0'],e['track_id']));return events,details,admissions

def main():
    delivery=ROOT/'inference_delivery/results/inference';summary=load(delivery/'summary.json');rows=[];totalobs=0;newindependent=[]
    for c in summary['conditions']:
        folder=delivery/c['sequence']/c['model'];obs=load(folder/'observations.json');raw=list(csv.DictReader((folder/'raw_detector_boxes.csv').open(encoding='utf-8')))
        events,IDs,admitted=extract_independent(obs);recorded=load(folder/'handoff_events.json')
        assert events==sorted(recorded,key=lambda e:(e['frame0'],e['track_id']))
        raw_frames={int(r['frame0']) for r in raw};track_frames={o['frame0'] for o in obs if o['confirmed_positions']};ordered=[o['frame0'] for o in obs]
        row={'sequence':c['sequence'],'model':c['model'],'observed_samples':len(obs),
             'raw_nonempty_frames':len(raw_frames),'tracked_ROI_nonempty_frames':len(track_frames),
             'longest_all_frame_raw_empty_run_samples':runs(set(ordered)-raw_frames,ordered),
             'longest_ROI_track_empty_run_samples':runs(set(ordered)-track_frames,ordered),
             'independent_event_count':len(events),'events':events,'ID_diagnostics':sorted(IDs,key=lambda r:r['track_ID']),
             'tentative_admissions_independently_rebuilt':admitted,
             'coverage_is_not_recall':'An output-presence statistic; no manually labelled detection population.',
             'event_truth_available':False}
        rows.append(row);totalobs+=len(obs);newindependent+=events
    assert len(rows)==8 and totalobs==216 and len(newindependent)==1
    result={'status':'ALL_EIGHT_EVENT_PATHS_MATCH_INDEPENDENT_SEQUENCE_SCAN','conditions':rows,'conditions_checked':8,
            'observation_ticks':216,'independent_predicted_events':1,'only_event':newindependent[0],
            'production_counter_modules_imported':False,'new_thresholds_or_training':False,'physical_miss_counts_established':False,
            'event_accuracy_F1_established':False,'whole_goal_complete':False}
    target=ROOT/'results/observation_diagnosis.json';assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='conditions'}),flush=True)
    print(json.dumps([{k:r[k] for k in ['sequence','model','raw_nonempty_frames','tracked_ROI_nonempty_frames','independent_event_count']} for r in rows]),flush=True)

if __name__=='__main__':main()
