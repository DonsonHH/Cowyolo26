from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import ast,hashlib,json,re
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    p=load(ROOT/'protocol/lost_v1.json');check=load(ROOT/'results/local_verification.json');summary=load(ROOT/'delivery/results/summary.json')
    assert check['protocol_sha256']==summary['protocol_sha256']==sha(ROOT/'protocol/lost_v1.json')
    assert check['candidate_module_sha256']==summary['candidate_module_sha256']==p['candidate_module_sha256']==sha(ROOT/'tools/lost_tracker.py')
    assert check['summary_sha256']==sha(ROOT/'delivery/results/summary.json')
    assert check['files']==77 and check['counter_paths']==12 and check['baseline_full_regressions']==3 and check['trace_updates']==13050
    assert check['cost_entries']==3411 and check['nonempty_decisions']==2416 and check['maximum_cost_difference']<1e-6
    assert check['all_lost_recoveries']==259 and check['lost_recoveries_in_scope']==33
    assert check['current_scope_actual_low_detection_in_ROI']==check['current_scope_recovery_ID_actually_output_in_ROI']==4
    assert check['maximum_recovery_gap_frames']==155 and check['single_eligibility_expression_AST_change']
    assert all(r['times_and_directions_exact'] and not r['full_event_records_exact'] for r in check['comparisons'])
    for variant in ['active_only_iou','allow_lost_iou']:
        assert [r['predicted_down'] for r in summary['conditions'] if r['variant']==variant]==[12,11,11]
    for w in p['weights']:
        assert sha(PROJECT/f'cows2021_adaptation_20261027/delivery/results/training/seed{w["seed"]}/weights/last.pt')==w['sha256']
    red=load(ROOT/'delivery/results/baseline_red_tests.json');green=load(ROOT/'delivery/results/candidate_green_tests.json')
    assert red['gate_passed'] and red['tests']==12 and red['failures']==2 and red['skipped']==1
    assert green['tests']==12 and green['gate_passed'] and green['failures']==green['errors']==green['skipped']==0
    unique=set()
    for name,n in [('delivery',77),('media_delivery',28)]:
        rows=load(ROOT/name/'delivery_manifest.json');assert len(rows)==n
        for r in rows:
            f=ROOT/name/r['path'];assert f.stat().st_size==r['bytes'] and sha(f)==r['sha256'];unique.add(r['path'])
    assert len(unique)==105
    cases=load(ROOT/'results/ROI_recovery_case_states.json');assert cases['candidate_component_replays_exact']==3 and cases['update_traces_replayed']==6525 and len(cases['cases'])==4
    wanted=next(c for c in cases['cases'] if c['seed']==28 and c['target_ID']==105)
    assert not wanted['target_events']
    states={r['source_frame']:r for r in wanted['local_counter_states']}
    assert states[9365]['target_axis']>.6 and states[9365]['state']['streak']==1 and states[9370]['target_axis'] is None and states[9370]['state']['streak']==0
    figures=load(ROOT/'results/case_figure_record.json');assert figures['visual_QA']=='PASS' and len(figures['source_images'])==12
    for r in figures['source_images']+figures['figures']:
        f=ROOT/'case_figures'/r['file'];assert sha(f)==r['sha256']
        with Image.open(f) as im:im.load();assert im.size==((2560,1440) if r in figures['source_images'] else (1920,1552))
    catalog=load(ROOT/'results/frozen_prediction_catalog_v4.json');intake=load(ROOT/'results/catalog_intake_verification.json')
    assert len(catalog['conditions'])==intake['conditions']==29 and len(catalog['paired_comparisons'])==9
    assert catalog['conditions'][:26]==load(catalog['previous_catalog_path'])['conditions']
    assert intake['catalog_sha256']==sha(ROOT/'results/frozen_prediction_catalog_v4.json') and intake['indexed_prediction_events']==207
    assert intake['software_fixture_direction_rows']==58 and intake['software_fixture_refused_as_real_reference'] and intake['known_QA_intake_blocked']
    media=load(ROOT/'results/media_verification.json');browser=load(ROOT/'results/browser_verification.json')
    assert media['browser_verified'] and media['browser_tests']==len(browser['tests'])==12 and all(t['pass'] for t in browser['tests'])
    assert media['browser_evidence_sha256']==sha(ROOT/'results/browser_verification.json') and media['browser_screenshot_sha256']==sha(ROOT/'results/browser_source9365.png')
    assert len(media['media'])==6 and all(r['strict_full_decode']=='PASS' and r['frames']==1962 and r['fps']==25 and r['duration_s']==78.48 for r in media['media'])
    for r in media['media']+media['reused_baselines']:assert sha(PROJECT/'phase3_diagnosis_20261026/inputs'/r['file'])==r['sha256']
    page=PROJECT/'phase3_diagnosis_20261026/annotation_workbench/lost_recovery_preview.html'
    assert media['page_sha256']==sha(page)==sha(ROOT/'templates/preview.html') and media['data_sha256']==sha(page.with_name('lost_recovery_preview_data.json'))
    snaps=list((ROOT/'media_delivery/results').glob('allow_lost_iou_seed*/f*.jpg'));assert len(snaps)==18
    for f in snaps:
        with Image.open(f) as im:im.load();assert im.size==(1280,720)
    for f in [ROOT/'previews/source9365_paired_all_seeds.jpg',ROOT/'results/browser_source9365.png']:
        with Image.open(f) as im:im.load()
    status=(ROOT/'results/final_status.txt').read_text(encoding='utf-8')
    for job in [130288,130291,130292]:
        line=next(s for s in status.splitlines() if s.startswith(str(job)+'|'));assert '|COMPLETED|0:0|' in line and '|4gpu|2|4G|' in line and 'gres/gpu' not in line
    docs=[ROOT/'计划与验收.md',ROOT/'Lost低分恢复与完整事件结果.md',ROOT/'Review与当前状态.md',PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',PROJECT/'evaluation_intake_20261028/README.md']
    links=[]
    for doc in docs:
        text=doc.read_text(encoding='utf-8');assert '\ufffd' not in text
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            link=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',link):
                line=re.match(r'^(.*):(\d+)$',link);f=Path(line[1] if line else link);assert f.exists(),f
                if line:assert 1<=int(line[2])<=len(f.read_text(encoding='utf-8').splitlines())
                links.append(link)
    out={'status':'LOST_ELIGIBILITY_SINGLE_FACTOR_NEGATIVE_RESULT_AND_DELIVERY_REVIEWED',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/lost_v1.json'),
      'candidate_module_sha256':p['candidate_module_sha256'],'single_factor_scope_verified':True,
      'real_tracker_tests':12,'original_expected_failures':2,'candidate_passes':12,
      'paired_conditions':6,'counter_paths':12,'baseline_full_regressions':3,'trace_updates':13050,
      'cost_entries':3411,'nonempty_decisions':2416,'lost_recoveries_all_history':259,
      'lost_recoveries_in_scope_whole_frame':33,'lost_recoveries_in_scope_ROI':4,'all_ROI_recovery_cases_inspected':True,
      'main_predictions_before':[12,11,11],'main_predictions_after':[12,11,11],
      'event_times_directions_equal_allseeds':True,'track_ID_records_equal':False,'maximum_lost_recovery_gap_s':6.2,
      'delivery_files_verified':105,'native_case_frames':12,'case_contact_sheets':1,'rendered_snapshots_decoded':18,
      'new_media':6,'browser_tests':12,'catalog_conditions':29,'catalog_pairs':9,'software_direction_rows':58,
      'local_links_checked':len(links),'documents':[{'path':str(d),'sha256':sha(d)} for d in docs],
      'independent_source_accuracy_verified':False,'adopted_as_demonstrated_counting_improvement':False,
      'new_reference_received':False,'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,
      'previous_goal_turn_classification':'progress: secondstage cost control completed and independently verified',
      'this_goal_turn_classification':'progress: Lost eligibility control implemented, all ROI recoveries inspected, unchanged events verified',
      'next_priority':'Receive independent human event JSON and verify source events before more scene-specific optimization',
      'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='documents'}))
if __name__=='__main__':main()
