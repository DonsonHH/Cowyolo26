"""Read-only geometric redundancy diagnostics, never a physical cow counter."""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import combinations
import csv,hashlib,json,math
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(Path(p).open(encoding='utf-8',newline='')))
def rect(row):return [float(row[k]) for k in ['x1','y1','x2','y2']]
def overlap(a,b):
    width=max(0.,min(a[2],b[2])-max(a[0],b[0]));height=max(0.,min(a[3],b[3])-max(a[1],b[1]))
    inter=width*height;area=lambda x:max(0.,x[2]-x[0])*max(0.,x[3]-x[1])
    return inter/(area(a)+area(b)-inter) if area(a)+area(b)>inter else 0.
def unique_gt(box,gt):
    values=[(overlap(box,g['xyxy']),g['publisher_ID']) for g in gt]
    if not values:return {'ID':None,'IoU':0.,'tied':False}
    best=max(v[0] for v in values);ties=[tid for value,tid in values if abs(value-best)<=1e-12]
    return {'ID':ties[0] if len(ties)==1 else None,'IoU':best,'tied':len(ties)>1}
def link_raw(a,b,raw,threshold):
    matches=[]
    for i,x in enumerate(raw):
        ax=overlap(a['xyxy'],x['xyxy'])
        if ax<threshold or abs(a['confidence']-x['confidence'])>1e-7:continue
        for j,y in enumerate(raw):
            if i==j:continue
            by=overlap(b['xyxy'],y['xyxy'])
            if by>=threshold and abs(b['confidence']-y['confidence'])<=1e-7:
                matches.append({'raw_indices':[x['raw_index'],y['raw_index']],'tracked_raw_IoUs':[ax,by],
                                'raw_pair_IoU':overlap(x['xyxy'],y['xyxy'])})
    if not matches:return None
    return max(matches,key=lambda m:(sum(m['tracked_raw_IoUs']),-m['raw_indices'][0],-m['raw_indices'][1]))
def summarize_pairs(rows,frames=479):
    frame_set={r['frame'] for r in rows};byid=defaultdict(list)
    for r in rows:byid[tuple(r['track_IDs'])].append(r)
    episodes=[]
    for ids,items in sorted(byid.items()):
        groups=[]
        for r in sorted(items,key=lambda r:r['frame']):
            if groups and r['frame']==groups[-1][-1]['frame']+1:groups[-1].append(r)
            else:groups.append([r])
        for group in groups:
            common={'track_IDs':list(ids),'first_frame':group[0]['frame'],'last_frame':group[-1]['frame'],
             'pair_frames':len(group),'elapsed_s_first_to_last':(group[-1]['frame']-group[0]['frame'])/30,
             'primary_supported_pair_frames':sum(r['primary_same_GT'] for r in group),
             'sensitivity_supported_pair_frames':sum(r['sensitivity_same_GT'] for r in group),
             'direct_raw_duplicate_pair_frames':sum(r['direct_raw_duplicate_pair'] for r in group),
             'maximum_pair_IoU':max(r['pair_IoU'] for r in group)}
            episodes.append(common)
    return {'high_overlap_pair_frames':len(rows),'frames_with_high_overlap_ID_pairs':len(frame_set),
       'fraction_of_all_video_frames_with_pair':len(frame_set)/frames,'unique_predicted_ID_pairs':len(byid),
       'contiguous_pair_episodes':len(episodes),'longest_pair_episode_frames':max((e['pair_frames'] for e in episodes),default=0),
       'GT_primary_supported_pair_frames':sum(r['primary_same_GT'] for r in rows),
       'GT_sensitivity_supported_pair_frames':sum(r['sensitivity_same_GT'] for r in rows),
       'direct_raw_duplicate_pair_frames':sum(r['direct_raw_duplicate_pair'] for r in rows),
       'unlinked_or_lower_overlap_raw_pair_frames':sum(not r['direct_raw_duplicate_pair'] for r in rows)},episodes
