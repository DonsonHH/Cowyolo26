from pathlib import Path
import csv,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def box_iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=lambda b:max(0,b[2]-b[0])*max(0,b[3]-b[1])
    return inter/(area(a)+area(b)-inter+1e-12)
def main():
    folder=ROOT/'delivery/results/pilot_allow_lost_iou'
    with (folder/'post_tracker_boxes.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    selected=[]
    for tid in [1,8]:
        row=next(r for r in rows if int(r['frame'])==120 and r['track_id']==str(tid))
        selected.append({'track_ID':tid,'xyxy':[float(row[k]) for k in ['x1','y1','x2','y2']],'confidence':float(row['confidence'])})
    gt=[list(map(float,row)) for row in csv.reader((ROOT/'input/publisher_gt_original.txt').open())]
    r=next(r for r in gt if int(r[0])==120 and int(r[1])==1);x,y,w,h=r[2:6];ref=[max(0,x),max(0,y),min(1920,x+w),min(1080,y+h)]
    events=load(folder/'handoff_events.json');overlap=box_iou(selected[0]['xyxy'],selected[1]['xyxy'])
    assert overlap>.5 and {e['track_id'] for e in events}=={1,18,36}
    out={'status':'NEW_EVENT_CASE_OVERLAPPING_PREDICTION_IDS_REVIEWED','frame':120,'model':'pilot','variant':'allow_lost_iou',
         'predictions':selected,'predicted_box_pair_IoU':overlap,'publisher_ID':1,'publisher_box_clipped':ref,
         'predicted_to_publisher_box_IoUs':[box_iou(s['xyxy'],ref) for s in selected],
         'ID1_emitted_event_frames':[e['frame'] for e in events if e['track_id']==1],
         'ID8_emitted_event_frames':[e['frame'] for e in events if e['track_id']==8],
         'manual_visual_observation':'Both predicted boxes overlap the same left visible cow at frame120; right visible cow is separate.',
         'event_FP_zero_does_not_prove_no_duplicate_track':True,
         'physical_identity_correctness_over_entire_clip_certified':False,'new_independent_test':False}
    path=ROOT/'results/overlap_case_review.json';assert not path.exists();path.write_text(json.dumps(out,indent=2),encoding='utf-8')
    path=ROOT/'results/case_local_verification.json';v=load(path);assert v['manual_visual_QA']=='PENDING'
    for r in v['figures']:assert sha(ROOT/'figures'/r['file'])==r['sha256']
    shutil.copyfile(path,ROOT/'results/case_local_verification_before_visual.json')
    v.update(manual_visual_QA='PASS',native_contact_images_viewed=5,main_overlay_panels_viewed=6,
          remaining_four_overlay_files_full_decoded_but_not_separately_claimed_visual_QA=True,
          new_case_overlap_review_sha256=sha(ROOT/'results/overlap_case_review.json'))
    path.write_text(json.dumps(v,indent=2),encoding='utf-8');print(json.dumps(out))
if __name__=='__main__':main()
