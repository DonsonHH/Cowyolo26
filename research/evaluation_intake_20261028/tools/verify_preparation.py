from pathlib import Path
import hashlib, json, urllib.request
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
catalog = load(ROOT/'results/frozen_prediction_catalog.json')
assert len(catalog['conditions']) == 17
for row in catalog['conditions']:
    for key in ['summary', 'protocol', 'events']:
        assert sha(Path(row[key+'_path'])) == row[key+'_sha256']
    events = load(row['events_path'])
    assert sum(r['direction']=='A->B' for r in events) == row['predicted_A_to_B']
    assert sum(r['direction']=='B->A' for r in events) == row['predicted_B_to_A']
    assert all(8912 <= r['source_frame'] <= 10873 and r['time_s'] == r['source_frame']/25 for r in events)
assert len({(r['checkpoint_sha256'],r['orientation']) for r in catalog['conditions']}) == 17
qa = load(ROOT/'results/known_QA_intake_check.json')
assert 'KNOWN_QA_FIXTURE_NOT_HUMAN_REFERENCE' in qa['blocking_findings']
assert qa['independent_reference_certified'] is False
before = load(ROOT/'results/annotation_jump_before_fix.json')
assert before['typed_frame'] == 10873 and before['after_update']['jump'] != '10873'
assert before['after_update']['paused'] is False
retest = load(ROOT/'results/annotation_browser_retest.json')
assert len(retest['tests']) == 9
assert retest['QA_draft_before'] == retest['QA_draft_after']
assert retest['main_draft_opened_or_modified'] is False and retest['no_events_added_or_deleted'] is True
assert retest['final_view']['jump'] == '9420' and retest['final_view']['error'] is None
assert retest['final_view']['paused'] is True and retest['final_view']['qaNoticeHidden'] is False
page = PROJECT/'phase3_diagnosis_20261026/annotation_workbench/index.html'
fix = load(ROOT/'results/annotation_jump_fix.json')
assert sha(page) == fix['new_sha256'] and sha(ROOT/'results/annotation_index_before_fix.html') == fix['old_sha256']
with urllib.request.urlopen('http://127.0.0.1:8779/annotation_workbench/index.html?qa=1', timeout=15) as response:
    assert response.status == 200
    assert hashlib.sha256(response.read()).hexdigest() == sha(page)
with Image.open(ROOT/'results/annotation_jump_fixed.png') as image:
    image.load()
    assert image.width > 700 and image.height > 700
tests = load(ROOT/'results/intake_test_results_v2.json')
assert tests['status'] == 'PASS' and tests['tests_run'] == 16
fix.update(browser_retest='PASS', browser_evidence_sha256=sha(ROOT/'results/annotation_browser_retest.json'),
           browser_screenshot_sha256=sha(ROOT/'results/annotation_jump_fixed.png'))
(ROOT/'results/annotation_jump_fix.json').write_text(json.dumps(fix, indent=2), encoding='utf-8')
report = {'status': 'UI_FIX_17_PREDICTION_ARTIFACTS_AND_DRAFT_INTAKE_PREPARATION_VERIFIED',
          'catalog_conditions': 17, 'normalized_Cows_aliases': 3, 'browser_retest_cases': 9,
          'intake_tests': 16, 'main_draft_modified': False, 'new_reference_received': False,
          'independent_count_accuracy_verified': False, 'FPGA_execution_verified': False,
          'whole_goal_complete': False}
target = ROOT/'results/preparation_verification.json'
assert not target.exists()
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
