from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    catalog=load(ROOT/'results/frozen_prediction_catalog_v2.json');checked=load(ROOT/'results/catalog_verification.json')
    prior=Path(catalog['previous_catalog_path']);assert sha(prior)==catalog['previous_catalog_sha256']
    assert catalog['conditions'][:17]==load(prior)['conditions'] and len(catalog['conditions'])==23 and len(catalog['paired_comparisons'])==3
    assert checked['catalog_sha256']==sha(ROOT/'results/frozen_prediction_catalog_v2.json') and checked['indexed_prediction_events']==139
    assert checked['distinct_bound_artifact_files']==35
    for row in catalog['conditions']:
        for field in ['events','summary','protocol']:assert sha(row[field+'_path'])==row[field+'_sha256']
    source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4';assert sha(source)==catalog['source_sha256']
    p=load(ROOT/'protocol/evaluation_v1.json');assert p['catalog_sha256']==sha(ROOT/'results/frozen_prediction_catalog_v2.json')
    for item in p['source_files'].values():assert sha(item['path'])==item['sha256']
    tests=load(ROOT/'results/all_test_results_delivery_final.json');assert sum(t['tests'] for t in tests['suites'])==28
    assert all(t['exit_code']==0 for t in tests['suites'])
    for t in tests['suites']:
        text=Path(t['log']).read_text(encoding='utf-8');assert f'Ran {t["tests"]} tests' in text and '\nOK' in text
    result=load(ROOT/'results/pipeline_test_results_delivery_final.json');assert result['status']=='PASS' and result['tests']==22
    cli=load(ROOT/'results/cli_verification.json');assert cli['checks']==3 and cli['stage_exit_code']==2 and not cli['score_output_created']
    assert cli['input_preserved'] and cli['original_matching_and_validation_sources_unchanged']
    template=load(ROOT/'acceptance_TEMPLATE.json')
    assert template['packet_sha256'] is None and all(template[k] is False for k in ['human_provenance_review_complete','native_source_review_complete','ambiguities_resolved','reviewer_independence_checked'])
    blocked=load(ROOT/'results/known_QA_cli_final/packet.json');assert not blocked['metrics_computed'] and blocked['status']=='DRAFT_INTAKE_BLOCKED'
    assert blocked['evaluation_protocol_sha256']==sha(ROOT/'protocol/evaluation_v1.json')
    dep=load(ROOT/'results/metric_dependency_record.json');assert not dep['global_or_bundled_environment_modified']
    assert sha(ROOT/'wheels'/dep['wheel'])==dep['wheel_sha256'] and dep['version']=='1.16.1'
    sys.path.insert(0,str(ROOT/'deps'));import scipy,numpy
    assert scipy.__version__=='1.16.1' and numpy.__version__=='2.3.5'
    probe=load(ROOT/'results/exit_probe_local_verification.json');assert probe['files']==9 and probe['trace_frames']==11
    assert probe['real_cost_entries_verified']==50 and probe['maximum_cost_or_IoU_difference']<1e-6
    assert probe['synthetic_cost_pairs']==25 and probe['source_full_original_replay_exact'] and probe['original_seed28_predictions']==11
    for item in load(ROOT/'exit_probe_delivery/delivery_manifest.json'):
        f=ROOT/'exit_probe_delivery'/item['path'];assert f.stat().st_size==item['bytes'] and sha(f)==item['sha256']
    exitp=load(ROOT/'protocol/exit_probe_v1.json');assert probe['protocol_sha256']==sha(ROOT/'protocol/exit_probe_v1.json')
    assert sha(ROOT/'evidence/installed_matching.py')==exitp['matching_source_sha256']
    assert 'np.arange(len(bboxes))' in (ROOT/'evidence/installed_stracks.py').read_text(encoding='utf-8')
    grid=load(ROOT/'exit_probe_delivery/results/exit_probe/low_score_cost_grid.json')
    assert grid['matches']==[] and min(min(row) for row in grid['installed_fused_costs'])>.75 and grid['secondstage_threshold']==.5
    t={r['source_frame']:r for r in probe['trace_summary']}
    assert t[9360]['target_state_after']==2 and t[9365]['target_second_eligible'] is False and t[9370]['target_second_eligible'] is False
    assert t[9375]['target_y']>.6 and t[9380]['best_first_cost']>.8 and not any(r['outside_ROI_only'] for r in t.values())
    figures=load(ROOT/'results/exit_case_figure_record.json');assert figures['visual_QA']=='PASS'
    assert len(figures['source_files'])==6 and len(figures['figures'])==2
    for row in figures['source_files']+figures['figures']:
        f=ROOT/'figures'/row['path'];assert sha(f)==row['sha256']
        with Image.open(f) as image:image.load();assert image.size==((2560,1440) if row in figures['source_files'] else (1920,788))
    status=(ROOT/'results/final_status.txt').read_text(encoding='utf-8');line=next(x for x in status.splitlines() if x.startswith('130276|'))
    assert '|COMPLETED|0:0|' in line and '|4gpu|2|4G|' in line and 'gres/gpu' not in line
    docs=[ROOT/'评价入口与下一步.md',ROOT/'B区中断与关联门槛.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',PROJECT/'evaluation_intake_20261028/README.md']
    links=[]
    for doc in docs:
        content=doc.read_text(encoding='utf-8');assert '\ufffd' not in content
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',content):
            link=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',link):
                match=re.match(r'^(.*):(\d+)$',link);f=Path(match[1] if match else link);assert f.exists(),f
                if match:assert 1<=int(match[2])<=len(f.read_text(encoding='utf-8').splitlines())
                links.append(link)
    artifacts=[p for folder in ['tools','protocol','evidence'] for p in (ROOT/folder).glob('*') if p.is_file()]
    record={'status':'PAIRED_EVENT_INTAKE_ASSOCIATION_BOUNDARIES_AND_REPORT_CLAIMS_REVIEWED',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'catalog_sha256':sha(ROOT/'results/frozen_prediction_catalog_v2.json'),
      'evaluation_protocol_sha256':sha(ROOT/'protocol/evaluation_v1.json'),'exit_probe_protocol_sha256':sha(ROOT/'protocol/exit_probe_v1.json'),
      'source_sha256':sha(source),'catalog_conditions':23,'preserved_historical_conditions':17,'current_pairs':3,
      'indexed_prediction_events':139,'bound_source_artifacts':35,'logic_tests':28,'actual_CLI_checks':3,
      'scipy':scipy.__version__,'numpy':numpy.__version__,'global_environment_modified':False,
      'probe_job_id':130276,'probe_files_verified':9,'probe_frames':11,'real_cost_entries_verified':50,
      'synthetic_cost_pairs':25,'native_source_frames':6,'visual_contact_sheets':2,
      'secondstage_score_fused_cost_lower_bound_over_gate':True,'lost_eligibility_and_raw_detection_limits_separately_reported':True,
      'first_verifier_subset_index_assumption_corrected_without_changing_probe':True,
      'same_job_partition_change_completed_without_GPU_allocation':True,
      'local_links_checked':len(links),'documents':[{'path':str(d),'sha256':sha(d)} for d in docs],
      'local_code_protocol_evidence':[{'path':str(p),'sha256':sha(p)} for p in artifacts],
      'association_cost_change_implemented':False,'current_source_predictions':[12,11,11],
      'new_independent_reference_received':False,'real_source_count_accuracy_calculated':False,
      'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,
      'previous_goal_turn_classification':'progress: causal confirmation handoff implemented and verified',
      'this_goal_turn_classification':'progress: current candidates integrated and B-region boundary evidence produced',
      'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['documents','local_code_protocol_evidence']}))
if __name__=='__main__':main()
