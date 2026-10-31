from pathlib import Path
from PIL import Image
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=load(ROOT/'protocol/stream_v1.json');s=load(ROOT/'delivery/results/summary.json');v=load(ROOT/'results/independent_verification.json')
    plots=load(ROOT/'results/plot_verification.json');visual=load(ROOT/'evidence/visual_review.json')
    for ID,name,log,elapsed,prefix in [('130362','confirmed12-rf-stream','status_02.txt','00:02:19','run_130362'),
                                    ('130363','confirmed12-rf-plots','plots_status_01.txt','00:00:02','plots_130363')]:
        assert re.search(ID+r'\s+'+name+r'\s+cu\s+COMPLETED\s+0:0\s+'+elapsed,(ROOT/'evidence'/log).read_text())
        assert (ROOT/'evidence'/(prefix+'.err')).stat().st_size==0 and 'Traceback' not in (ROOT/'evidence'/(prefix+'.out')).read_text()
    for folder,archive,metadata,manifest,count in [
        ('delivery','RF_stream_delivery.tar.gz','delivery_record.json','delivery_manifest.json',214),
        ('plot_delivery','plot_delivery.tar.gz','plots_delivery_record.json','plot_delivery_manifest.json',8)]:
        r=load(ROOT/'evidence'/metadata);file=ROOT/archive
        assert file.stat().st_size==r['archive_bytes'] and sha(file)==r['archive_sha256']
        rows=load(ROOT/folder/manifest)['files'];assert len(rows)==count and r['files']==count+1
        for row in rows:assert (ROOT/folder/row['file']).stat().st_size==row['bytes'] and sha(ROOT/folder/row['file'])==row['sha256']
    assert sha(ROOT/'protocol/stream_v1.json')==s['protocol_sha256']=='7c0aa230cae61d5ee169a9782ebc467ce1c45a2de962c752cef787312acbe4af'
    for name,digest in p['input_sha256'].items():assert sha(ROOT/'input'/name)==sha(ROOT/'delivery/input'/name)==digest
    for name in ['run_experiments.py','stream_linker.py','identity_worker.py']:assert sha(ROOT/'tools'/name)==sha(ROOT/'delivery/tools'/name)
    assert sha(ROOT/'input/association.py')==sha(PROJECT/'rf_queue_20261026/tools/association.py')==p['association_component_sha256']
    assert sha(ROOT/'tools/identity_worker.py')==sha(PROJECT/'confirmed12_capture_identity_20261029/tools/identity_worker.py')==p['worker_sha256']
    assert s['event_ledgers']==v['event_ledgers']==p['expected_event_ledgers']==144 and len(s['cases'])==v['cases_checked']==12
    assert s['true_query_forward_calls']==v['real_model_query_results']==515
    assert v['causal_RF_contexts']==120 and v['read_window_incidence_entries']==16898
    assert v['image_dotproducts_verified']==15450 and v['identity_scores_verified']==3090
    assert v['maximum_query_feature_difference_from_prior_actual_source_run']==0 and v['maximum_independent_score_error']<1e-12
    assert [c['real_query_forward_calls'] for c in s['cases']]==[60,35,35,35,60,60,60,35,60,55,20,0]
    one=next(c for c in s['cases'] if c['case_id']=='S01_single')
    assert one['RF_status_counts']=={'RF_UNIQUE_CANDIDATE':5,'RF_SHARED_WINDOW':7}
    for ID in ['S02_duplicates','S03_delay_inside']:
        c=next(c for c in s['cases'] if c['case_id']==ID)
        assert c['terminal_status_counts']==one['terminal_status_counts'] and c['RF_status_counts']==one['RF_status_counts']
    late=next(c for c in v['case_checks'] if c['case_id']=='S04_late');assert late['unique_late_read_ids']==12 and late['late_observation_links']==13
    wrong=next(c for c in v['case_checks'] if c['case_id']=='S07_wrong_single')
    assert len(wrong['mock_RF_ownership_audit'])==5 and all(r['mock_owner_matches_event'] is False for r in wrong['mock_RF_ownership_audit'])
    assert s['cases'][-2]['terminal_status_counts']=={'VISUAL_ALL_CONDITIONS_REJECTED':4,'UNRESOLVED_QUEUE_CAPACITY':8}
    assert s['cases'][-1]['terminal_status_counts']=={'UNRESOLVED_EXPIRED_WAITING':4,'UNRESOLVED_QUEUE_CAPACITY':8}
    assert all(c['worker_results_after_source_replay_end']==0 for c in s['cases'][:10])
    for c in s['cases']:
        rows=load(ROOT/'delivery/results/cases'/c['case_id']/'events.json')
        assert len(rows)==12 and all(r['verified_identity'] is False and r['source_cow_identity_reference'] is None and r['RF_input_is_synthetic'] is True for r in rows)
    test=(ROOT/'evidence/stream_tests.txt').read_text();assert 'Ran 14 tests' in test and test.rstrip().endswith('OK')
    assert len(visual['figures'])==2 and visual['panels_viewed']==3
    for row in visual['figures']:assert row['actual_visual_review']=='PASS' and sha(Path(row['path']))==row['sha256']
    assert len(plots['files'])==4 and plots['counted_interval_rows']==12 and plots['focus_incident_passages']==2
    for row in plots['files']:
        path=Path(row['path']);assert sha(path)==row['sha256']
        if path.suffix=='.png':
            with Image.open(path) as im:im.load();assert list(im.size)==row['dimensions']
        else:assert ET.parse(path).getroot().tag.endswith('svg')
    prior=PROJECT/'confirmed12_capture_identity_20261029'
    retained={
        'confirmed12_capture_identity_20261029/results/final_review_v3.json':p['source_capture_final_review_sha256'],
        'confirmed12_capture_identity_20261029/protocol/chain_v1.json':p['source_capture_protocol_sha256'],
        'confirmed12_capture_identity_20261029/delivery/results/replay/events.json':p['source_first_query_reference_sha256'],
        'human_count_confirmation_20261028/results/frozen_development_candidate.json':p['source_frozen_count_candidate_sha256'],
        'human_count_confirmation_20261028/evidence/user_confirmation.json':'fe8a895cd6ac71815ff8e2f6ad8d932a6453c41971b6b7a18ea9c2f743dd0f9f',
        'firststage_iou_regression_20261029/results/final_review.json':sha(PROJECT/'firststage_iou_regression_20261029/results/final_review.json')}
    for relative,digest in retained.items():assert sha(PROJECT/relative)==digest
    assert load(prior/'protocol/chain_v1.json')['identity']==p['source_identity']
    for c in load(ROOT/'input/runtime_captures.json'):assert sha(Path(c['local_snapshot_path']))==c['snapshot_sha256']
    accepted=load(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json')
    assert accepted['human_total']==accepted['predicted_down']==12 and accepted['absolute_total_error']==0
    assert load(PROJECT/'firststage_iou_regression_20261029/results/final_review.json')['candidate_global_replacement_adopted'] is False
    docs=[ROOT/'计划与验收.md',ROOT/'12事件流式读码与真实查询异常验证.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text and '\r\r' not in text
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            target=unquote(match[1] or match[2])
            if re.match(r'^[A-Za-z]:[/\\]',target):assert Path(target).exists(),target;links.append(target)
    evidence=['protocol/stream_v1.json','protocol/plots_v1.json','results/independent_verification.json','results/plot_verification.json',
              'evidence/visual_review.json','evidence/stream_tests.txt','evidence/delivery_record.json','evidence/plots_delivery_record.json',
              'evidence/status_02.txt','evidence/plots_status_01.txt']
    result={'status':'CAUSAL_RF_STREAM_144_LEDGERS_515_REAL_QUERIES_AND_PRESSURE_CONTROLS_REVIEWED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'jobs_completed':['130362','130363'],'job_exit_codes':['0:0','0:0'],
        'reused_source_events':12,'functional_cases':10,'real_pressure_controls':2,'event_ledgers':144,
        'actual_query_configuration_forwards':515,'actual_completed_query_jobs':103,'causal_RF_contexts':120,
        'independent_read_window_relations':16898,'independent_image_dotproducts':15450,'independent_identity_scores':3090,
        'single_code_RF_candidates_and_shared':[5,7],'duplicate_and_inside_delay_decisions_equal_single_case':True,
        'late_unique_reads':12,'late_event_links':13,'deliberate_wrong_single_mock_RF_candidates':5,
        'burst_actual_query_jobs_capacity_rejects':[4,8],'expired_waiting_capacity_rejects':[4,8],'expired_task_query_forwards':0,
        'source_features_equal_prior_real_query_run':True,'unit_checks':14,'scientific_plot_files':4,
        'plots_actually_viewed':2,'visual_panels':3,'local_links_checked':len(links),'data_archive_members':215,'plot_archive_members':9,
        'current_confirmed12_count_version_and_photos_preserved':True,'identity_models_gallery_and_thresholds_unchanged':True,
        'actual_RF_hardware_connected':False,'source_cow_identity_accuracy':None,'new_detector_forwards':0,'new_training_updates':0,
        'FPGA_execution_verified':False,'whole_goal_complete':False,
        'evidence_hashes':{r:sha(ROOT/r) for r in evidence},'retained_artifact_hashes':retained,
        'documents':[{'path':str(path.resolve()),'sha256':sha(path)} for path in docs],'plot_files':plots['files']}
    path=ROOT/'results/final_review.json';assert not path.exists();path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','retained_artifact_hashes','documents','plot_files']}))
if __name__=='__main__':main()
