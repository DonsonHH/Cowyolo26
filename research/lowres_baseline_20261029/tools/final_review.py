from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from PIL import Image
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;BOARD=PROJECT/'pynq_lowres_20261029'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    s=load(ROOT/'delivery/results/baseline/summary.json');v=load(ROOT/'results/independent_verification.json');media=load(ROOT/'results/media_verification.json');plot=load(ROOT/'results/plot_v2_verification.json')
    p1=load(ROOT/'protocol/baseline_v1.json');p2=load(ROOT/'protocol/baseline_v2_path_fix.json')
    assert s['protocol_sha256']==sha(ROOT/'protocol/baseline_v2_path_fix.json')==v['protocol_sha256']
    assert p2['supersedes_v1_sha256']==sha(ROOT/'protocol/baseline_v1.json') and p1['conditions']==p2['conditions'] and p1['prediction']==p2['prediction']
    for key in ['counter_kwargs','sizes','expected_total_detector_source_image_forwards','expected_total_tracker_updates']:assert p1[key]==p2[key]
    assert p1['videos'][0]==p2['videos'][0] and p1['videos'][1]['sha256']==p2['videos'][1]['sha256']
    assert s['actual_detector_source_image_forwards']==50700 and s['prior_completed_source_prediction_records']==44952
    assert s['resumed_new_detector_source_image_forwards']==s['predictor_inference_image_hook_count_current_resume']==5748
    assert s['prior_in_memory_predictor_hook_counter_not_recovered_after_failure'] is True and s['tracker_updates']==32808 and s['counter_paths']==72
    assert v['validation_matching_cases']==18852 and v['candidate_validation_IoUs']==20801 and v['raw_boxes_inverse_verified']==43119
    assert v['maximum_native_inverse_error']==0 and v['independent_counter_paths']==72 and v['publisher6_event_metric_conditions']==48
    assert v['event_matching_multiple_optima_conditions']==2 and v['ROI_centers_recomputed']==5971
    val={(r['model'],r['input_size']):r for r in s['validation_metrics']}
    expected_val=[[66,392,670],[626,1532,1690],[1621,1759,1770],[655,1383,1602]]
    expected_counts=[[0,0,0],[0,7,10],[1,7,8],[2,7,10]]
    for i,model in enumerate(['official','seed26','seed27','seed28']):
        assert [val[(model,size)]['matched'] for size in [192,256,320]]==expected_val[i]
        for j,size in enumerate([192,256,320]):
            row=next(r for r in s['video_metrics'] if r['scene']=='original' and r['model']==model and r['input_size']==size and r['counter']=='handoff_events')
            assert row['down']==expected_counts[i][j] and row['absolute_down_total_error']==abs(expected_counts[i][j]-12) and row['formal_event_metrics'] is None
    toros=[]
    for size in [192,256,320]:
        scores=[]
        for stride in [6,1]:
            r=next(r for r in s['video_metrics'] if r['scene']=='toros' and r['model']=='official' and r['input_size']==size and r['counter']=='handoff_events' and r['sample_stride']==stride)
            scores.append([r['formal_event_metrics'][k] for k in ['TP','FP','FN']])
        toros.append(scores)
    assert toros==[[[1,0,5],[4,0,2]],[[4,0,2],[6,0,0]],[[4,0,2],[6,0,0]]]
    assert media['full_strict_decoded_video_frames']==5886 and len(media['movies'])==3 and len(media['actual_video_frame_checks'])==12
    assert plot['bar_segments']==48 and plot['layout_repair_only'] is True and plot['original_data_and_movies_unchanged'] is True
    for archive,meta_path in [('results_delivery.tar.gz','evidence/transfer.json'),('media_delivery.tar.gz','evidence/media_transfer.json'),('plot_v2_delivery.tar.gz','evidence/plot_v2_transfer.json')]:
        info=load(ROOT/meta_path);assert sha(ROOT/archive)==info['sha256'] and (ROOT/archive).stat().st_size==info['bytes']
    jobs=(ROOT/'evidence/final_jobs.txt').read_text()
    for phrase in ['130501|cow-lowres-baseline|4gpu|FAILED|1:0|','130502|cow-lowres-v2|4gpu|FAILED|1:0|',
       '130503|cow-lowres-toros|4gpu|COMPLETED|0:0|','130504|cow-lowres-media|4gpu|COMPLETED|0:0|','130505|cow-lowres-plot-v2|4gpu|COMPLETED|0:0|']:assert phrase in jobs
    assert 'DETECTOR_FACTORIAL_REMOTE_DIRECTORY_NOT_CREATED_NO_NEW_TRAINING_ARTIFACTS' in jobs
    plan=load(PROJECT/'detector_factorial_20261029/protocol/training_v2_lowres_plan.json')
    assert plan['deploy_input_sizes']==[192,256,320] and plan['new_training_runs_planned']==15 and plan['new_training_runs_submitted']==0
    board=load(BOARD/'results/board_state_review.json')
    assert board['PYNQ_version']=='3.1.1' and board['own_benchmark_PID']==8082 and board['own_benchmark_terminal_state']=='NOT_OBSERVED'
    assert board['own_benchmark_restart_count']==0 and board['own_benchmark_results_retrieved'] is False
    assert board['current_PL_bitfile_after_benchmark']=='UNKNOWN_NOT_READ_BACK' and board['actual_live5FPS_measurement_available'] is False
    assert board['foreground_and_background_joint5FPS_proven'] is False and board['user_board_state_question_pending'] is True
    source_checks=[]
    for rel,key in [('evidence/board_sources.json','source_files'),('evidence/runtime_details.json','sources')]:
        raw=load(BOARD/rel);obj=json.loads(''.join(m['content'].get('text','') for m in raw['messages'] if m['type']=='stream'))
        for row in obj[key]:
            file=BOARD/'board_source_snapshot'/Path(row['path']).relative_to('/home/xilinx/jupyter_notebooks')
            assert sha(file)==row['sha256'];source_checks.append({'path':str(file.resolve()),'sha256':sha(file)})
    raw=load(BOARD/'evidence/release_evidence.json');obj=json.loads(''.join(m['content'].get('text','') for m in raw['messages'] if m['type']=='stream'))
    for row in obj['sources']+obj['reports']:
        file=BOARD/'board_source_snapshot'/row['relative'];assert sha(file)==row['sha256'];source_checks.append({'path':str(file.resolve()),'sha256':sha(file)})
    for old in board['past_performance_records']:
        assert old['record_type']=='historical_read_not_live_remeasurement' and sha(Path(old['source_path']))==old['source_sha256']
    assert all(k['removed'] for k in board['own_Jupyter_kernels'])
    visual=[]
    for row in media['actual_video_frame_checks']:
        file=Path(row['decoded_frame']);assert sha(file)==row['sha256']
        visual.append({'path':str(file.resolve()),'sha256':sha(file),'image_panels':4,'review':'Actuallyvieweddecodedvideoframe;allfourmodels,sourceframe/5Hzsample,ROIandcounterlabelslegible;missesretained.'})
    file=ROOT/'plot_v2_delivery/results/plots_v2/lowres_baseline_counts.png'
    visual.append({'path':str(file.resolve()),'sha256':sha(file),'image_panels':4,'review':'Actuallyviewedv2;all48valueslegible,sharedlegendandverticalannotationsremovedv1overlap;numericaldataunchanged.'})
    assert len(visual)==13 and sum(r['image_panels'] for r in visual)==52
    record=ROOT/'evidence/visual_review.json';assert not record.exists();record.write_text(json.dumps({'current_pages':visual,'current_figures_actually_viewed':13,'current_image_panels_actually_viewed':52,
    'additional_retired_v1_science_figure_viewed_and_layout_issue_repaired':True},indent=2)+'\n')
    rasters=[]
    for file in sorted(ROOT.rglob('*')):
        if file.is_file() and file.suffix.lower() in ['.png','.jpg','.jpeg']:
            with Image.open(file) as im:im.load();dims=list(im.size)
            rasters.append({'path':str(file.resolve()),'sha256':sha(file),'dimensions':dims})
    assert len(rasters)==26
    frozen=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';assert sha(frozen)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
    accepted=load(frozen);retained={frozen.relative_to(PROJECT).as_posix():sha(frozen)}
    for pk,hk in [('reference_path','reference_sha256'),('checkpoint_path','checkpoint_sha256')]:
        file=Path(accepted[pk]);assert sha(file)==accepted[hk];retained[file.relative_to(PROJECT).as_posix()]=sha(file)
    file=Path(accepted['source_event_record']['events_path']);assert sha(file)==accepted['source_event_record']['events_sha256'] and len(load(file))==12;retained[file.relative_to(PROJECT).as_posix()]=sha(file)
    docs=[ROOT/'计划与验收.md',ROOT/'低分辨率基线与5Hz计数结果.md',ROOT/'Review与当前状态.md',BOARD/'计划与当前状态.md',BOARD/'PYNQ低分辨率部署与连接核查.md',
       PROJECT/'detector_factorial_20261029/计划与验收.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for doc in docs:
        for m in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',doc.read_text(encoding='utf-8')):
            link=m.group(1) or m.group(2)
            if link.startswith(('http://','https://','#')):continue
            file=Path(unquote(link.split('#')[0]));file=file if file.is_absolute() else doc.parent/file
            assert file.exists(),(doc,link);links.append({'document':str(doc.resolve()),'link':link})
    evidence=[ROOT/'protocol/baseline_v1.json',ROOT/'protocol/baseline_v2_path_fix.json',ROOT/'results/independent_verification.json',
    ROOT/'results/media_verification.json',ROOT/'results/plot_v2_verification.json',ROOT/'results/transfer_verification.json',
    ROOT/'evidence/final_jobs.txt',ROOT/'evidence/visual_review.json',ROOT/'delivery/results/baseline/summary.json',
    ROOT/'delivery/results/baseline/resume_gate.json',ROOT/'delivery/results/baseline/baseline_counter_regression.json',
    ROOT/'results/independent_video_table.json',ROOT/'results/independent_validation_table.json',ROOT/'media_delivery/results/media/media_metadata.json',
    ROOT/'plot_v2_delivery/results/plots_v2/plot_data.json',ROOT/'plot_v2_delivery/results/plots_v2/lowres_baseline_counts.svg']
    boardevidence=[BOARD/'results/board_environment.json',BOARD/'results/board_state_review.json',BOARD/'evidence/board_inventory.json',
       BOARD/'evidence/benchmark_launch02.json',BOARD/'evidence/board_upload.json',BOARD/'evidence/serial_prompt01.json',
       BOARD/'evidence/ssh_probe01.json',BOARD/'evidence/connectivity_revalidation02.json']
    result={'status':'LOWRES12_CONDITIONS_50700_FORWARDS_72_COUNTER_PATHS_REVIEWED_WITH_UNRESOLVED_BOARD_BENCHMARK',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'offline_phase_complete':True,'board_benchmark_complete':False,'whole_goal_complete':False,
    'protocol_v1_sha256':sha(ROOT/'protocol/baseline_v1.json'),'protocol_v2_sha256':sha(ROOT/'protocol/baseline_v2_path_fix.json'),
    'input_sizes':[192,256,320],'target_frontend_Hz':5,'target_frame_period_ms':200,'model_resolution_conditions':12,
    'actual_source_detector_image_forwards':50700,'completed_source_records_reused':44952,'resume_source_forwards_directly_hooked':5748,
    'prior_failed_job_in_memory_hook_counter_not_invented':True,'all_counter_updates':32808,'independent_counter_paths':72,
    'validation_matching_cases':18852,'validation_candidate_IoUs':20801,'native_inverse_boxes':43119,'maximum_native_inverse_error':0,
    'publisher6_metric_conditions':48,'event_matching_tied_optima_retained':2,'validation_matches_4models_by3sizes':expected_val,
    'original_down_counts_4models_by3sizes':expected_counts,'Toros_official_TP_FP_FN_3sizes_by5Hz30Hz':toros,
    'all_models_sizes_counters_sampling_and_negative_results_retained':True,'new_training_updates':0,'identity_encoder_forwards':0,
    'new_lowres_training_conditions_planned':15,'new_lowres_training_conditions_submitted':0,'new_final_test':False,
    'human_confirmed12_version_preserved':True,'global_lowres_model_adoption':False,'board_inventory_live_confirmed':True,
    'PYNQ_version':'3.1.1','own_board_benchmark_PID':8082,'own_board_benchmark_terminal_state':'NOT_OBSERVED',
    'own_board_benchmark_restart_count':0,'current_PL_after_benchmark':'UNKNOWN_NOT_READ_BACK',
    'board_process_results_retrieved':False,'current_live_PYNQ_5FPS_proven':False,'foreground_background_joint_PYNQ_5FPS_proven':False,
    'user_board_state_question_pending':True,'board_source_file_records_verified':len(source_checks),'board_source_file_records':source_checks,
    'all_current13_figures_actually_viewed':True,'current_image_panels_actually_viewed':52,'all_local_rasters_fully_decoded':26,
    'three_movies_strict_decoded_frames':5886,'actual_video_frame_alignment_checks':12,'current_SVG_bar_segments_verified':48,
    'local_document_links_checked':len(links),'evidence_hashes':{f.relative_to(ROOT).as_posix():sha(f) for f in evidence},
    'board_evidence_hashes':{f.relative_to(BOARD).as_posix():sha(f) for f in boardevidence},
    'retained_artifact_hashes':retained,'documents':[{'path':str(f.resolve()),'sha256':sha(f)} for f in docs],'rasters':rasters}
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','board_evidence_hashes','board_source_file_records','retained_artifact_hashes','documents','rasters']}))
if __name__=='__main__':main()