def main():
    target=ROOT/'results/audit.json';assert not target.exists();target.parent.mkdir(exist_ok=True)
    p=load(ROOT/'protocol/duplicate_v1.json')
    for f in p['input_files']:assert sha(f['path'])==f['sha256'] and Path(f['path']).stat().st_size==f['bytes']
    for c in p['conditions']:
        for f in c['files'].values():assert sha(f['path'])==f['sha256'] and Path(f['path']).stat().st_size==f['bytes']
    gtfile=Path(p['input_files'][1]['path']);gtframes=defaultdict(list)
    for row in csv.reader(gtfile.open()):
        r=list(map(float,row));frame,tid=int(r[0]),int(r[1]);x,y,w,h=r[2:6];box=[max(0,x),max(0,y),min(1920,x+w),min(1080,y+h)]
        if box[2]>box[0] and box[3]>box[1]:gtframes[frame].append({'publisher_ID':tid,'xyxy':box})
    result=[];raw_records={};allpairs=[];episodes_all=[]
    summary=load(p['input_files'][0]['path'])
    for c in p['conditions']:
        rawframes=defaultdict(list)
        for row in read(c['files']['raw_detector_boxes.csv']['path']):
            f=int(row['frame']);a=rect(row)
            if .1<(a[1]+a[3])/2160<.95:
                rawframes[f].append({'raw_index':len(rawframes[f]),'xyxy':a,'confidence':float(row['confidence'])})
        if c['model'] not in raw_records:
            pairs=[]
            for f in range(479):
                for a,b in combinations(rawframes[f],2):
                    value=overlap(a['xyxy'],b['xyxy'])
                    if value>=p['high_overlap_pair_IoU_threshold']:
                        pairs.append({'frame':f,'raw_indices':[a['raw_index'],b['raw_index']],'pair_IoU':value,
                                      'xyxy_a':a['xyxy'],'xyxy_b':b['xyxy'],'confidences':[a['confidence'],b['confidence']]})
            raw_records[c['model']]={'raw_ROI_rows':sum(map(len,rawframes.values())),
                'raw_overlap_pair_frames':len(pairs),'frames_with_raw_overlap_pairs':len({r['frame'] for r in pairs}),'pairs':pairs}
        frames=defaultdict(list)
        for row in read(c['files']['post_tracker_boxes.csv']['path']):
            if row['track_id']=='':continue
            f=int(row['frame']);box=rect(row)
            if .1<(box[1]+box[3])/2160<.95:
                frames[f].append({'ID':int(row['track_id']),'xyxy':box,'confidence':float(row['confidence'])})
        pairs=[]
        for f in range(479):
            assert len(frames[f])==len({r['ID'] for r in frames[f]})
            for a,b in combinations(sorted(frames[f],key=lambda r:r['ID']),2):
                value=overlap(a['xyxy'],b['xyxy'])
                if value<p['high_overlap_pair_IoU_threshold']:continue
                a_gt=unique_gt(a['xyxy'],gtframes[f]);b_gt=unique_gt(b['xyxy'],gtframes[f])
                same=a_gt['ID'] is not None and a_gt['ID']==b_gt['ID']
                linked=link_raw(a,b,rawframes[f],p['raw_link_IoU_threshold'])
                item={'condition':c['name'],'model':c['model'],'variant':c['variant'],'frame':f,'track_IDs':[a['ID'],b['ID']],
                    'pair_IoU':value,'xyxy_a':a['xyxy'],'xyxy_b':b['xyxy'],'confidences':[a['confidence'],b['confidence']],
                    'GT_a':a_gt,'GT_b':b_gt,'primary_same_GT':same and min(a_gt['IoU'],b_gt['IoU'])>=p['GT_primary_IoU'],
                    'sensitivity_same_GT':same and min(a_gt['IoU'],b_gt['IoU'])>=p['GT_sensitivity_IoU'],
                    'raw_link':linked,'direct_raw_duplicate_pair':linked is not None and linked['raw_pair_IoU']>=p['high_overlap_pair_IoU_threshold']}
                pairs.append(item)
        stats,episodes=summarize_pairs(pairs)
        events=load(c['files']['handoff_events.json']['path']);eventindex=defaultdict(list)
        for e in events:eventindex[e['track_id']].append(e['frame'])
        for e in episodes:
            e.update(condition=c['name'],model=c['model'],variant=c['variant'],
                event_frames_per_ID_over_whole_clip=[eventindex[i] for i in e['track_IDs']],
                event_frames_per_ID_during_episode=[[f for f in eventindex[i] if e['first_frame']<=f<=e['last_frame']] for i in e['track_IDs']])
            e['both_IDs_emit_event_in_episode']=all(e['event_frames_per_ID_during_episode'])
            e['both_IDs_emit_any_event_in_clip']=all(e['event_frames_per_ID_over_whole_clip'])
        stats.update(condition=c['name'],model=c['model'],variant=c['variant'],tracked_ROI_observations=sum(map(len,frames.values())),
                     geometric_episode_with_both_IDs_emitting_events=sum(e['both_IDs_emit_event_in_episode'] for e in episodes),
                     IDpair_with_both_IDs_ever_emitting_events=len({tuple(e['track_IDs']) for e in episodes if e['both_IDs_emit_any_event_in_clip']}))
        result.append(stats);allpairs+=pairs;episodes_all+=episodes
    known=next(r for r in allpairs if r['condition']=='pilot_allow_lost_iou' and r['frame']==120 and r['track_IDs']==[1,8])
    assert abs(known['pair_IoU']-.8575113387044181)<1e-12 and known['sensitivity_same_GT'] and not known['primary_same_GT']
    record={'status':'ALL_SIX_FROZEN_TRACKER_OUTPUTS_AND_TWO_RAW_CACHES_GEOMETRIC_REDUNDANCY_AUDITED',
      'protocol_sha256':sha(ROOT/'protocol/duplicate_v1.json'),'source_summary_sha256':p['previous_summary_sha256'],
      'conditions':result,'raw_cache_metrics':raw_records,'all_high_overlap_pairs':allpairs,'episodes':episodes_all,
      'known_case_frame120':known,'frame_updates_checked':6*479,'read_only_predictions_unchanged':True,
      'physical_duplicate_track_rate_established':False,'new_independent_reference_received':False,
      'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    target.write_text(json.dumps(record,indent=2),encoding='utf-8')
    fields=list(result[0])
    with (ROOT/'results/condition_metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(result)
    fields=['condition','frame','track_ID_a','track_ID_b','pair_IoU','GT_a','GT_b','GT_a_IoU','GT_b_IoU','primary_same_GT','sensitivity_same_GT','direct_raw_duplicate_pair']
    with (ROOT/'results/overlap_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in allpairs:w.writerow({**{k:r[k] for k in ['condition','frame','pair_IoU','primary_same_GT','sensitivity_same_GT','direct_raw_duplicate_pair']},
             'track_ID_a':r['track_IDs'][0],'track_ID_b':r['track_IDs'][1],'GT_a':r['GT_a']['ID'],'GT_b':r['GT_b']['ID'],
             'GT_a_IoU':r['GT_a']['IoU'],'GT_b_IoU':r['GT_b']['IoU']})
    print(json.dumps({'conditions':result,'raw':{k:{a:b for a,b in v.items() if a!='pairs'} for k,v in raw_records.items()},
         'known_case_raw_link':known['raw_link'],'episodes':len(episodes_all)}))
if __name__=='__main__':main()
