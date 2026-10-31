from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    p=load(ROOT/'protocol/regression_v1.json');summary=load(ROOT/'delivery/results/summary.json');check=load(ROOT/'results/local_verification.json')
    assert check['protocol_sha256']==summary['protocol_sha256']==sha(ROOT/'protocol/regression_v1.json')
    assert check['summary_sha256']==sha(ROOT/'delivery/results/summary.json')
    assert check['files']==68 and check['reference_rows']==1775 and check['reference_IDs']==9 and check['reference_events']==6
    assert check['tracker_runs']==6 and check['counter_paths']==12 and check['main_method_conditions']==8
    assert check['update_traces']==2874 and check['ROI_track_rows']==6251 and check['admitted_history']==95
    for name,checksum in p['input_modules'].items():assert sha(ROOT/'input'/name)==sha(ROOT/'delivery/input'/name)==checksum
    assert sha(ROOT/'input/publisher_gt_original.txt')==p['publisher_GT_sha256']
    assert p['source_fps']==30 and p['source_frames']==479 and p['roi_axis']=='x'
    assert p['counter']=={'lower':.4,'upper':.6,'stable_samples':3,'maximum_gap_s':2.}
    main=[r for r in summary['scores'] if r['main_method']]
    assert [r['metrics']['TP'] for r in main]==[6,6,6,6,2,2,2,3]
    assert [r['metrics']['FN'] for r in main]==[0,0,0,0,4,4,4,3]
    for row in summary['scores']:
        m=row['metrics'];assert m['FP']==0 and m['wrong_direction_matches']==0
        assert m['f1']==2*m['TP']/(2*m['TP']+m['FP']+m['FN'])
        assert m['recall']==m['TP']/6 and m['precision']==1.
        events=load(ROOT/'delivery'/row['events_path']);assert len(events)==m['predicted_events']
    new=next(r for r in summary['scores'] if r['condition_id']=='pilot_allow_lost_iou_handoff')
    assert [p['reference_events'][a['reference_index']]['track_id'] for a in new['metrics']['pairs']]==[1,7,17]
    assert [p['reference_events'][i]['track_id'] for i in new['metrics']['unmatched_reference_indices']]==[14,16,22]
    assert new['metrics']['pairs'][0]['time_error_s']==abs(110/30-125/30)
    old=next(r for r in summary['scores'] if r['condition_id']=='pilot_installed_confirmed_only');assert old['metrics']['TP']==2
    union=set()
    for folder,n in [('delivery',68),('case_delivery',19)]:
        manifest=load(ROOT/folder/'delivery_manifest.json');assert len(manifest)==n
        for item in manifest:
            f=ROOT/folder/item['path'];assert f.stat().st_size==item['bytes'] and sha(f)==item['sha256'];union.add(item['path'])
    assert len(union)==87
    cases=load(ROOT/'results/case_local_verification.json');assert cases['manual_visual_QA']=='PASS' and cases['images_full_decoded']==15 and cases['main_overlay_panels_viewed']==6
    assert cases['native_contact_images_viewed']==5 and cases['component_replays_exact']==3
    overlap=load(ROOT/'results/overlap_case_review.json');assert cases['new_case_overlap_review_sha256']==sha(ROOT/'results/overlap_case_review.json')
    assert overlap['frame']==120 and overlap['predicted_box_pair_IoU']>.85 and [r['track_ID'] for r in overlap['predictions']]==[1,8]
    assert overlap['ID1_emitted_event_frames']==[125] and not overlap['ID8_emitted_event_frames']
    assert overlap['event_FP_zero_does_not_prove_no_duplicate_track']
    for row in cases['figures']:
        f=ROOT/'figures'/row['file'];assert sha(f)==row['sha256']
        with Image.open(f) as image:image.load();assert image.size==(1920,780)
    status=(ROOT/'results/final_status.txt').read_text(encoding='utf-8')
    for job in [130293,130294]:
        line=next(s for s in status.splitlines() if s.startswith(str(job)+'|'));assert '|COMPLETED|0:0|' in line and '|4gpu|2|' in line and 'gres/gpu' not in line
    docs=[ROOT/'计划与验收.md',ROOT/'外部方法回归与结果.md',ROOT/'Review与当前状态.md',PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for doc in docs:
        text=doc.read_text(encoding='utf-8');assert '\ufffd' not in text
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            link=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',link):
                line=re.match(r'^(.*):(\d+)$',link);f=Path(line[1] if line else link);assert f.exists(),f
                if line:assert 1<=int(line[2])<=len(f.read_text(encoding='utf-8').splitlines())
                links.append(link)
    current=load(PROJECT/'lost_recovery_20261028/results/catalog_intake_verification.json');assert current['conditions']==29 and not current['source_accuracy_computed']
    result={'status':'EXTERNAL_FIXED_METHOD_REGRESSION_AND_OVERLAPPING_ID_RISK_REVIEWED',
       'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/regression_v1.json'),
       'summary_sha256':sha(ROOT/'delivery/results/summary.json'),'files_verified':87,
       'publisher_GT_rows':1775,'publisher_GT_IDs':9,'derived_reference_events':6,
       'detector_caches':2,'tracker_runs':6,'counter_paths_scored':12,'main_method_conditions':8,
       'original_full_baseline_regressions':2,'independent_exhaustive_scores':12,'update_traces':2874,
       'main_official_TP':[6,6,6,6],'main_pilot_TP':[2,2,2,3],'main_pilot_FN':[4,4,4,3],
       'all12_conditions_event_FP_and_direction_errors_zero':True,'new_pilot_match_reference_ID':1,
       'new_prediction_frame':125,'reference_frame':110,'new_match_time_error_s':.5,
       'same_cow_overlapping_prediction_IDs_observed':True,'overlap_case_frame':120,'overlapping_box_pair_IoU':overlap['predicted_box_pair_IoU'],
       'native_case_frames':5,'image_files_decoded':15,'main_overlay_panels_viewed':6,
       'source_MultiCam_29conditions_unchanged':True,'source_MultiCam_predictions':[12,11,11],
       'local_links_checked':len(links),'documents':[{'path':str(d),'sha256':sha(d)} for d in docs],
       'old_pilot_adopted_as_final_model':False,'Cows2021_three_weights_crossdomain_test_claimed':False,
       'new_independent_test':False,'new_detector_forwards':0,'training_updates':0,'MultiCam_independent_truth_received':False,
       'FPGA_execution_verified':False,'whole_goal_complete':False,'goal_should_remain_active':True,
       'previous_goal_turn_classification':'progress: Lost singlefactor control completed and allROI recoveries inspected',
       'this_goal_turn_classification':'progress: alreadyused external reference regression scored and duplicateID risk found'}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='documents'}))
if __name__=='__main__':main()
