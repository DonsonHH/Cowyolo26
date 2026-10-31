"""Read-only reference-conditioned raw/center/confirmation counter oracles."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
import json,gzip,hashlib,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'input'))
from zone_counter import ZoneCounter
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def loadgz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n')
def savegz(p,obj):
    assert not p.exists(),p
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(obj,separators=(',',':')).encode())
def iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=lambda x:(x[2]-x[0])*(x[3]-x[1]);union=area(a)+area(b)-intersection
    return intersection/union if union>0 else 0.
def assign(reference,candidates,threshold):
    matrix=[[iou(r['xyxy'],c['xyxy']) for c in candidates] for r in reference];best=(-1,-1.);solution=[];ties=0
    def search(i,used,pairs,total):
        nonlocal best,solution,ties
        if i==len(reference):
            count=len(pairs)
            if count>best[0] or count==best[0] and total>best[1]+1e-12:best=(count,total);solution=list(pairs);ties=1
            elif count==best[0] and abs(total-best[1])<=1e-12:
                ties+=1
                if pairs<solution:solution=list(pairs)
            return
        search(i+1,used,pairs,total)
        for j in range(len(candidates)):
            if j not in used and matrix[i][j]>=threshold:search(i+1,used|{j},pairs+[(i,j)],total+matrix[i][j])
    search(0,set(),[],0.)
    return solution,matrix,ties
def center(box):return (box[0]+box[2])/(2*2560),(box[1]+box[3])/(2*1440)
def eligible(box):
    cx,cy=center(box);return cy if .34<cx<.75 and 0<=cy<=1 else None
def count_positions(values,config):
    counter=ZoneCounter(**config);events=[];ticks=[]
    for frame in range(0,10874,5):
        positions=values.get(frame,{})
        for event in counter.update(frame/25,positions):events.append({**event,'frame0':frame})
        ticks.append({'frame0':frame,'time_s':frame/25,'confirmed_positions':positions,'confirmed_IDs':sorted(positions)})
    return events,ticks
def longest(values,tid,region):
    maximum=run=0
    for frame in range(0,10874,5):
        position=values.get(frame,{}).get(tid)
        inside=position is not None and (position<.4 if region=='A' else position>.6)
        run=run+1 if inside else 0;maximum=max(maximum,run)
    return maximum
def main():
    p=load(ROOT/'protocol/audit_v1.json')
    for name,digest in p['input_sha256'].items():assert sha(ROOT/'input'/name)==digest
    out=ROOT/'results';out.mkdir(exist_ok=False);started=time.monotonic_ns()
    reference=defaultdict(list)
    for row in load(ROOT/'input/reference_boxes.json'):reference[row['frame0']].append(row)
    for rows in reference.values():rows.sort(key=lambda r:r['reference_track_id'])
    ids=[e['track_id'] for e in load(ROOT/'input/reference_events.json')];expected=load(ROOT/'input/reference_events.json')
    selfpositions={frame:{r['reference_track_id']:r['axis_position'] for r in rows} for frame,rows in reference.items()}
    selfevents,_=count_positions(selfpositions,p['counter']);assert selfevents==expected,(selfevents,expected)
    save(out/'reference_self_regression.json',{'status':'ALL12_BASELINE640_EVENTS_AND_EXACT_TIMES_REPRODUCED',
      'events':selfevents,'independent_ground_truth':False,'reference_box_samples':sum(map(len,reference.values()))})
    results=[];allcases=[];assignments=0;casepaths=0;referencerows=0
    for cache in p['caches']:
        for kind in ['raw','trace','summary']:assert sha(cache[kind+'_file'])==cache[kind+'_sha256']
        raw={r['frame0']:r['predictions'] for r in loadgz(cache['raw_file'])};trace=loadgz(cache['trace_file']);post=defaultdict(list)
        assert list(raw)==list(range(0,10874,5))
        for r in trace['post_tracker']:
            if r['track_id'] is not None:post[r['frame0']].append(r)
        summary=next(r for r in load(cache['summary_file']) if r['counter']=='handoff_events')
        actual=[e for e in trace['handoff_events'] if 8912<=e['frame0']<=10873]
        assert actual==summary['events'] and sum(e['direction']=='A->B' for e in actual)==summary['down']
        for threshold in p['IoU_thresholds']:
            modevalues={mode:defaultdict(dict) for mode in ['presence_using_reference_center','raw_box_center_assisted_identity','post_confirmed_plus_valid_admitted_center_assisted_identity']}
            correspondences=[];rawmap={};postmap={};ties_total=0
            for frame,refs in sorted(reference.items()):
                matches,matrix,ties=assign(refs,raw[frame],threshold);assignments+=1;ties_total+=ties>1
                match={i:j for i,j in matches}
                pmatches,pmatrix,pties=assign(refs,post[frame],threshold);assignments+=1;ties_total+=pties>1
                pmatch={i:j for i,j in pmatches}
                for i,ref in enumerate(refs):
                    tid=ref['reference_track_id'];r=raw[frame][match[i]] if i in match else None;pr=post[frame][pmatch[i]] if i in pmatch else None
                    if r:
                        modevalues['presence_using_reference_center'][frame][tid]=ref['axis_position'];rawmap[(frame,tid)]=r
                        axis=eligible(r['xyxy'])
                        if axis is not None:modevalues['raw_box_center_assisted_identity'][frame][tid]=axis
                    if pr:
                        postmap[(frame,pr['track_id'])]=tid;axis=eligible(pr['xyxy'])
                        if axis is not None:modevalues['post_confirmed_plus_valid_admitted_center_assisted_identity'][frame][tid]=axis
                    correspondences.append({'frame0':frame,'reference_track_id':tid,'reference_box':ref['xyxy'],'reference_axis_position':ref['axis_position'],
                       'reference_origin':ref['origin'],'raw_prediction_index':match.get(i),'raw_IoU':matrix[i][match[i]] if i in match else None,
                       'maximum_available_raw_IoU':max(matrix[i]) if matrix[i] else 0.,'raw_axis_position':center(r['xyxy'])[1] if r else None,
                       'raw_center_eligible_ROI':eligible(r['xyxy']) is not None if r else None,'raw_box':r['xyxy'] if r else None,
                       'raw_confidence':r['confidence'] if r else None,'post_prediction_index':pmatch.get(i),
                       'post_IoU':pmatrix[i][pmatch[i]] if i in pmatch else None,'post_track_id':pr['track_id'] if pr else None,
                       'post_box':pr['xyxy'] if pr else None,'post_axis_position':center(pr['xyxy'])[1] if pr else None,
                       'post_center_eligible_ROI':eligible(pr['xyxy']) is not None if pr else None})
            referencerows+=len(correspondences)
            admitted=[]
            target=modevalues['post_confirmed_plus_valid_admitted_center_assisted_identity']
            for tick in trace['observations']:
                frame=tick['frame0']
                for acceptance in tick['accepted_history']:
                    candidate_tid=acceptance['track_id'];reference_tid=postmap.get((frame,candidate_tid));previous=round(acceptance['observation_time_s']*25)
                    record={'candidate_track_id':candidate_tid,'confirmation_frame0':frame,'observation_frame0':previous,
                       'reference_track_id':reference_tid,'actual_axis_position':acceptance['axis_position'],'admitted_to_oracle':False}
                    r=rawmap.get((previous,reference_tid)) if reference_tid is not None else None
                    if r and abs(center(r['xyxy'])[1]-acceptance['axis_position'])<=.0001:
                        if reference_tid not in target[previous]:
                            target[previous][reference_tid]=acceptance['axis_position'];record['admitted_to_oracle']=True
                        else:record['reason']='REFERENCE_ALREADY_HAS_CONFIRMED_OBSERVATION'
                    else:record['reason']='NO_SAME_REFERENCE_RAW_MATCH_OR_AXIS_DOES_NOT_MATCH'
                    admitted.append(record)
            oracle_events={};observation_streams={}
            for mode,values in modevalues.items():
                events,obs=count_positions(values,p['counter']);oracle_events[mode]=events;observation_streams[mode]=obs;casepaths+=1
            actualmapped=[]
            for event in actual:
                tid=postmap.get((event['frame0'],event['track_id']));actualmapped.append({**event,'reference_track_id':tid,'direct_event_frame_spatial_match':tid is not None})
            trackrows=[];buckets=Counter()
            for tid in ids:
                framecases=[r for r in correspondences if r['reference_track_id']==tid]
                counts={mode:sum(e['track_id']==tid and e['direction']=='A->B' for e in events) for mode,events in oracle_events.items()}
                mapped=sum(e['reference_track_id']==tid and e['direction']=='A->B' for e in actualmapped)
                if mapped:bucket='ACTUAL_EVENT_HAS_DIRECT_REFERENCE_CORRESPONDENCE'
                elif counts['presence_using_reference_center']==0:bucket='MATCHED_RAW_COVERAGE_CANNOT_FORM_CURRENT_STABLE_REGIONS'
                elif counts['raw_box_center_assisted_identity']==0:bucket='RAW_CENTER_ROI_OR_STABLE_REGION_DIFFERENCE'
                elif counts['post_confirmed_plus_valid_admitted_center_assisted_identity']==0:bucket='POST_CONFIRMATION_OR_TRACK_BOX_COVERAGE_LOSS'
                else:bucket='ID_FRAGMENTATION_COUNTER_STATE_OR_UNRESOLVED_EVENT_CORRESPONDENCE'
                buckets[bucket]+=1
                postids=Counter(r['post_track_id'] for r in framecases if r['post_track_id'] is not None)
                trackrows.append({'reference_track_id':tid,'reference_box_samples':len(framecases),'raw_correspondence_samples':sum(r['raw_prediction_index'] is not None for r in framecases),
                  'post_correspondence_samples':sum(r['post_prediction_index'] is not None for r in framecases),'post_ID_frequencies':dict(postids),
                  'actual_direct_corresponding_down_events':mapped,'oracle_down_events':counts,'diagnostic_bucket':bucket,
                  'longest_stable_region_runs':{mode:{z:longest(values,tid,z) for z in ['A','B']} for mode,values in modevalues.items()}})
            case={'condition':cache['condition'],'threshold':threshold,'reference_is_GT':False,'actual_global_down_count':summary['down'],
              'actual_global_up_count':summary['up'],'actual_events_with_direct_reference_correspondence':sum(e['reference_track_id'] is not None for e in actualmapped),
              'actual_unmapped_event_count':sum(e['reference_track_id'] is None for e in actualmapped),
              'oracle_down_counts':{mode:sum(e['direction']=='A->B' for e in es) for mode,es in oracle_events.items()},
              'oracle_distinct_reference_tracks_with_down_event':{mode:len({e['track_id'] for e in es if e['direction']=='A->B'}) for mode,es in oracle_events.items()},
              'per_track_diagnostic_buckets':dict(buckets),'tracks':trackrows,'tie_optima_frame_problems':ties_total,
              'actual_events_direct_correspondence':actualmapped,'oracle_events':oracle_events,'post_admission_checks':admitted}
            folder=out/cache['condition']/('iou'+str(threshold).replace('.',''));folder.mkdir(parents=True,exist_ok=False)
            save(folder/'case.json',case);savegz(folder/'frame_correspondence.json.gz',correspondences);savegz(folder/'oracle_observations.json.gz',observation_streams)
            allcases.append({k:v for k,v in case.items() if k not in ['tracks','actual_events_direct_correspondence','oracle_events','post_admission_checks']})
        print(json.dumps({'condition_complete':cache['condition'],'down':summary['down']}),flush=True)
    assert len(allcases)==54 and casepaths==162 and referencerows==27*2*581
    result={'status':'ALL27_CACHES2_FIXED_IOU_LEVELS162_DIAGNOSTIC_ORACLE_PATHS_COMPLETE','created_host_UTC':datetime.now(timezone.utc).isoformat(),
       'protocol_sha256':sha(ROOT/'protocol/audit_v1.json'),'cached_conditions':27,'IoU_levels':[.5,.3],'cases':allcases,
       'reference_box_samples':581,'case_reference_rows':referencerows,'frame_assignment_problems':assignments,'counter_oracle_paths':162,
       'reference_is_independent_GT':False,'identity_labels_generated':False,'new_model_forwards':0,'new_training_updates':0,'board_actions':0,
       'global_pipeline_changed':False,'whole_goal_complete':False,'elapsed_s':(time.monotonic_ns()-started)/1e9}
    save(out/'summary.json',result);print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
if __name__=='__main__':main()
