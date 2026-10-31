from pathlib import Path
from PIL import Image
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=load(ROOT/'protocol/regression_v1.json');s=load(ROOT/'delivery/results/summary.json')
    v=load(ROOT/'results/independent_verification.json');media=load(ROOT/'results/media_verification.json')
    case=load(ROOT/'results/reference_case_verification.json');focus=load(ROOT/'results/failure_focus_record.json')
    visual=load(ROOT/'evidence/visual_review.json');decision=load(ROOT/'results/adoption_decision.json')
    jobs=[('130351','firststage-iou-regression','status_01.txt','00:00:22','regression_130351'),
          ('130352','firststage-paired-media','render_status_03.txt','00:03:59','render_130352')]
    for ID,name,file,elapsed,prefix in jobs:
        text=(ROOT/'evidence'/file).read_text(encoding='utf-8')
        assert re.search(ID+r'\s+'+name+r'\s+cu\s+COMPLETED\s+0:0\s+'+elapsed,text)
        assert (ROOT/'evidence'/(prefix+'.err')).stat().st_size==0
        assert 'Traceback' not in (ROOT/'evidence'/(prefix+'.out')).read_text(encoding='utf-8')
    assert sha(ROOT/'protocol/regression_v1.json')==s['protocol_sha256']=='648d3f7d226fff6885245bdcd137c5bfcab9f0ecf263650f02965bcc2a985450'
    for folder,archive,record,manifest,expected in [
      ('delivery','regression_delivery.tar.gz','delivery_record.json','delivery_manifest.json',140),
      ('media_delivery','media_delivery.tar.gz','media_delivery_record.json','media_delivery_manifest.json',68)]:
        metadata=load(ROOT/'evidence'/record);file=ROOT/archive
        assert file.stat().st_size==metadata['archive_bytes'] and sha(file)==metadata['archive_sha256']
        rows=load(ROOT/folder/manifest)['files'];assert len(rows)==expected and metadata['files']==expected+1
        for r in rows:
            path=ROOT/folder/r['file'];assert path.stat().st_size==r['bytes'] and sha(path)==r['sha256']
    assert sha(ROOT/'tools/replay.py')==sha(ROOT/'delivery/tools/replay.py')
    assert sha(ROOT/'tools/render.py')==sha(ROOT/'media_delivery/tools/render.py')
    assert s['full_tracker_runs']==v['tracker_runs']==18 and s['counter_paths']==v['counter_paths']==36
    assert s['total_tracker_updates']==v['observation_ticks']==31166 and v['counter_interface_ticks']==62332
    assert v['native_ROI_centers_verified']==9027 and v['ROI_box_pair_IoUs_verified']==6367 and v['ROI_overlap_candidate_rows']==69
    assert len(v['reference_scored_paths'])==8 and v['baseline_gate_conditions']==9
    assert case['IoU_entries']==175 and case['maximum_difference']==0
    main_rows=[]
    for source in p['sources']:
        values=[]
        for variant in p['variants']:
            condition=next(r for r in s['conditions'] if r['source']==source['name'] and r['variant']==variant)
            windows=[r for r in condition['window_counters'] if r['counter']=='confirmation_handoff']
            ab=sum(w['down'] for w in windows);ba=sum(w['up'] for w in windows)
            values.append([ab,ba])
            if source['scene']!='toros_used_reverse':assert all(w['formal_event_metrics'] is None for w in windows)
        main_rows.append({'source':source['name'],'scene':source['scene'],'before_A_to_B_B_to_A':values[0],'after_A_to_B_B_to_A':values[1]})
    assert [r['after_A_to_B_B_to_A'][0] for r in main_rows if r['scene']=='original_clip']==[12,11,11]
    assert [r['after_A_to_B_B_to_A'][0] for r in main_rows if r['scene']=='new_long']==[0,12,12,12]
    assert [r['after_A_to_B_B_to_A'][1] for r in main_rows if r['scene']=='toros_used_reverse']==[5,4]
    assert decision['status']=='FIRSTSTAGE_PURE_IOU_GLOBAL_REPLACEMENT_NOT_ADOPTED_AFTER_PAIRED_REGRESSION'
    assert decision['candidate_global_replacement_adopted'] is False and decision['posthoc_scene_or_seed_specific_switching_added'] is False
    assert decision['summary_sha256']==sha(ROOT/'delivery/results/summary.json')
    assert decision['independent_verification_sha256']==sha(ROOT/'results/independent_verification.json')
    assert decision['toros_official_TP_FP_FN_before_after']==[[6,0,0],[5,0,1]]
    assert media['movie_count']==9 and media['decoded_frames']==8444 and media['raster_count']==47 and media['native_source_images']==16
    for row in media['movies']:assert row['local_strict_full_decode']=='PASS' and sha(Path(row['absolute_path']))==row['sha256']
    for row in media['rasters']:
        path=Path(row['path']);assert sha(path)==row['sha256']
        with Image.open(path) as im:im.verify()
    assert visual['actual_sheets_viewed']==32 and visual['actual_panels_viewed']==66
    assert len(visual['sheets'])==31 and sum(r['predefined_anchor'] for r in visual['sheets'])==22
    for row in visual['sheets']:assert row['actual_visual_review']=='PASS' and sha(Path(row['absolute_path']))==row['sha256']
    figure=Path(focus['figure_path']);assert sha(figure)==focus['figure_sha256']==visual['failure_focus_figure']['sha256']
    assert visual['failure_focus_figure']['actual_visual_review']=='PASS' and len(focus['panels'])==4
    for r in focus['panels']:assert sha(Path(r['native_path']))==r['native_sha256']
    with Image.open(figure) as im:assert list(im.size)==focus['dimensions'];im.verify()
    retained={
      'human_count_confirmation_20261028/evidence/user_confirmation.json':'fe8a895cd6ac71815ff8e2f6ad8d932a6453c41971b6b7a18ea9c2f743dd0f9f',
      'human_count_confirmation_20261028/results/frozen_development_candidate.json':p['current_confirmed12_candidate_sha256'],
      'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json':p['current_29_condition_catalog_sha256'],
      'overhead_positive_reference_20261028/reference/assistant_event_draft_v1.json':p['new_long_draft_sha256'],
      'event_timing_refinement_20261029/reference/assistant_event_timing_v2.json':p['new_long_timing_draft_sha256'],
      'long_video_track_gap_20261029/results/final_review.json':p['prior_candidate_review_sha256'],
      'overhead_long_session_20261028/input/2023-08-17T13-25-38.mp4':'8210a5bf206dd7f2356bc3d4653b439ab6de12ccfdc8209fe301ac7f02807058',
      'phase3_diagnosis_20261026/inputs/multicam_original.mp4':'5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1'}
    for relative,digest in retained.items():assert sha(PROJECT/relative)==digest
    accepted=load(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json')
    assert accepted['predicted_down']==accepted['human_total']==12 and accepted['absolute_total_error']==0
    docs=[ROOT/'计划与验收.md',ROOT/'多seed与反向回归结果及采用决策.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text and '\r\r' not in text
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            target=unquote(match[1] or match[2])
            if re.match(r'^[A-Za-z]:[/\\]',target):assert Path(target).exists(),target;links.append(target)
    evidence=['protocol/regression_v1.json','protocol/media_v1.json','results/independent_verification.json',
        'results/reference_case.json','results/reference_case_verification.json','results/media_verification.json',
        'results/failure_focus_record.json','results/adoption_decision.json','evidence/visual_review.json',
        'evidence/status_01.txt','evidence/render_status_03.txt','evidence/delivery_record.json','evidence/media_delivery_record.json']
    result={'status':'FIRSTSTAGE_IOU_NINE_SOURCE_REGRESSION_AND_GLOBAL_NONADOPTION_REVIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'jobs_completed':['130351','130352'],'job_exit_codes':['0:0','0:0'],
            'fixed_sources':9,'full_tracker_runs':18,'exact_baseline_gate_conditions':9,'counter_paths':36,
            'tracker_update_ticks':31166,'counter_interface_update_ticks':62332,'native_ROI_centers_verified':9027,
            'ROI_pair_IoUs_verified':6367,'high_overlap_candidate_pair_ticks':69,'reference_scored_paths':8,
            'reference_rows_independently_derived':1775,'publisher_reference_events':6,'exploratory_reference_case_IoUs':175,
            'main_result_rows':main_rows,'toros_official_TP_FP_FN_before_after':[[6,0,0],[5,0,1]],
            'toros_pilot_TP_FP_FN_before_after':[[2,0,4],[4,0,2]],
            'movies_fully_decoded':9,'movie_frames_fully_decoded':8444,'native_source_images':16,'raster_files_checked':48,
            'case_sheets_actually_viewed':32,'case_panels_actually_viewed':66,'predefined_paired_case_sheets':22,
            'exploratory_paired_case_sheets':9,'focused_reference_figure_panels':4,'local_links_checked':len(links),
            'regression_archive_members':141,'media_archive_members':69,'candidate_global_replacement_adopted':False,
            'current_confirmed12_candidate_preserved':True,'prior_results_and_new_long_drafts_preserved':True,
            'new_long_reference_final_scoring_eligible':False,'posthoc_scene_or_seed_specific_switching_added':False,
            'new_independent_test':False,'new_detector_forwards':0,'new_training_updates':0,
            'FPGA_execution_verified':False,'whole_goal_complete':False,
            'evidence_hashes':{x:sha(ROOT/x) for x in evidence},'retained_artifact_hashes':retained,
            'documents':[{'path':str(path.resolve()),'sha256':sha(path)} for path in docs],
            'rasters':media['rasters']+[{'path':str(figure),'sha256':sha(figure)}]}
    target=ROOT/'results/final_review.json';assert not target.exists();target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['main_result_rows','evidence_hashes','retained_artifact_hashes','documents','rasters']}))
if __name__=='__main__':main()
