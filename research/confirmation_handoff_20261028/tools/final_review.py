from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    p=load(ROOT/'protocol/handoff_v1.json');local=load(ROOT/'results/local_verification.json')
    summary=load(ROOT/'delivery/results/replay_v2/summary.json');check=load(ROOT/'delivery/results/independent_verification.json')
    assert local['files']==64 and local['counter_paths']==9 and local['trace_frames']==6525
    assert check['source_summary_sha256']==sha(ROOT/'delivery/results/replay_v2/summary.json')
    assert p['handoff_module_sha256']==sha(ROOT/'tools/confirmation_counter.py')==sha(ROOT/'delivery/tools/confirmation_counter.py')==check['module_sha256']
    assert p['frozen_base_counter_sha256']==sha(ROOT/'input/zone_counter.py')==sha(ROOT/'delivery/input/zone_counter.py')
    assert [c['baseline_down'] for c in summary['conditions']]==[11,10,11] and [c['handoff_down'] for c in summary['conditions']]==[12,11,11]
    assert [len(c['added_events']) for c in summary['conditions']]==[1,1,0] and all(not c['removed_events'] for c in summary['conditions'])
    assert [(c['added_events'][0]['source_frame'],c['added_events'][0]['track_id']) for c in summary['conditions'][:2]]==[(9345,95),(9345,57)]
    assert check['accepted_history']==41 and check['tentative_observations']==127 and check['trace_frames']==6525
    for row in load(ROOT/'delivery/delivery_manifest.json'):
        f=ROOT/'delivery'/row['path'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
    server=(ROOT/'delivery/results/replay_v2/behavior_server_green.txt').read_text(encoding='utf-8')
    assert 'Ran 14 tests' in server and server.rstrip().endswith('OK')
    assert 'failures=2' in (ROOT/'results/behavior_baseline_red.txt').read_text(encoding='utf-8')
    causal=load(ROOT/'results/local_causal_replay.json');assert causal['trace_frames']==6525
    for c in causal['conditions'][:2]:
        s=next(s for s in c['selected_states'] if s['frame']==9315)
        assert s['handoff_state']['origin']=='A' and s['handoff_state']['streak']==3
        assert s['disabled_state']['origin'] is None and s['disabled_state']['streak']==2
    media=load(ROOT/'results/media_verification.json');browser=load(ROOT/'results/browser_verification.json')
    assert media['browser_verified'] and media['browser_tests']==len(browser['tests'])==13 and browser['all_tests_passed']
    assert media['browser_evidence_sha256']==sha(ROOT/'results/browser_verification.json')
    assert media['browser_screenshot_sha256']==sha(ROOT/'results/browser_source9345_viewport.png')
    for r in media['media']+media['reused_baselines']:
        assert sha(PROJECT/'phase3_diagnosis_20261026/inputs'/r['file'])==r['sha256']
    assert len(media['media'])==6 and all(r['strict_full_decode']=='PASS' and r['frames']==1962 and r['duration_s']==78.48 for r in media['media'])
    page=PROJECT/'phase3_diagnosis_20261026/annotation_workbench/confirmation_handoff_preview.html'
    assert media['page_sha256']==sha(page)==sha(ROOT/'templates/preview.html')
    assert media['data_sha256']==sha(page.with_name('confirmation_handoff_preview_data.json'))
    for f in [ROOT/'previews/source9345_paired_all_seeds.jpg',ROOT/'results/browser_source9345_viewport.png']:
        with Image.open(f) as image:image.load()
    status=(ROOT/'results/final_status.txt').read_text(encoding='utf-8')
    assert '130241|FAILED|1:0|' in status and all(f'{job}|COMPLETED|0:0|' in status for job in [130243,130244])
    docs=[ROOT/'计划与验收.md',ROOT/'入口观察交接与配对结果.md',ROOT/'Review与当前状态.md',PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for doc in docs:
        content=doc.read_text(encoding='utf-8');assert '\ufffd' not in content
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',content):
            value=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',value):
                line=re.match(r'^(.*):(\d+)$',value);path=Path(line[1] if line else value);assert path.exists(),path
                if line:assert 1<=int(line[2])<=len(path.read_text(encoding='utf-8').splitlines())
                links.append(value)
    r={'status':'CONFIRMATION_HANDOFF_IMPLEMENTATION_REPLAYS_MEDIA_AND_CLAIMS_REVIEWED',
       'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/handoff_v1.json'),
       'module_sha256':sha(ROOT/'tools/confirmation_counter.py'),'implementation_completed':True,
       'baseline_predictions':[11,10,11],'handoff_predictions':[12,11,11],'added_event_frames':[9345,9345],
       'behavior_tests':14,'original_tracker_regressions':3,'disabled_wrapper_regressions':3,
       'independent_event_paths':9,'update_traces':6525,'tentative_observations':127,'admitted_history':41,
       'delivery_files':64,'new_media':6,'browser_tests':13,'local_links_checked':len(links),
       'documents':[{'path':str(d),'sha256':sha(d)} for d in docs],
       'physical_duplicate_cow_events_independently_ruled_out':False,'independent_source_accuracy_verified':False,
       'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,
       'original_interface_failure_preserved':True,'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='documents'}))
if __name__=='__main__':main()
