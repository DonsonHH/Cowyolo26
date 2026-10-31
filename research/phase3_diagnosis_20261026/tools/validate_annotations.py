"""Validate source-review structure and coverage without certifying human truth."""
from pathlib import Path
from collections import Counter
import argparse,json

SOURCE_SHA='5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1'
FPS,FRAMES=25,14009

def valid_frame(x):return type(x) is int and 0<=x<FRAMES

def validate(value):
    def require(ok,message):
        if not ok:raise ValueError(message)
    require(value.get('schema_version')=='cattle-passages-v1','Unsupported schema')
    source=value.get('source',{})
    require(source.get('sha256')==SOURCE_SHA and source.get('fps')==FPS and source.get('frames')==FRAMES,'Source identity, fps or frame count changed')
    require(value.get('annotation_status')=='draft_pending_independent_review','Draft validator cannot approve or certify annotations')
    require(isinstance(value.get('reviewer'),str) and bool(value['reviewer'].strip()),'Reviewer declaration missing')
    require(value.get('blinding') in ['source_only_no_prior_predictions_declared','prior_outputs_seen'],'Blinding declaration missing')
    require(isinstance(value.get('events'),list) and isinstance(value.get('reviewed_intervals'),list),'Events and coverage must be arrays')
    ids=set();counts=Counter();coincident=Counter()
    ranges=[]
    for row in value['reviewed_intervals']:
        a,b=row.get('start_frame'),row.get('end_frame')
        require(valid_frame(a) and valid_frame(b) and a<=b,'Invalid coverage interval')
        ranges.append((a,b))
    merged=[]
    for a,b in sorted(ranges):
        if merged and a<=merged[-1][1]+1:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    uncovered=[];unreliable=[]
    for row in value['events']:
        identity=row.get('event_id');frame=row.get('source_frame');time=row.get('time_s')
        require(isinstance(identity,str) and bool(identity) and identity not in ids,'Missing or duplicate event identity')
        ids.add(identity)
        require(valid_frame(frame),'Invalid event frame')
        require(type(time) in [int,float] and abs(time-frame/FPS)<=1e-6,'Event time differs from original frame/fps')
        require(row.get('direction') in ['A->B','B->A'],'Invalid direction')
        require(row.get('completion') in ['complete','censored','uncertain'],'Invalid completion status')
        counts[row['completion']]+=1;coincident[(frame,row['direction'])]+=1
        if row['completion']=='complete' and not any(a<=frame<=b for a,b in merged):uncovered.append(identity)
        if row['completion']=='complete' and frame==14008:unreliable.append(identity)
    return {'structural_status':'PASS','reviewer_declaration':value['reviewer'],
            'blinding_declaration':value['blinding'],'events':len(ids),'event_status_counts':dict(counts),
            'merged_reviewed_intervals':merged,'covered_frames':sum(b-a+1 for a,b in merged),
            'full_video_coverage_declared':merged==[(0,FRAMES-1)],
            'complete_events_outside_declared_coverage':uncovered,
            'complete_events_on_unreliable_source_frame':unreliable,
            'coincident_event_groups_for_review':[{'source_frame':f,'direction':d,'events':n} for (f,d),n in coincident.items() if n>1],
            'frozen_reference_status':'PENDING_INDEPENDENT_REVIEW_AND_SOURCE_FRAME_CHECK',
            'scope':'Schema and declared coverage only; does not establish correctness, human authorship or independence'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('annotation',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=validate(json.loads(args.annotation.read_text(encoding='utf-8')))
    if args.output:args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))
