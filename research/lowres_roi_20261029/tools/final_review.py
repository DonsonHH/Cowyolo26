from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from PIL import Image
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):assert not p.exists();p.write_text(json.dumps(obj,indent=2)+'\n')
s=load(ROOT/'delivery/results/roi/summary.json');v=load(ROOT/'results/independent_verification.json');m=load(ROOT/'results/media_verification.json')
assert s['actual_detector_source_image_forwards']==s['active_predictor_inference_image_calls']==v['raw_source_condition_ticks']==31848
assert s['new_crop_tracker_updates']==v['counter_observation_ticks']==32808 and s['new_crop_counter_paths']==v['independent_counter_paths']==72
assert v['raw_boxes_matrix_inverse_verified']==9173 and v['maximum_inverse_absolute_error']==0 and v['native_ROI_centers_recomputed']==8027
assert v['publisher6_formal_event_conditions']==48 and v['multiple_optimal_event_assignment_conditions']==0
pixel=load(ROOT/'delivery/results/pixel_independent_verification.json');assert pixel['raw_frame_crops_verified']==8 and pixel['actual_unique_NN_arrays_verified']==24 and pixel['actual_model_anchor_hash_rows_verified']==96
assert pixel['maximum_float32_absolute_difference']<=1.2e-7
assert s['baseline_full_cache_traces_exact']==36 and s['baseline_full_cache_counter_paths_exact']==72
original=[];toros=[]
for model in ['official','seed26','seed27','seed28']:
    original.append([next(r for r in s['video_metrics'] if r['scene']=='original' and r['model']==model and r['input_size']==size and r['counter']=='handoff_events')['down'] for size in [192,256,320]])
assert original==[[0,0,0],[7,8,10],[4,6,10],[8,11,11]]
for size in [192,256,320]:
    toros.append([[next(r for r in s['video_metrics'] if r['scene']=='toros' and r['model']=='official' and r['input_size']==size and r['sample_stride']==stride and r['counter']=='handoff_events')['formal_event_metrics'][k] for k in ['TP','FP','FN']] for stride in [6,1]])
assert toros==[[[4,0,2],[5,0,1]],[[3,0,3],[5,0,1]],[[3,0,3],[4,0,2]]]
for archive,transfer in [('data_delivery.tar.gz','data_transfer.json'),('media_delivery.tar.gz','media_transfer.json')]:
    meta=load(ROOT/'evidence'/transfer);assert (ROOT/archive).stat().st_size==meta['bytes'] and sha(ROOT/archive)==meta['sha256']
assert m['SVG_bars']==72 and m['input_tensor_panels_exact']==24 and m['strict_decoded_video_frames']==1962
assert m['maximum_SVG_bar_data_error']<2e-5
visual=[{'path':str((ROOT/'media_delivery/results/media/full_vs_roi_all_models.png').resolve()),'panels':9,
         'observation':'All72numbersreadable;sharedlegendseparatefromaxes;original12andToros6referencelinesvisible;negativecasesretained.'}]
for row in m['actual_decoded_video_anchor_checks']:
    file=Path(row['path']);assert sha(file)==row['sha256'];visual.append({'path':str(file.resolve()),'panels':6,
      'observation':'Actuallyopeneddecodedvideoframe;all3sizerowsandfull/cropcolumns,sourcef/heldsampleandcumulativecountslegible.'})
meta=load(ROOT/'media_delivery/results/media/media_metadata.json')
for row in meta['input_sheets']:
    file=ROOT/'media_delivery'/row['path'];assert sha(file)==row['sha256'];visual.append({'path':str(file.resolve()),'panels':5,
      'observation':'Actuallyopenedsourcecontext,fixedorientedcropand3actualNNarraysat1:1scale;originalorTorosorientationandpaddingconsistent.'})
assert len(visual)==13 and sum(r['panels'] for r in visual)==73
for row in visual:
    file=Path(row['path']);row['sha256']=sha(file)
    with Image.open(file) as image:image.load();row['dimensions']=list(image.size)
