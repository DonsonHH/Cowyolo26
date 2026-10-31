"""Exploratory publisher-ID support for the official-model regression case."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'input'))
from confirmation_counter import ConfirmationHandoffCounter
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def iou(a,b):
    ix=max(0,min(a[2],b[2])-max(a[0],b[0]));iy=max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=lambda q:max(0,q[2]-q[0])*max(0,q[3]-q[1])
    return ix*iy/(area(a)+area(b)-ix*iy+1e-7)
def main():
    by_gt=defaultdict(dict)
    for row in csv.reader((ROOT/'input/publisher_gt_original.txt').open()):
        r=list(map(float,row));by_gt[int(r[0])][int(r[1])]=[r[2],r[3],r[2]+r[4],r[3]+r[5]]
    frames=[110,150,153,162,167,170,193,195,199,245]
    candidates=[];matrix_entries=0
    for mode in ['original_fused','firststage_pure_IoU']:
        folder=ROOT/'delivery/results'/('toros_generic__'+mode)
        with (folder/'post_tracker_boxes.csv').open(newline='') as f:post=list(csv.DictReader(f))
        obs=load(folder/'observations.json');counter=ConfirmationHandoffCounter();states=[]
        for row in obs:
            frame=row['frame0'];positions={int(k):v for k,v in row['confirmed_positions'].items()}
            tentative={int(k):v for k,v in row['tentative_positions'].items()}
            events=counter.update(frame/30,positions,tentative,row['confirmed_IDs'])
            if frame not in frames:continue
            record={'frame0':frame,'mode':mode,'source_GT_boxes':by_gt[frame],'track_support':[],'counter_states':{}}
            for r in post:
                if int(r['frame0'])!=frame or not r['track_id']:continue
                tid=int(r['track_id']);box=[float(r[k]) for k in ['x1','y1','x2','y2']]
                ranked=sorted([{'publisher_ID':g,'IoU':iou(box,b)} for g,b in by_gt[frame].items()],key=lambda v:-v['IoU'])
                matrix_entries+=len(ranked)
                record['track_support'].append({'track_ID':tid,'native_xyxy':box,'all_publisher_IoUs':ranked,
                    'best_publisher_ID':ranked[0]['publisher_ID'] if ranked else None,'best_IoU':ranked[0]['IoU'] if ranked else None})
            for tid in [5,15]:
                if tid in counter.counters and tid in counter.counters[tid].states:
                    record['counter_states'][str(tid)]=vars(counter.counters[tid].states[tid]).copy()
            record['events_now']=events;states.append(record)
        candidates.append({'mode':mode,'frames':states})
    find=lambda mode,f,tid:next(r for c in candidates if c['mode']==mode for t in c['frames'] if t['frame0']==f for r in t['track_support'] if r['track_ID']==tid)
    for frame in [150,153]:
        assert find('firststage_pure_IoU',frame,5)['best_publisher_ID']==14 and find('firststage_pure_IoU',frame,5)['best_IoU']>.75
    for frame in [162,167,170,195,199,245]:
        assert find('firststage_pure_IoU',frame,5)['best_publisher_ID']==7 and find('firststage_pure_IoU',frame,5)['best_IoU']>.75
    for frame in [150,153,167,170,195,199,245]:
        assert find('original_fused',frame,5)['best_publisher_ID']==14 and find('original_fused',frame,5)['best_IoU']>.75
    assert find('firststage_pure_IoU',167,15)['best_publisher_ID']==14
    result={'status':'PUBLISHER_ID14_TO7_TRACK_SUPPORT_CHANGE_AND_COUNTER_STATES_RECONSTRUCTED',
            'analysis_is_exploratory_after_regression':True,'publisher_GT_sha256':sha(ROOT/'input/publisher_gt_original.txt'),
            'target_algorithm_ID':5,'publisher_before_after':[14,7],'before_frames':[150,153],'after_frames':[162,167,170,195,199,245],
            'GT_overlap_matrix_entries':matrix_entries,'paired_case_records':candidates,
            'best_overlap_is_diagnostic_support_not_a_formal_ID_switch_metric':True,
            'aggregate_ID_switch_or_physical_duplicate_rate_computed':False,'new_prediction_or_reference_changed':False,
            'candidate_adopted':False,'whole_goal_complete':False}
    target=ROOT/'results/reference_case.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='paired_case_records'}))
if __name__=='__main__':main()
