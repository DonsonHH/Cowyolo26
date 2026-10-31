"""Independent matrix geometry and set-based episode reconstruction."""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import permutations
import csv,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(Path(p).open(encoding='utf-8',newline='')))
def matrix(a,b):
    a=np.asarray(a,np.float64).reshape(-1,4);b=np.asarray(b,np.float64).reshape(-1,4)
    intersection=np.maximum(0.,np.minimum(a[:,None,2:],b[None,:,2:])-np.maximum(a[:,None,:2],b[None,:,:2])).prod(2)
    area_a=np.maximum(0.,a[:,2:]-a[:,:2]).prod(1);area_b=np.maximum(0.,b[:,2:]-b[:,:2]).prod(1)
    union=area_a[:,None]+area_b[None,:]-intersection
    return np.divide(intersection,union,out=np.zeros_like(intersection),where=union>0)
def main():
    target=ROOT/'results/independent_verification.json';assert not target.exists()
    p=load(ROOT/'protocol/duplicate_v1.json');a=load(ROOT/'results/audit.json')
    assert a['protocol_sha256']==sha(ROOT/'protocol/duplicate_v1.json')
    for row in p['input_files']:assert sha(row['path'])==row['sha256']
    gt=defaultdict(list)
    for row in csv.reader(Path(p['input_files'][1]['path']).open()):
        r=list(map(float,row));x,y,w,h=r[2:6];rect=np.maximum([0.,0.,-np.inf,-np.inf],[x,y,x+w,y+h]);rect[2:]=np.minimum(rect[2:],[1920,1080])
        if np.all(rect[2:]>rect[:2]):gt[int(r[0])].append((int(r[1]),rect.tolist()))
    records={(r['condition'],r['frame'],*r['track_IDs']):r for r in a['all_high_overlap_pairs']}
    assert len(records)==len(a['all_high_overlap_pairs'])==75
    verified=set();matrix_entries=0;sourcechecks={};raw_counts={};episodes=[];maxerr=0.
    for c in p['conditions']:
        for item in c['files'].values():assert sha(item['path'])==item['sha256'];sourcechecks[item['path']]=item['sha256']
        pred=defaultdict(list);raw=defaultdict(list)
        for row in read(c['files']['post_tracker_boxes.csv']['path']):
            rect=[float(row[k]) for k in ['x1','y1','x2','y2']]
            if row['track_id'] and .1<(rect[1]+rect[3])/2160<.95:pred[int(row['frame'])].append((int(row['track_id']),rect,float(row['confidence'])))
        for row in read(c['files']['raw_detector_boxes.csv']['path']):
            rect=[float(row[k]) for k in ['x1','y1','x2','y2']]
            if .1<(rect[1]+rect[3])/2160<.95:raw[int(row['frame'])].append((rect,float(row['confidence'])))
        raw_pair_count=0;raw_frames=set();conditionpairs=[];pairframes=defaultdict(set)
        for f in range(479):
            people=sorted(pred[f],key=lambda r:r[0]);pb=[r[1] for r in people];rb=[r[0] for r in raw[f]]
            pair_m=matrix(pb,pb);raw_m=matrix(rb,rb);link_m=matrix(pb,rb);gt_m=matrix(pb,[r[1] for r in gt[f]])
            matrix_entries+=pair_m.size+raw_m.size+link_m.size+gt_m.size
            rawedges=np.argwhere(np.triu(raw_m>=.5,k=1));raw_pair_count+=len(rawedges)
            if len(rawedges):raw_frames.add(f)
            edges=np.argwhere(np.triu(pair_m>=.5,k=1))
            for i,j in edges:
                key=(c['name'],f,people[i][0],people[j][0]);assert key in records;r=records[key];verified.add(key)
                err=abs(float(pair_m[i,j])-r['pair_IoU']);maxerr=max(maxerr,err);assert err<1e-12
                geoinfo=[]
                for index,label in [(i,'GT_a'),(j,'GT_b')]:
                    scores=gt_m[index]
                    if not len(scores):info={'ID':None,'IoU':0.,'tied':False}
                    else:
                        best=float(scores.max());ids=[gt[f][q][0] for q in np.flatnonzero(abs(scores-best)<=1e-12)]
                        info={'ID':ids[0] if len(ids)==1 else None,'IoU':best,'tied':len(ids)>1}
                    assert info['ID']==r[label]['ID'] and info['tied']==r[label]['tied'] and abs(info['IoU']-r[label]['IoU'])<1e-12
                    geoinfo.append(info)
                same=geoinfo[0]['ID'] is not None and geoinfo[0]['ID']==geoinfo[1]['ID']
                assert r['primary_same_GT']==(same and min(g['IoU'] for g in geoinfo)>=.5)
                assert r['sensitivity_same_GT']==(same and min(g['IoU'] for g in geoinfo)>=.3)
                links=[]
                for q,z in permutations(range(len(raw[f])),2):
                    if link_m[i,q]>=.9 and link_m[j,z]>=.9 and abs(people[i][2]-raw[f][q][1])<=1e-7 and abs(people[j][2]-raw[f][z][1])<=1e-7:
                        links.append((float(link_m[i,q]+link_m[j,z]),-q,-z,q,z))
                if not links:assert r['raw_link'] is None and not r['direct_raw_duplicate_pair']
                else:
                    _,_,_,q,z=max(links);assert r['raw_link']['raw_indices']==[q,z]
                    assert abs(r['raw_link']['raw_pair_IoU']-raw_m[q,z])<1e-12
                    assert np.max(abs(np.array(r['raw_link']['tracked_raw_IoUs'])-[link_m[i,q],link_m[j,z]]))<1e-12
                    assert r['direct_raw_duplicate_pair']==(raw_m[q,z]>=.5)
                conditionpairs.append(r);pairframes[(people[i][0],people[j][0])].add(f)
        previous=a['raw_cache_metrics'][c['model']]
        assert previous['raw_overlap_pair_frames']==raw_pair_count and previous['frames_with_raw_overlap_pairs']==len(raw_frames)
        raw_counts[c['model']]={'raw_pair_frames':raw_pair_count,'sourceframes_with_pairs':len(raw_frames)}
        metric=next(r for r in a['conditions'] if r['condition']==c['name'])
        assert metric['high_overlap_pair_frames']==len(conditionpairs) and metric['frames_with_high_overlap_ID_pairs']==len({r['frame'] for r in conditionpairs})
        assert metric['tracked_ROI_observations']==sum(map(len,pred.values()))
        assert metric['GT_primary_supported_pair_frames']==sum(r['primary_same_GT'] for r in conditionpairs)
        assert metric['GT_sensitivity_supported_pair_frames']==sum(r['sensitivity_same_GT'] for r in conditionpairs)
        assert metric['direct_raw_duplicate_pair_frames']==sum(r['direct_raw_duplicate_pair'] for r in conditionpairs)
        prior_episodes={(tuple(e['track_IDs']),e['first_frame'],e['last_frame']):e for e in a['episodes'] if e['condition']==c['name']}
        expected_episodes=[];events=load(c['files']['handoff_events.json']['path'])
        for pair,frames in pairframes.items():
            starts=sorted(f for f in frames if f-1 not in frames)
            for start in starts:
                end=start
                while end+1 in frames:end+=1
                key=(pair,start,end);assert key in prior_episodes;e=prior_episodes[key];expected_episodes.append(key)
                assert e['pair_frames']==end-start+1 and e['elapsed_s_first_to_last']==(end-start)/30
                for index,identity in enumerate(pair):
                    emitted=[x['frame'] for x in events if x['track_id']==identity]
                    assert e['event_frames_per_ID_over_whole_clip'][index]==emitted
                    assert e['event_frames_per_ID_during_episode'][index]==[f for f in emitted if start<=f<=end]
                assert e['both_IDs_emit_event_in_episode']==all(e['event_frames_per_ID_during_episode'])
                assert e['both_IDs_emit_any_event_in_clip']==all(e['event_frames_per_ID_over_whole_clip'])
        assert len(expected_episodes)==len(prior_episodes)==metric['contiguous_pair_episodes'];episodes+=expected_episodes
    assert verified==set(records) and len(episodes)==len(a['episodes'])==48
    r={'status':'ALL2874_CONDITION_FRAMES_75_OVERLAP_PAIRS_AND_48_EPISODES_INDEPENDENTLY_VERIFIED',
       'protocol_sha256':sha(ROOT/'protocol/duplicate_v1.json'),'audit_sha256':sha(ROOT/'results/audit.json'),
       'conditions':6,'condition_frames':2874,'high_overlap_pair_frames':75,'episode_count':48,
       'all_IoU_matrix_entries_recomputed':matrix_entries,'maximum_pair_IoU_difference':maxerr,
       'distinct_bound_condition_artifacts':len(sourcechecks),'raw_cache_counts':raw_counts,
       'source_inputs_SHA_preserved':True,'method_predictions_unchanged':True,
       'physical_duplicate_track_rate_established':False,'new_independent_reference':False,
       'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    target.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
if __name__=='__main__':main()