save(ROOT/'evidence/visual_review.json',{'figures_actually_viewed':13,'image_panels_actually_viewed':73,'figures':visual})
frozen=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json'
assert sha(frozen)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
accepted=load(frozen);retained={frozen.relative_to(PROJECT).as_posix():sha(frozen)}
for key,hashkey in [('reference_path','reference_sha256'),('checkpoint_path','checkpoint_sha256')]:
    f=Path(accepted[key]);assert sha(f)==accepted[hashkey];retained[f.relative_to(PROJECT).as_posix()]=sha(f)
f=Path(accepted['source_event_record']['events_path']);assert sha(f)==accepted['source_event_record']['events_sha256'] and len(load(f))==12
retained[f.relative_to(PROJECT).as_posix()]=sha(f)
docs=[ROOT/'计划与验收.md',ROOT/'固定通道裁剪与低分辨率结果.md',ROOT/'Review与当前状态.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
links=[]
for doc in docs:
    for match in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',doc.read_text(encoding='utf-8')):
        link=match.group(1) or match.group(2)
        if link.startswith(('https://','http://','#')):continue
        path=Path(unquote(link.split('#')[0]));path=path if path.is_absolute() else doc.parent/path
        assert path.exists(),(str(doc),link);links.append({'document':str(doc.resolve()),'link':link})
for name in ['collect_data.txt','collect_media.txt']:
    text=(ROOT/'evidence'/name).read_text()
    jobs=['130506','130507'] if name=='collect_data.txt' else ['130508']
    for job in jobs:assert job+'|COMPLETED|0:0|' in text
evidence=['protocol/roi_v1.json','protocol/media_and_pixel_v1.json','protocol/media_render_v1.json',
 'results/independent_verification.json','results/media_verification.json','results/data_transfer_verification.json',
 'delivery/results/roi/summary.json','delivery/results/roi/paired_full_vs_roi.json','delivery/results/roi/full_input_cache_regression_gate.json',
 'delivery/results/pixel_independent_verification.json','results/paired_full_vs_roi.csv','evidence/visual_review.json',
 'evidence/collect_data.txt','evidence/collect_media.txt','media_delivery/results/media/media_metadata.json',
 'media_delivery/results/media/full_vs_roi_all_models.svg','media_delivery/results/media/plot_data.json']
result={'status':'FIXED_LANE_CROP12_CONDITIONS31848_FORWARDS72_PATHS_AND73_VISUAL_PANELS_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'offline_phase_complete':True,'whole_goal_complete':False,
 'input_sizes':[192,256,320],'model_resolution_conditions':12,'actual_source_image_forwards':31848,
 'actual_predictor_hook_image_count':31848,'full_input_cache_regression_traces':36,'full_input_counter_regression_paths':72,
 'new_tracker_updates':32808,'independent_counter_paths':72,'native_inverse_boxes':9173,'maximum_native_inverse_error':0,
 'native_ROI_centers_verified':8027,'formal_event_conditions':48,'paired_full_vs_crop_conditions':72,
 'independent_source_crops':8,'actual_NN_input_arrays':24,'model_input_anchor_hashes':96,
 'maximum_input_float32_delta':pixel['maximum_float32_absolute_difference'],
 'original_crop_down_counts_4models_by3sizes':original,'Toros_official_crop_TP_FP_FN_3sizes_by5Hz30Hz':toros,
 'all_models_sizes_sampling_counters_and_negative_results_retained':True,'global_crop_adopted':False,
 'all_crop_conditions_restore_original12':False,'human_confirmed12_version_preserved':True,'retained_historical_evidence':retained,
 'new_training_updates':0,'new_reference_labels':0,'identity_encoder_forwards':0,'new_independent_test':False,
 'PYNQ_actions_in_this_offline_experiment':0,'PYNQ5FPS_proven':False,'actual_board_validation_in_separate_phase':True,
 'SVG_bar_count':72,'video_strict_decode_frames':1962,'video_actual_anchor_frames':4,
 'figures_actually_viewed':13,'image_panels_actually_viewed':73,'NN_input_display_panels_pixel_exact':24,
 'evidence_hashes':{r:sha(ROOT/r) for r in evidence},'documents':[{'path':str(d.resolve()),'sha256':sha(d)} for d in docs],
 'local_links_checked':len(links)}
save(ROOT/'results/final_review.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','documents','retained_historical_evidence']}))
