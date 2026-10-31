from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from PIL import Image
from collections import Counter
import json,hashlib,re,zlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bind(files):return {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files}
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    p1=load(ROOT/'protocol/study_v1.json');p2=load(ROOT/'protocol/study_v2.json');audit=load(ROOT/'results/input_audit.json')
    assert p1['conditions']==p2['conditions'] and p1['registered_IDs']==p2['registered_IDs']
    assert p2['original_protocol_sha256']==sha(ROOT/'protocol/study_v1.json')==audit['protocol_sha256']
    assert p2['numerical_gate_revision']['models_thresholds_selection_queries_same_as_v1'] is True
    assert p2['numerical_gate_revision']['new_gallery_results_from_failedattempt_examined_to_change_gate'] is False
    assert p1['old_baseline_tolerances']==p2['old_baseline_tolerances']
    for row in audit['new_images']:
        file=Path(row['local_path']);data=file.read_bytes()
        assert len(data)==row['official_bytes']==row['bytes'] and zlib.crc32(data)&0xffffffff==row['official_CRC32']
        assert hashlib.sha1(data).hexdigest()==row['official_SHA1'] and sha(file)==row['sha256']
    assert audit['full_decoded_input_images']==132 and audit['exact_cross_role_pixel_duplicate_groups']==audit['exact_cross_role_byte_duplicate_groups']==[]
    summary=load(ROOT/'delivery/results/study_v2/summary.json');assert summary['Slurm_JOB_ID']=='130423' and summary['actual_image_forwards']==660
    assert summary['new_training_updates']==summary['threshold_changes']==0 and summary['retrieval_decisions']==720
    checks=load(ROOT/'results/independent_verification.json');assert checks['verified_decisions']==720 and checks['scalar_dot_products']==21600 and checks['per_identity_max_scores']==4320
    assert checks['prior_CPU_gallery_max_feature_delta']==checks['prior_CPU_actual_query_max_feature_delta']==0
    assert checks['prior_CPU_real60_tensor_hashes_exact'] is True and checks['real_query_identity_accuracy_computed'] is False
    expected={'A_official_frozen':{'old_Aug14':[11,0,19,0,30],'new_Aug19':[12,0,18,0,29]},
    'B_letterbox_frozen':{'old_Aug14':[9,0,21,0,26],'new_Aug19':[13,0,17,2,26]},
    'C_letterbox_trained_seed26':{'old_Aug14':[23,1,6,1,28],'new_Aug19':[27,0,3,5,30]},
    'C_letterbox_trained_seed27':{'old_Aug14':[14,0,16,3,29],'new_Aug19':[19,0,11,1,28]},
    'C_letterbox_trained_seed28':{'old_Aug14':[17,0,13,0,29],'new_Aug19':[21,0,9,0,30]}}
    for row in checks['metrics']:assert [row[k] for k in ['known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts','known_closed_top1_correct']]==expected[row['condition']][row['gallery_condition']]
    newfalse=[r for r in load(ROOT/'results/all_false_accept_cases.json') if r['gallery_condition']=='new_Aug19']
    assert len(newfalse)==8 and len({r['query_id'] for r in newfalse})==6 and {r['true_anonymous_id'] for r in newfalse}=={'033','035','076'}
    actual=load(ROOT/'results/all_real_event_outcomes.json');assert len(actual)==120
    newaccepts=[r for r in actual if r['accepted'] and r['gallery_condition']=='new_Aug19']
    assert len(newaccepts)==1 and newaccepts[0]['condition']=='C_letterbox_trained_seed28' and newaccepts[0]['query_id']=='E010_f9790_tid102' and newaccepts[0]['predicted_id']=='009'
    assert all(r['verified_identity'] is False for r in actual)
    status=(ROOT/'evidence/status02.txt').read_text();plotstatus=(ROOT/'evidence/plot_status_and_collection.txt').read_text()
    assert '130422|cow-crossdate-gallery|4gpu|FAILED|1:0|00:00:10|' in status
    assert '130423|cow-crossdate-v2|4gpu|COMPLETED|0:0|00:00:10|' in status
    assert '130424|cow-gallery-plot|4gpu|COMPLETED|0:0|00:00:01|' in plotstatus
    assert (ROOT/'delivery/logs/study-130422.err').stat().st_size>0 and (ROOT/'delivery/logs/study-v2-130423.err').stat().st_size==0 and (ROOT/'plot_delivery/logs/plot-130424.err').stat().st_size==0
    firstlines=[json.loads(line) for line in (ROOT/'delivery/logs/study-130422.out').read_text().splitlines()]
    assert len(firstlines)==4 and firstlines[-1]['actual_image_forwards_so_far']==528
    failedC28=load(ROOT/'evidence/attempt01_C28_regression.json');assert failedC28['old_all60_candidate_and_acceptance_exact'] is True and failedC28['old_gallery_maximum_feature_abs_delta']>1e-5
    failed_forwards_inferred=528+30+60
    transfer=load(ROOT/'results/transfer_verification.json');plot=load(ROOT/'results/plot_verification.json')
    assert transfer['members']==128 and plot['members']==7 and plot['SVG_segments_verified']==40
    for name,meta_path in [('results_delivery.tar.gz','evidence/result_transfer.json'),('plots_delivery.tar.gz','evidence/plot_transfer.json')]:
        meta=load(ROOT/meta_path);assert sha(ROOT/name)==meta['sha256'] and (ROOT/name).stat().st_size==meta['bytes']
    raster=[]
    for f in sorted(ROOT.rglob('*')):
        if f.is_file() and f.suffix.lower() in ['.jpg','.jpeg','.png']:
            with Image.open(f) as im:im.load();size=list(im.size)
            raster.append({'path':str(f.resolve()),'sha256':sha(f),'dimensions':size})
    sources=load(ROOT/'results/source_review_record.json');assert len(sources['pages'])==3 and sources['actual_image_panels']==52
    visual=[]
    for page in sources['pages']:
        assert sha(Path(page['file']))==page['sha256']
        for panel in page['panels']:assert sha(Path(panel['path']))==panel['sha256']
        visual.append({'path':page['file'],'sha256':page['sha256'],'actual_image_panels':len(page['panels']),
            'review':'Actually viewed; native gallery IDs, all new false accepts, query and all5ID009reference images legible and correctly paired.'})
    f=ROOT/'plot_delivery/results/plots/gallery_date_risk.png';visual.append({'path':str(f.resolve()),'sha256':sha(f),'actual_image_panels':2,'review':'Actually viewed; all10pairedrows, complete0to30axisandfalseacceptcounts, labels and legend legible.'})
    assert sum(r['actual_image_panels'] for r in visual)==54
    visual_path=ROOT/'evidence/visual_review.json';assert not visual_path.exists();visual_path.write_text(json.dumps({'pages':visual,'actually_viewed_pages':4,'actually_viewed_image_panels':54},indent=2)+'\n')
    frozen=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';accepted=load(frozen)
    assert sha(frozen)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
    retained={frozen.relative_to(PROJECT).as_posix():sha(frozen)}
    for pathkey,hashkey in [('reference_path','reference_sha256'),('checkpoint_path','checkpoint_sha256')]:
        file=Path(accepted[pathkey]);assert sha(file)==accepted[hashkey];retained[file.relative_to(PROJECT).as_posix()]=sha(file)
    er=accepted['source_event_record'];events=Path(er['events_path']);assert sha(events)==er['events_sha256']
    eventlist=load(events);assert len(eventlist)==12;retained[events.relative_to(PROJECT).as_posix()]=sha(events)
    exclusion=PROJECT/'identity_source_provenance_20261029/results/evaluation_admission.json'
    assert sha(exclusion)==p2['source_pair_exclusion_sha256'] and load(exclusion)['independent_event_identity_accuracy_admitted'] is False
    retained[exclusion.relative_to(PROJECT).as_posix()]=sha(exclusion)
    docs=[ROOT/'计划与验收.md',ROOT/'跨日期图库与真实抓拍身份结果.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for doc in docs:
        for match in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',doc.read_text(encoding='utf-8')):
            link=match.group(1) or match.group(2)
            if link.startswith(('http://','https://','#')):continue
            path=Path(unquote(link.split('#')[0]));path=path if path.is_absolute() else doc.parent/path
            assert path.exists(),(doc,link);links.append({'document':str(doc.resolve()),'link':link})
    evidence=[ROOT/'protocol/study_v1.json',ROOT/'protocol/study_v2.json',ROOT/'results/input_audit.json',ROOT/'results/independent_verification.json',
    ROOT/'results/transfer_verification.json',ROOT/'results/plot_verification.json',ROOT/'results/source_review_record.json',visual_path,
    ROOT/'results/all_false_accept_cases.json',ROOT/'results/all_real_event_outcomes.json',ROOT/'results/paired_identity_outcomes.json',
    ROOT/'evidence/status01.txt',ROOT/'evidence/status02.txt',ROOT/'evidence/plot_status_and_collection.txt',
    ROOT/'delivery/results/study_v2/summary.json',ROOT/'delivery/tools/run_study.py',ROOT/'delivery/tools/run_study_v2.py',
    ROOT/'delivery/logs/study-130422.out',ROOT/'delivery/logs/study-130422.err',ROOT/'delivery/logs/study-v2-130423.out',ROOT/'delivery/logs/study-v2-130423.err',
    ROOT/'plot_delivery/results/plots/plot_data.json',ROOT/'plot_delivery/results/plots/gallery_date_risk.svg']
    result={'status':'FIXED5_ENCODERS_TWO_DATE_GALLERIES_720_DECISIONS_AND_ALL_FALSE_ACCEPT_CASES_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'phase_complete':True,'whole_goal_complete':False,
    'protocol_v1_sha256':sha(ROOT/'protocol/study_v1.json'),'protocol_v2_sha256':sha(ROOT/'protocol/study_v2.json'),
    'new_gallery_images':30,'decoded_distinct_input_positions':132,'paired_model_gallery_conditions':10,
    'labelled_queries':60,'registered_queries':30,'gallery_excluded_queries':30,'actual_event_query_images':12,
    'actual_successful_run_image_forwards':660,'failed_run_image_forwards_inferred_from_logged_stop_and_source':failed_forwards_inferred,
    'combined_model_attempt_image_forwards':660+failed_forwards_inferred,'retrieval_decisions':720,'scalar_dot_products_verified':21600,'identity_scores_verified':4320,
    'old_CPU_gallery_and60_actual_query_feature_maxdelta':0,'old_GPU_all300_predictions_acceptances_exact':True,'prior_CPU_actual_query_tensor_hashes_exact':True,
    'model_thresholds_and_queries_unchanged':True,'numerical_gate_failure_and_revision_preserved':True,
    'all_five_models_reported':True,'new_gallery_C26_C_W_U_unknownFAR':[27,0,3,5],'new_unknown_false_accept_case_model_query_pairs':8,
    'new_unknown_false_accept_distinct_query_images':6,'new_unknown_false_accept_distinct_IDs':3,
    'new_real_accepted_candidates':newaccepts,'event_identity_accuracy_admitted':False,'new_gallery_later_than_original_source_disclosed':True,
    'new_independent_test':False,'real_RF_or_eartag_mapping_proven':False,'new_training_updates':0,'new_detector_forwards':0,
    'current_confirmed12_count_milestone_preserved':True,'FPGA_execution_verified':False,'local_rasters_fully_decoded':len(raster),
    'actually_viewed_figures':4,'actually_viewed_image_panels':54,'SVG_bar_segments_verified':40,
    'Slurm_jobs':{'130422':'FAILED1:0 numericgatepreserved','130423':'COMPLETED0:0CPUstudy','130424':'COMPLETED0:0scientificplot'},
    'local_document_links_checked':len(links),'evidence_hashes':bind(evidence),'retained_artifact_hashes':retained,
    'documents':[{'path':str(p.resolve()),'sha256':sha(p)} for p in docs],'rasters':raster}
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','retained_artifact_hashes','documents','rasters','new_real_accepted_candidates']}))
if __name__=='__main__':main()
