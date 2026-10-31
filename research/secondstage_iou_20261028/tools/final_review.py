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
    p=load(ROOT/'protocol/secondstage_v1.json');local=load(ROOT/'results/local_verification.json');summary=load(ROOT/'delivery/results/summary.json')
    assert local['protocol_sha256']==summary['protocol_sha256']==sha(ROOT/'protocol/secondstage_v1.json')
    assert local['summary_sha256']==sha(ROOT/'delivery/results/summary.json')
    assert local['candidate_module_sha256']==p['candidate_module_sha256']==sha(ROOT/'tools/secondstage_tracker.py')
    assert local['single_score_fusion_block_AST_change_verified'] and local['firststage_and_lost_eligibility_unchanged']
    assert local['event_paths']==12 and local['trace_updates']==13050 and local['full_baseline_regressions']==3
    assert local['secondstage_nonempty_decisions']==1190 and local['secondstage_cost_entries']==1490 and local['maximum_cost_or_IoU_difference']<1e-6
    assert local['applied_low_stage_matches_all_history']==786 and local['ROI_track_rows_with_history']==3415
    assert all(c['event_times_and_directions_exact_without_ID'] and not c['full_event_records_exact'] for c in local['comparisons'])
    assert [c['predicted_down'] for c in summary['conditions'] if c['variant']=='installed_baseline']==[12,11,11]
    assert [c['predicted_down'] for c in summary['conditions'] if c['variant']=='secondstage_iou']==[12,11,11]
    assert [c['applied_low_stage_matches_in_scope'] for c in summary['conditions'] if c['variant']=='secondstage_iou']==[72,11,30]
    red=load(ROOT/'delivery/results/baseline_red_tests.json');green=load(ROOT/'delivery/results/candidate_green_tests.json')
    assert red['tests']==green['tests']==9 and red['failures']==2 and red['expected_two_baseline_failures_observed']
    assert green['gate_passed'] and green['failures']==green['errors']==green['skipped']==0
    unique=set()
    for folder,expected in [('delivery',71),('media_delivery',25)]:
        rows=load(ROOT/folder/'delivery_manifest.json');assert len(rows)==expected
        for item in rows:
            f=ROOT/folder/item['path'];assert f.stat().st_size==item['bytes'] and sha(f)==item['sha256'];unique.add(item['path'])
    assert len(unique)==96
    for w in p['weights']:
        f=PROJECT/f'cows2021_adaptation_20261027/delivery/results/training/seed{w["seed"]}/weights/last.pt';assert sha(f)==w['sha256']
    catalog=load(ROOT/'results/frozen_prediction_catalog_v3.json');intake=load(ROOT/'results/catalog_intake_verification.json')
    assert len(catalog['conditions'])==intake['conditions']==26 and len(catalog['paired_comparisons'])==6
    old=load(catalog['previous_catalog_path']);assert catalog['conditions'][:23]==old['conditions']
    assert intake['catalog_sha256']==sha(ROOT/'results/frozen_prediction_catalog_v3.json') and intake['indexed_prediction_events']==173
    assert intake['software_fixture_direction_rows']==52 and intake['software_fixture_refused_as_real_reference']
    assert intake['known_QA_intake_blocked'] and not intake['source_accuracy_computed']
    media=load(ROOT/'results/media_verification.json');browser=load(ROOT/'results/browser_verification.json')
    assert media['browser_verified'] and media['browser_tests']==len(browser['tests'])==12 and all(t['pass'] for t in browser['tests'])
    assert media['browser_evidence_sha256']==sha(ROOT/'results/browser_verification.json')
    assert media['browser_screenshot_sha256']==sha(ROOT/'results/browser_source9365.png')
    assert len(media['media'])==6 and all(r['strict_full_decode']=='PASS' and r['frames']==1962 and r['fps']==25 and r['duration_s']==78.48 for r in media['media'])
    for r in media['media']+media['reused_baselines']:assert sha(PROJECT/'phase3_diagnosis_20261026/inputs'/r['file'])==r['sha256']
    page=PROJECT/'phase3_diagnosis_20261026/annotation_workbench/secondstage_iou_preview.html'
    assert media['page_sha256']==sha(page)==sha(ROOT/'templates/preview.html')
    assert media['data_sha256']==sha(page.with_name('secondstage_iou_preview_data.json'))
    jpgs=list((ROOT/'media_delivery/results').glob('secondstage_iou_seed*/f*.jpg'));assert len(jpgs)==15
    for f in jpgs:
        with Image.open(f) as im:im.load();assert im.size==(1280,720)
    for f in [ROOT/'previews/source9420_paired_all_seeds.jpg',ROOT/'results/browser_source9365.png']:
        with Image.open(f) as im:im.load()
    status=(ROOT/'results/final_status.txt').read_text(encoding='utf-8')
    for job in [130277,130278,130280]:
        line=next(s for s in status.splitlines() if s.startswith(str(job)+'|'));assert '|COMPLETED|0:0|' in line and '|4gpu|2|4G|' in line and 'gres/gpu' not in line
    docs=[ROOT/'计划与验收.md',ROOT/'第二阶段代价对照与结果.md',ROOT/'Review与当前状态.md',PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',PROJECT/'evaluation_intake_20261028/README.md']
    links=[]
    for doc in docs:
        text=doc.read_text(encoding='utf-8');assert '\ufffd' not in text
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            link=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',link):
                line=re.match(r'^(.*):(\d+)$',link);f=Path(line[1] if line else link);assert f.exists(),f
                if line:assert 1<=int(line[2])<=len(f.read_text(encoding='utf-8').splitlines())
                links.append(link)
    record={'status':'SECONDSTAGE_SINGLE_FACTOR_CONTROL_EVENT_NEGATIVE_RESULT_AND_DELIVERY_REVIEWED',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/secondstage_v1.json'),
      'candidate_module_sha256':p['candidate_module_sha256'],'single_factor_scope_verified':True,
      'real_tracker_behavior_tests':9,'expected_original_failures':2,'candidate_behavior_passes':9,
      'paired_conditions':6,'independent_event_paths':12,'trace_updates':13050,
      'secondstage_decisions':1190,'cost_entries':1490,'all_history_low_matches':786,'ROI_rows_added_by_seed':[10,4,3],
      'main_predictions_before':[12,11,11],'main_predictions_after':[12,11,11],
      'event_times_and_directions_equal_allseeds':True,'track_ID_records_equal_allseeds':False,
      'delivery_files_verified':96,'new_media':6,'snapshots_decoded':15,'browser_tests':12,
      'catalog_conditions':26,'catalog_pairs':6,'software_fixture_direction_rows':52,
      'local_links_checked':len(links),'documents':[{'path':str(d),'sha256':sha(d)} for d in docs],
      'current_source_accuracy_verified':False,'adopted_as_demonstrated_counting_improvement':False,
      'new_reference_received':False,'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,
      'previous_goal_turn_classification':'progress: current evaluation intake and B-region diagnostic completed',
      'this_goal_turn_classification':'progress: controlled implementation evaluated; negative event result and expanded intake verified',
      'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k!='documents'}))
if __name__=='__main__':main()
