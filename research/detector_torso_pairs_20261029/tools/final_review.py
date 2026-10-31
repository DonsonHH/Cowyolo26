from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from PIL import Image
import json,hashlib,gzip,re,math
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/pairs'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    p=load(ROOT/'protocol/pairs_v1.json');summary=load(OUT/'summary.json');probe=load(ROOT/'delivery/results/input_controls/summary.json')
    verify=load(ROOT/'results/independent_verification.json');inputcheck=load(ROOT/'results/input_controls_verification.json');plotcheck=load(ROOT/'results/plot_verification.json')
    assert summary['protocol_sha256']==sha(ROOT/'protocol/pairs_v1.json')
    assert probe['protocol_sha256']==sha(ROOT/'protocol/input_controls_v1.json')==inputcheck['protocol_sha256']
    assert summary['detector_actual_image_forwards']==summary['active_predictor_inference_image_calls']==13093 and probe['actual_source_image_forwards']==288
    assert summary['predictor_input_tensor_shape_counts']=={'(1, 3, 640, 384)':13093}
    assert summary['unique_source_images_hashed_and_decoded']==8380 and summary['crop_target_counts']=={'val_official':1141,'train_seed26':2920,'val_seed26':592,'val_seed27':505,'val_seed28':226}
    val=[r for r in summary['condition_summaries'] if r['split']=='val'];assert [r['matched'] for r in val]==[1141,592,505,226]
    assert [r['unmatched_references'] for r in val]==[723,1272,1359,1638]
    assert [r['unmatched_predictions'] for r in val]==[960,928,335,1330]
    assert [r['strata']['complete']['matched'] for r in val]==[544,237,226,88]
    train=next(r for r in summary['condition_summaries'] if r['split']=='train')
    assert train['references']==8888 and train['matched']==2920 and train['unmatched_references']==5968
    assert train['strata']['complete']['matched']==1281 and train['strata']['clipped']['matched']==1639
    assert verify['unique_references']==10752 and verify['reference_condition_rows']==16344 and verify['matched_crop_targets']==5384
    assert verify['one_to_one_image_assignments_verified']==13093 and verify['assignment_candidate_IoUs']==16625
    assert verify['multiple_optimal_assignment_image_cases']==0 and verify['predicted_boxes_native_inverse_verified']==11943
    assert verify['downloaded_native_case_images_pixel_verified']==18 and verify['case_selection_rules_verified']==24
    assert inputcheck['probe_source_forwards']==288 and inputcheck['pair_baseline_repeat_cases']==64
    assert inputcheck['prior320_square_sample_correspondence_cases']==48 and inputcheck['prior320_sample_all_boxes_correspond_at_IoU0999'] is True
    assert inputcheck['maximum_rotation_inverse_IoU_difference']<1e-10 and inputcheck['cached_full_validation_replays']==6
    assert inputcheck['same_source_preprocess_tensor_hashes_identical_across_all4models'] is True
    assert inputcheck['complete_reference_boxes']==919 and inputcheck['ideal_AABB_exterior_above025']==512
    probe_metrics=probe['metrics'];table=[]
    for name in ['official','seed26','seed27','seed28']:
        values=[]
        for size,rect in [(640,True),(320,True),(640,False),(320,False)]:
            r=next(r for r in probe_metrics if r['condition']==name and r['orientation']=='clockwise90' and r['imgsz']==size and r['rect']==rect and not r['repeat'])
            assert r['references']==12;values.append(r['matched'])
        table.append(values)
    assert table==[[6,3,6,5],[4,11,4,11],[2,10,2,10],[2,7,4,8]]
    decision=load(ROOT/'results/training_route_decision.json')
    assert decision['status']=='PRESERVE_COUNTING_BASELINE_AND_PRIORITIZE_INPUT_SCALE_ORIENTATION_TRAINING_BEFORE_CROP_LOCALIZER'
    assert decision['pipeline_or_weights_changed'] is False and decision['imgsz320_global_adoption'] is False and decision['localizer_training_started'] is False
    assert decision['next_training_factorial']['planned_new_training_runs']==9 and decision['next_training_factorial']['current_protocol_only_not_training_execution'] is True
    assert summary['new_training_updates']==summary['identity_encoder_forwards']==0
    assert summary['animal_identity_labels_generated'] is False and summary['candidate_final_images_accessed'] is False and summary['current_counting_pipeline_changed'] is False
    status=(ROOT/'evidence/status06.txt').read_text()
    for phrase in ['130498|cow-torso-pairs|4gpu|COMPLETED|0:0|00:09:17|','130499|cow-torso-input|4gpu|COMPLETED|0:0|00:00:13|','130500|cow-torso-plot|4gpu|COMPLETED|0:0|00:00:01|']:assert phrase in status
    for file in ['pairs-130498.err','input-130499.err','plot-130500.err']:assert (ROOT/'delivery/logs'/file).stat().st_size==0
    metadata=load(ROOT/'evidence/result_transfer.json');assert sha(ROOT/'results_delivery.tar.gz')==metadata['sha256']
    assert (ROOT/'results_delivery.tar.gz').stat().st_size==metadata['bytes'] and metadata['members']==74
    assert sha(ROOT/'evidence/main_cases_before_input_controls.json')==sha(OUT/'case_selection.json')
    assert sha(ROOT/'evidence/input_controls_summary_before_full_download.json')==sha(ROOT/'delivery/results/input_controls/summary.json')
    for relative in ['tools/run_pairs.py','tools/geometry.py','tools/input_controls.py','tools/plot_results.py','protocol/pairs_v1.json','protocol/input_controls_v1.json']:assert sha(ROOT/relative)==sha(ROOT/'delivery'/relative)
    assert plotcheck['bar_segments']==12 and plotcheck['CDF_curves']==11 and plotcheck['CDF_source_values']==4973 and plotcheck['SVG_CDF_vertices']==9935
    sheets=load(ROOT/'results/source_review_record.json');assert len(sheets['pages'])==10 and sheets['actual_image_panels']==77
    assert sheets['missed_reference_blank_slots_not_counted_as_images']==11
    visual=[];native_cache={};crop_pixels=0;warps=0
    for page in sheets['pages']:
        assert sha(Path(page['path']))==page['sha256']
        for panel in page['panels']:
            file=Path(panel['source_path']);assert sha(file)==panel['source_sha256']
            if panel['source_path'] not in native_cache:
                with Image.open(file) as im:im.load();native_cache[panel['source_path']]=im.convert('RGB')
            if panel['kind']=='actual_detector_crop':
                crop=native_cache[panel['source_path']].crop(panel['crop_box'])
                assert hashlib.sha256(crop.tobytes()).hexdigest()==panel['RGB_pixel_sha256'];crop_pixels+=1
            elif panel['kind']=='rotated_reference_visual':
                source=native_cache[panel['source_path']];warp=panel['warp'];a,b,c,d,e,f=warp['inverse_affine'];ow,oh=warp['output_size_WH']
                corners=[[a*x+b*y+c,d*x+e*y+f] for x,y in [(0,0),(ow,0),(ow,oh),(0,oh)]]
                ref=panel['reference']['full_native_quad']
                error=max(min(math.hypot(x-u,y-v) for u,v in ref) for x,y in corners);assert error<1e-8
                photo=source.transform((ow,oh),Image.Transform.AFFINE,warp['inverse_affine'],resample=Image.Resampling.BILINEAR,fillcolor=(127,127,127))
                assert hashlib.sha256(photo.tobytes()).hexdigest()==panel['RGB_pixel_sha256'];warps+=1
        visual.append({'path':page['path'],'sha256':page['sha256'],'image_panels':len(page['panels']),'review':'Actually viewed. Source/predicted crop/reference rows, allnegativeblanks, and all8fixedsizecontrols legible and corresponding.'})
    for file,n in [('reference_matching.png',2),('crop_geometry_CDF.png',3)]:
        image=ROOT/'delivery/results/plots'/file;visual.append({'path':str(image.resolve()),'sha256':sha(image),'image_panels':n,
            'review':'Actually viewed; fullcountlimits, all4models, conditionalcomplete-matchdenominators, exterior-not-backgroundscope and CDFlegends legible.'})
    assert len(visual)==12 and sum(r['image_panels'] for r in visual)==82 and crop_pixels==13 and warps==24
    file=ROOT/'evidence/visual_review.json';assert not file.exists();file.write_text(json.dumps({'pages':visual,'actually_viewed_figures':12,'actually_viewed_image_panels':82,'actual_integer_crop_pixels_rechecked':crop_pixels,'reference_warp_inverse_quad_controls':warps},indent=2)+'\n')
    rasters=[]
    for image in sorted(ROOT.rglob('*')):
        if image.is_file() and image.suffix.lower() in ['.jpg','.jpeg','.png']:
            with Image.open(image) as im:im.load();size=list(im.size)
            rasters.append({'path':str(image.resolve()),'sha256':sha(image),'dimensions':size})
    assert len(rasters)==31
    frozen=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';assert sha(frozen)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
    f=load(frozen);retained={frozen.relative_to(PROJECT).as_posix():sha(frozen)}
    for pk,hk in [('reference_path','reference_sha256'),('checkpoint_path','checkpoint_sha256')]:
        file=Path(f[pk]);assert sha(file)==f[hk];retained[file.relative_to(PROJECT).as_posix()]=sha(file)
    events=Path(f['source_event_record']['events_path']);assert sha(events)==f['source_event_record']['events_sha256'] and len(load(events))==12
    retained[events.relative_to(PROJECT).as_posix()]=sha(events)
    old=PROJECT/'crop_domain_20261029/results/final_review.json';assert sha(old)==p['previous_crop_domain_final_sha256'];retained[old.relative_to(PROJECT).as_posix()]=sha(old)
    docs=[ROOT/'计划与验收.md',ROOT/'检测框躯干配对与尺度诊断.md',ROOT/'Review与当前状态.md',
        PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for doc in docs:
        for m in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',doc.read_text(encoding='utf-8')):
            link=m.group(1) or m.group(2)
            if link.startswith(('http://','https://','#')):continue
            path=Path(unquote(link.split('#')[0]));path=path if path.is_absolute() else doc.parent/path
            assert path.exists(),(doc,link);links.append({'document':str(doc.resolve()),'link':link})
    evidence=[ROOT/'protocol/pairs_v1.json',ROOT/'protocol/input_controls_v1.json',ROOT/'results/geometry_preflight.json',
    ROOT/'results/independent_verification.json',ROOT/'results/input_controls_verification.json',ROOT/'results/plot_verification.json',
    ROOT/'results/full_cache_vs_current640.json',ROOT/'results/training_route_decision.json',ROOT/'results/transfer_verification.json',
    ROOT/'results/source_review_record.json',ROOT/'evidence/visual_review.json',ROOT/'results/case_source_pixel_verification.json',
    ROOT/'results/independent_metric_table.json',ROOT/'results/independent_crop_rows.json',ROOT/'evidence/status06.txt',
    OUT/'summary.json',OUT/'gate_before_predictions.json',OUT/'source_geometry.json.gz',OUT/'case_selection.json',OUT/'image_audit.json',
    ROOT/'delivery/results/input_controls/summary.json',ROOT/'delivery/results/input_controls/rows.json',ROOT/'delivery/results/input_controls/tensor_records.json',
    ROOT/'delivery/results/plots/plot_data.json',ROOT/'delivery/results/plots/reference_matching.svg',ROOT/'delivery/results/plots/crop_geometry_CDF.svg',
    ROOT/'tools/run_pairs.py',ROOT/'tools/geometry.py',ROOT/'tools/input_controls.py']
    result={'status':'ACTUAL_DETECTOR_TORSO_PAIRS_INPUT_SCALE_CONTROL_AND_TRAINING_PRIORITY_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'phase_complete':True,'whole_goal_complete':False,'protocol_sha256':sha(ROOT/'protocol/pairs_v1.json'),'input_control_protocol_sha256':sha(ROOT/'protocol/input_controls_v1.json'),
    'source_images':8380,'unique_reference_objects':10752,'train_references':8888,'validation_references':1864,
    'main_actual_detector_forwards':13093,'adaptive_control_actual_detector_forwards':288,'total_actual_detector_forwards':13381,
    'source_image_forwards_exclude_framework_warmup':True,'validation_four_model_matches':[r['matched'] for r in val],
    'training_matched_targets':2920,'training_unmatched_references_preserved':5968,'all_condition_reference_rows_verified':16344,
    'all_condition_crop_targets_verified':5384,'assignment_candidate_IoUs_verified':16625,'multiple_optimal_assignment_images':0,
    'first_last_baseline_repeats_verified':64,'prior320_sample_correspondences_verified':48,'fixed8_CW_table_640rect_320rect_640square_320square':table,
    'cached_replays_not_new_model_forwards':9426,'reference_complete_count':919,'ideal_AABB_exterior_above025':512,
    'all_four_models_and_all_three_seeds_retained':True,'new_training_updates':0,'identity_encoder_forwards':0,
    'global_imgsz320_replacement_adopted':False,'localizer_training_started':False,'planned_new_training_candidate_runs':9,
    'animal_identity_labels_generated':False,'native_passage_accuracy_computed':False,'actual_event_identity_accuracy_admitted':False,
    'original_human12_count_milestone_preserved':True,'new_final_test':False,'candidate_final_pixels_accessed':False,'FPGA_execution_verified':False,
    'actual_case_records':24,'case_native_images_pixel_verified':18,'all_local_rasters_decoded':31,'actually_viewed_figures':12,'actually_viewed_image_panels':82,
    'actual_crop_pixel_controls':13,'reference_warp_inverse_quad_controls':24,'SVG_bar_segments_verified':12,'SVG_CDF_curves_verified':11,
    'SVG_CDF_values_verified':4973,'SVG_CDF_vertices_verified':9935,'local_document_links_checked':len(links),
    'Slurm_jobs':{'130498':'COMPLETED0:0 main9m17s','130499':'COMPLETED0:0 input13s','130500':'COMPLETED0:0 plot1s'},
    'evidence_hashes':{file.relative_to(ROOT).as_posix():sha(file) for file in evidence},'retained_artifact_hashes':retained,
    'documents':[{'path':str(file.resolve()),'sha256':sha(file)} for file in docs],'rasters':rasters}
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','retained_artifact_hashes','documents','rasters']}))
if __name__=='__main__':main()
