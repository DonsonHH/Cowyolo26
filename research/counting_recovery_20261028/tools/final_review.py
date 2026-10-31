"""Requirement-bound delivery review; preserves earlier verification snapshots."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    p=load(ROOT/'protocol/recovery_v2.json');local=load(ROOT/'results/local_verification.json')
    check=load(ROOT/'delivery/results/independent_verification.json')
    a=load(ROOT/'delivery/results/replay_v2/summary.json');b=load(ROOT/'delivery/results/full640_confirmation/summary.json')
    rows=a['conditions']+b['conditions'];assert len(rows)==10
    source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4'
    assert sha(source)==p['source_sha256'] and p['source_scope_inclusive']==[8912,10873]
    weights=[]
    for w in p['weights']:
        path=PROJECT/f'cows2021_adaptation_20261027/delivery/results/training/seed{w["seed"]}/weights/last.pt'
        assert sha(path)==w['sha256'];weights.append({'seed':w['seed'],'sha256':sha(path)})
    manifest=load(ROOT/'delivery/delivery_manifest.json')
    for item in manifest:
        path=ROOT/'delivery'/item['path'];assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256']
    assert len(manifest)==local['files']==191
    assert check['coordinate_rows']==36669 and check['baseline_exact_regressions']==1 and check['snapshot_full_decodes']==60
    assert check['protocol_sha256']==a['protocol_sha256']==b['protocol_sha256']==sha(ROOT/'protocol/recovery_v2.json')
    full=sorted((r for r in rows if r['arm']['name']=='full640_5hz'),key=lambda r:r['seed'])
    old=[len(load(PROJECT/f'orientation_video_20261027/delivery/results/inference/clockwise90_seed{s}/source_events.json')) for s in [26,27,28]]
    assert old==[8,6,8] and [r['predicted_down'] for r in full]==[11,10,11]
    assert all(r['predicted_up']==0 for r in rows)
    media=load(ROOT/'results/media_verification.json');browser=load(ROOT/'results/browser_verification.json')
    assert len(media['media'])==8 and media['browser_verified'] and len(browser['tests'])==14
    assert all(r['pass'] is True for r in browser['tests'])
    assert media['browser_evidence_sha256']==sha(ROOT/'results/browser_verification.json')
    assert media['browser_screenshot_sha256']==sha(ROOT/'results/browser_preview.png')
    page=PROJECT/'phase3_diagnosis_20261026/annotation_workbench/counting_recovery_preview.html'
    assert media['page_sha256']==sha(page)==sha(ROOT/'templates/preview.html')
    assert media['data_sha256']==sha(page.with_name('counting_recovery_preview_data.json'))
    for item in media['media']+media['reused_baselines']:
        path=PROJECT/'phase3_diagnosis_20261026/inputs'/item['file'];assert sha(path)==item['sha256']
    # Installed source was captured after inference; do not claim a pre-run source-code freeze.
    byte=(ROOT/'evidence/installed_byte_tracker.py').read_text(encoding='utf-8')
    yaml=(ROOT/'evidence/installed_bytetrack.yaml').read_text(encoding='utf-8')
    assert 'self.max_frames_lost = args.track_buffer' in byte and 'self.frame_id += 1' in byte
    assert 'self.frame_id - track.end_frame > self.max_frames_lost' in byte and 'track_buffer: 30' in yaml
    docs=[ROOT/'源片漏计优化与下一步.md',ROOT/'Review与当前状态.md',PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for doc in docs:
        content=doc.read_text(encoding='utf-8');assert '\ufffd' not in content and '待原始结果核对' not in content
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',content):
            link=unquote(match[1] or match[2])
            if re.match(r'^[A-Za-z]:[/\\]',link):
                line=re.match(r'^(.*):(\d+)$',link);path=Path(line[1] if line else link);assert path.exists(),path
                if line:assert 1<=int(line[2])<=len(path.read_text(encoding='utf-8').splitlines())
                links.append(link)
    partial=ROOT/'results/delivery.tar.gz';original=load(ROOT/'results/delivery_record.json')
    assert partial.stat().st_size<original['bytes']
    partial_record={'local_file':str(partial),'bytes':partial.stat().st_size,'sha256':sha(partial),
                    'complete':False,'unpacked_or_used_for_analysis':False,'full_remote_bytes':original['bytes'],
                    'complete_compact_archive_used_instead':True}
    evidence={'captured_after_inference':True,'pre_run_installed_source_hash_freeze_claimed':False,
              'files':[{'path':str(path),'sha256':sha(path)} for path in sorted((ROOT/'evidence').iterdir()) if path.is_file()],
              'track_buffer_update_calls':30,'nominal_5Hz_budget_s':6.,'nominal_25Hz_budget_s':1.2,
              'count_stability_duration_equal_but_tracker_wallclock_not_equal':True,
              'pure_sampling_rate_causal_claim_allowed':False}
    result={'status':'SOURCE_UNDERCOUNT_DEVELOPMENT_DELIVERY_AND_SCIENTIFIC_SCOPE_REVIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(source),'weights':weights,
            'requirements':{'user_scope_only_exported':True,'all10_conditions_and_failures_retained':True,
              'preplanned_selection_and_postpilot_confirmation_separate':True,'baseline_exact_regression':True,
              'coordinate_and_independent_counter_checks':True,'eight_media_full_decode':True,
              'four_conditions_browser_checked':True,'manual_claim_review':True},
            'full320_predictions':old,'full640_predictions':[r['predicted_down'] for r in full],
            'all10_predicted_down':[r['predicted_down'] for r in rows],'local_files_verified':191,
            'coordinate_rows':36669,'browser_tests':14,'current_documents':[{'path':str(doc),'sha256':sha(doc)} for doc in docs],
            'local_links_checked':len(links),'tracker_clock_limit':evidence,'interrupted_original_transfer':partial_record,
            'new_training_updates':0,'user_rough_total_treated_as_truth':False,
            'independent_source_accuracy_verified':False,'FPGA_execution_verified':False,
            'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','full640_predictions','local_files_verified','coordinate_rows','browser_tests','local_links_checked','whole_goal_complete']}))
if __name__=='__main__':main()
