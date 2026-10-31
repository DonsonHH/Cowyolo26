from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from PIL import Image
import json,hashlib,re,zlib,math
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;STUDY=ROOT/'delivery/results/study'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    protocol=load(ROOT/'protocol/study_v1.json');audit=load(ROOT/'results/input_audit.json');summary=load(STUDY/'summary.json')
    independent=load(ROOT/'results/independent_verification.json');frozen=load(STUDY/'selection_frozen.json');plot=load(ROOT/'results/plot_verification.json')
    assert protocol['conditions']==load(PROJECT/'crossdate_gallery_20261029/protocol/study_v2.json')['conditions']
    assert sha(ROOT/'protocol/study_v1.json')==audit['protocol_sha256']==summary['protocol_sha256']==independent['protocol_sha256']
    assert sha(STUDY/'selection_frozen.json')==summary['frozen_selection_sha256']==independent['frozen_selection_sha256']
    assert summary['status']=='FROZEN_VALIDATION_CROP_AND_THRESHOLD_CHOICES_WITH_ALL40_EVALUATION_CONDITIONS_COMPLETE'
    assert summary['Slurm_JOB_ID']=='130496' and summary['actual_image_forwards']==3640 and summary['new_training_updates']==0
    assert summary['validation_model_rule_conditions']==20 and summary['evaluation_model_rule_threshold_conditions']==40
    assert summary['validation_decisions']==2200 and summary['evaluation_curated_decisions']==2400 and summary['real_event_decisions']==480
    assert independent['counts']=={'dot_products':70700,'identity_scores':14140,'unique_retrieval_rows':2540,'threshold_decisions':5080}
    assert independent['validation_rule_selections_verified']==5 and independent['validation_thresholds_verified']==20
    assert independent['unique_rule_source_image_transforms_verified']==728 and independent['transform_log_rows_verified']==3640
    assert independent['previous510_P0_evaluation_tensor_hashes_exact'] is True and independent['only_validation_available_to_current_selection'] is True
    assert independent['maximum_dot_difference']<1e-12
    assert audit['total_images']==182 and audit['cross_role_pixel_duplicates']==audit['cross_role_byte_duplicates']==[]
    assert len(audit['groups']['validation_gallery'])==25
    for row in audit['groups']['validation_gallery']:
        file=Path(row['local_path']);data=file.read_bytes()
        assert sha(file)==row['sha256'] and len(data)==row['official_bytes']
        assert zlib.crc32(data)&0xffffffff==row['official_CRC32'] and hashlib.sha1(data).hexdigest()==row['official_SHA1']
    for group,rows in audit['groups'].items():
        for row in rows:assert sha(Path(row['local_path']))==row['sha256']
    direction=load(ROOT/'results/direction_audit.json');assert len(direction['pairs'])==3
    angles=[r['after_current_PIL_ROTATE90_residual_deg'] for r in direction['pairs']]
    assert all(abs(a)<25 for a in angles) and all(abs(r['after_opposite_PIL_ROTATE270_residual_deg'])>150 for r in direction['pairs'])
    choices=frozen['choices'];assert [r['selected_rule'] for r in choices]==['P0_original']*4+['P1_border08_both']
    assert frozen['evaluation_image_accesses']==0 and frozen['image_forwards_before_evaluation']==1600 and frozen['validation_image_accesses']==80
    assert all(r['all72_previous_decisions_exact'] and max(r[k] for k in ['gallery_feature_delta','labelled_query_feature_delta','real_query_feature_delta','similarity_maxdelta'])==0 for r in summary['baseline_regressions'])
    metrics=load(ROOT/'results/metric_table.json');assert len(metrics)==80
    selected=[]
    for c in choices:
        r=next(r for r in metrics if r['stage']=='evaluation' and r['condition']==c['condition'] and r['rule']==c['selected_rule'] and r['threshold_method']=='validation_calibrated')
        selected.append([r[k] for k in ['known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts']])
    assert selected==[[19,0,11,3],[14,0,16,2],[26,0,4,3],[19,0,11,1],[19,0,11,0]]
    c28=[r for r in metrics if r['stage']=='evaluation' and r['condition']=='C_letterbox_trained_seed28']
    assert next(r for r in c28 if r['rule']=='P1_border08_both' and r['threshold_method']=='original_fixed')['known_correct_accepted_C']==21
    assert next(r for r in c28 if r['rule']=='P0_original' and r['threshold_method']=='validation_calibrated')['known_correct_accepted_C']==14
    assert next(r for r in c28 if r['rule']=='P0_original' and r['threshold_method']=='original_fixed')['known_correct_accepted_C']==21
    errors=load(ROOT/'results/selected_rule_false_accept_cases.json');allerrors=load(ROOT/'results/all_false_accept_cases.json')
    assert len(errors)==9 and len({r['query_id'] for r in errors})==7 and len({r['true_anonymous_id'] for r in errors})==4 and len(allerrors)==82
    real=load(ROOT/'results/all_real_event_outcomes.json');selected_real=load(ROOT/'results/selected_rule_actual_outcomes.json')
    assert len(real)==480 and sum(r['accepted'] for r in real)==16 and all(r['verified_identity'] is False for r in real)
    accepted=[r for r in selected_real if r['accepted']]
    assert len(accepted)==1 and accepted[0]['query_id']=='E010_f9790_tid102' and accepted[0]['predicted_id']=='009'
    assert accepted[0]['condition']=='C_letterbox_trained_seed28' and accepted[0]['rule']=='P1_border08_both'
    decision=load(ROOT/'results/adoption_decision.json')
    assert decision['status']=='NO_GLOBAL_CROP_OR_THRESHOLD_REPLACEMENT_AFTER_VALIDATION_FROZEN_DEVELOPMENT_CHECK'
    assert decision['deployed_counting_or_identity_pipeline_changed'] is False and decision['per_scene_seed_override_added'] is False
    status=(ROOT/'evidence/status02.txt').read_text();plot_status=(ROOT/'evidence/plot_status_and_collection.txt').read_text()
    assert '130496|cow-crop-domain|4gpu|COMPLETED|0:0|00:00:45|' in status
    assert '130497|cow-crop-plot|4gpu|COMPLETED|0:0|00:00:02|' in plot_status
    assert (ROOT/'delivery/logs/study-130496.err').stat().st_size==0 and (ROOT/'plot_delivery/logs/plot-130497.err').stat().st_size==0
    assert plot['SVG_bar_segments_verified']==40 and plot['SVG_grid_cell_annotations_verified']==plot['SVG_grid_annotation_center_pairs']==80
    for archive_name,meta_path in [('results_delivery.tar.gz','evidence/result_transfer.json'),('plots_delivery.tar.gz','evidence/plot_transfer.json')]:
        m=load(ROOT/meta_path);assert sha(ROOT/archive_name)==m['sha256'] and (ROOT/archive_name).stat().st_size==m['bytes']
    for relative in ['tools/run_study.py','tools/crop_rules.py','protocol/study_v1.json']:assert sha(ROOT/relative)==sha(ROOT/'delivery'/relative)
    raster=[]
    for file in sorted(ROOT.rglob('*')):
        if file.is_file() and file.suffix.lower() in ['.jpg','.jpeg','.png']:
            with Image.open(file) as im:im.load();size=list(im.size)
            raster.append({'path':str(file.resolve()),'sha256':sha(file),'dimensions':size})
    assert len(raster)==56
    visual=[]
    for record_name in ['source_review_record.json','case_review_record.json']:
        record=load(ROOT/'results'/record_name)
        for page in record['pages']:
            assert sha(Path(page['path']))==page['sha256']
            for panel in page['panels']:assert sha(Path(panel['source_path']))==panel['source_sha256']
            visual.append({'path':page['path'],'sha256':page['sha256'],'image_panels':len(page['panels']),
                'review':'Actually viewed; gallery, fixed rule geometry, all selected error case pairs or sole selected real candidate with all5references legible.'})
    for relative,n in [('validation_choices_risk.png',2),('all_rules_counts.png',4)]:
        file=ROOT/'plot_delivery/results/plots'/relative
        visual.append({'path':str(file.resolve()),'sha256':sha(file),'image_panels':n,
        'review':'Actually viewed; registered and excluded counts, boththresholds and allrules/seeds readable; P3controlandselectionstarsidentified.'})
    assert len(visual)==6 and sum(r['image_panels'] for r in visual)==72
    visual_path=ROOT/'evidence/visual_review.json';assert not visual_path.exists();visual_path.write_text(json.dumps({'pages':visual,'actually_viewed_figures':6,'actually_viewed_image_panels':72},indent=2)+'\n')
    frozen_count=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';assert sha(frozen_count)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
    f=load(frozen_count);retained={frozen_count.relative_to(PROJECT).as_posix():sha(frozen_count)}
    for pathkey,hashkey in [('reference_path','reference_sha256'),('checkpoint_path','checkpoint_sha256')]:
        file=Path(f[pathkey]);assert sha(file)==f[hashkey];retained[file.relative_to(PROJECT).as_posix()]=sha(file)
    events=Path(f['source_event_record']['events_path']);assert sha(events)==f['source_event_record']['events_sha256'] and len(load(events))==12
    retained[events.relative_to(PROJECT).as_posix()]=sha(events)
    source_exclusion=PROJECT/'identity_source_provenance_20261029/results/evaluation_admission.json'
    assert load(source_exclusion)['independent_event_identity_accuracy_admitted'] is False;retained[source_exclusion.relative_to(PROJECT).as_posix()]=sha(source_exclusion)
    prior_final=PROJECT/'crossdate_gallery_20261029/results/final_review.json';assert sha(prior_final)==protocol['prior_gallery_final_sha256'];retained[prior_final.relative_to(PROJECT).as_posix()]=sha(prior_final)
    docs=[ROOT/'计划与验收.md',ROOT/'裁剪域验证与采用决策.md',ROOT/'Review与当前状态.md',
    PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for doc in docs:
        for match in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',doc.read_text(encoding='utf-8')):
            link=match.group(1) or match.group(2)
            if link.startswith(('http://','https://','#')):continue
            file=Path(unquote(link.split('#')[0]));file=file if file.is_absolute() else doc.parent/file
            assert file.exists(),(doc,link);links.append({'document':str(doc.resolve()),'link':link})
    evidence=[ROOT/'protocol/study_v1.json',ROOT/'results/input_audit.json',ROOT/'results/direction_audit.json',
    ROOT/'results/independent_verification.json',ROOT/'results/independent_validation_thresholds.json',ROOT/'results/adoption_decision.json',
    ROOT/'results/transfer_verification.json',ROOT/'results/plot_verification.json',ROOT/'results/collection_metadata_interpretation.json',
    ROOT/'results/source_review_record.json',ROOT/'results/case_review_record.json',visual_path,ROOT/'results/metric_table.json',
    ROOT/'results/all_false_accept_cases.json',ROOT/'results/selected_rule_false_accept_cases.json',ROOT/'results/all_real_event_outcomes.json',
    ROOT/'results/selected_rule_actual_outcomes.json',ROOT/'evidence/status02.txt',ROOT/'evidence/plot_status_and_collection.txt',
    STUDY/'summary.json',STUDY/'selection_frozen.json',STUDY/'access_log.json',STUDY/'accesses_at_freeze.json',
    STUDY/'tensor_log.json',STUDY/'image_transform_log.json',STUDY/'forward_batches.json',ROOT/'tools/run_study.py',ROOT/'tools/crop_rules.py',
    ROOT/'plot_delivery/results/plots/plot_data.json',ROOT/'plot_delivery/results/plots/all_rules_counts.svg',ROOT/'plot_delivery/results/plots/validation_choices_risk.svg']
    result={'status':'VALIDATION_FROZEN_CROP_THRESHOLD_40_CONDITIONS_5080_DECISIONS_AND_NONADOPTION_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'phase_complete':True,'whole_goal_complete':False,
    'protocol_sha256':sha(ROOT/'protocol/study_v1.json'),'frozen_selection_sha256':sha(STUDY/'selection_frozen.json'),
    'new_validation_gallery_images':25,'source_inputs_fully_decoded':182,'validation_model_rule_conditions':20,
    'evaluation_model_rule_threshold_conditions':40,'model_image_forwards':3640,'validation_before_gate_image_forwards':1600,
    'evaluation_after_gate_image_forwards':2040,'all_threshold_decisions_verified':5080,'scalar_dot_products_verified':70700,
    'identity_max_scores_verified':14140,'unique_crop_pixel_transforms_verified':728,'previous_P0_tensor_hashes_exact':510,
    'previous_P0_candidates_acceptances_and_features_exact':True,'all20_thresholds_and5_choices_verified':True,
    'selected_rules':[r['selected_rule'] for r in choices],'selected_evaluation_C_W_U_F':selected,
    'all_five_encoders_and_three_seeds_retained':True,'P3_control_never_selected':True,
    'all_error_model_query_threshold_pairs_preserved':82,'selected_error_pairs_reviewed':9,'selected_error_distinct_query_images':7,
    'selected_error_distinct_unknown_IDs':4,'all_actual_candidate_config_event_pairs':16,
    'selected_actual_unverified_candidates':accepted,'event_identity_accuracy_admitted':False,
    'new_independent_test':False,'actual_Aug14_queries_withAug19_gallery_retrospective':True,
    'global_crop_or_threshold_replacement_adopted':False,'current_confirmed12_count_milestone_preserved':True,
    'direction_residual_deg_three_known_source_transforms':angles,'source_identity_truth_promoted':False,
    'SVG_bar_segments_verified':40,'SVG_grid_annotation_and_quad_pairs_verified':80,'actually_viewed_figures':6,
    'actually_viewed_image_panels':72,'local_rasters_fully_decoded':len(raster),'local_document_links_checked':len(links),
    'new_training_updates':0,'new_detector_forwards':0,'real_RF_hardware_connected':False,'FPGA_execution_verified':False,
    'Slurm_jobs':{'130496':'COMPLETED0:0 CPUstudy45s','130497':'COMPLETED0:0 plot2s'},
    'evidence_hashes':{file.relative_to(ROOT).as_posix():sha(file) for file in evidence},'retained_artifact_hashes':retained,
    'documents':[{'path':str(file.resolve()),'sha256':sha(file)} for file in docs],'rasters':raster}
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','retained_artifact_hashes','documents','rasters','selected_actual_unverified_candidates']}))
if __name__=='__main__':main()
