from pathlib import Path
from collections import defaultdict
import csv,json,numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    record=load(ROOT/'results/reference_case.json');by_gt=defaultdict(dict);count=0;maxerror=0.
    for row in csv.reader((ROOT/'input/publisher_gt_original.txt').open()):
        r=list(map(float,row));by_gt[int(r[0])][int(r[1])]=[r[2],r[3],r[2]+r[4],r[3]+r[5]]
    for mode in record['paired_case_records']:
        path=ROOT/'delivery/results'/('toros_generic__'+mode['mode'])/'post_tracker_boxes.csv'
        with path.open(newline='') as f:post=list(csv.DictReader(f))
        for case in mode['frames']:
            frame=case['frame0'];assert {int(k):v for k,v in case['source_GT_boxes'].items()}==by_gt[frame]
            for trace in case['track_support']:
                actual=next(r for r in post if int(r['frame0'])==frame and r['track_id']==str(trace['track_ID']))
                a=np.asarray([float(actual[k]) for k in ['x1','y1','x2','y2']],float);assert a.tolist()==trace['native_xyxy']
                ids=list(by_gt[frame]);b=np.asarray(list(by_gt[frame].values()),float)
                extent=np.maximum(0,np.minimum(a[2:],b[:,2:])-np.maximum(a[:2],b[:,:2]));intersection=extent.prod(axis=1)
                union=np.maximum(0,a[2:]-a[:2]).prod()+np.maximum(0,b[:,2:]-b[:,:2]).prod(axis=1)-intersection
                values=intersection/(union+1e-7);expected=dict(zip(ids,values))
                for r in trace['all_publisher_IoUs']:
                    error=abs(expected[r['publisher_ID']]-r['IoU']);assert error<1e-12;maxerror=max(maxerror,float(error));count+=1
                best=max(expected,key=expected.get);assert trace['best_publisher_ID']==best and abs(trace['best_IoU']-expected[best])<1e-12
    assert count==record['GT_overlap_matrix_entries']==175
    result={'status':'PUBLISHER_REFERENCE_CASE_175_OVERLAPS_VECTORIZED_INDEPENDENTLY_VERIFIED',
            'IoU_entries':count,'maximum_difference':maxerror,'exploratory_case_not_formal_ID_switch_metric':True,
            'candidate_adopted':False,'whole_goal_complete':False}
    path=ROOT/'results/reference_case_verification.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
