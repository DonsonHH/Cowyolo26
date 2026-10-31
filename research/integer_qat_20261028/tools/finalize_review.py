from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
target = ROOT / 'results/final_review.json'
assert not target.exists()
synthesis = ROOT.parent / 'research_synthesis_20261027/results/review_after_six_epoch_integer_QAT_v2.json'
combined = json.loads(synthesis.read_text(encoding='utf-8'))
assert len(combined['documents']) == 24
for row in combined['documents']: assert sha(Path(row['path'])) == row['sha256']
actual = combined['actual_six_epoch_paired_integer_QAT_inspected']
assert actual['formal_QAT_updates'] == actual['paired_float_updates'] == 360
assert actual['files_verified'] == 145 and actual['same_reused_validation_queries_calibrate_and_score'] is True
paths = ['六轮配对QAT与身份验证结果.md', 'Review与当前状态.md', 'protocol/paired_integer_qat_v1.json',
         'results/local_verification.json', 'results/validation12_conditions.csv', 'results/delivery_status_01.txt',
         'delivery/results/study/summary.json', 'delivery/results/independent_verification.json',
         'delivery/results/study/all_models_thresholds_frozen.json', 'tools/train.py', 'tools/independent_verify.py']
status = (ROOT / 'results/delivery_status_01.txt').read_text(encoding='utf-8')
for job in ['129998', '129999', '130000']:
    assert any(line.startswith(job + '|') and '|COMPLETED|0:0|' in line for line in status.splitlines())
result = {'status': 'SIX_EPOCH_PAIRED_QAT_EXPERIMENT_DELIVERY_AND_FULL_REVIEW_COMPLETE',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'goal_turn_classification': 'progress',
          'phase_experiment_delivery_and_manual_review_complete': True, 'actual_results': actual,
          'synthesis_review_sha256': sha(synthesis),
          'evidence_files': [{'path': path, 'sha256': sha(ROOT / path)} for path in paths],
          'whole_goal_completion_audit': [
              {'requirement': 'Publicdata training and applying to userselected video range', 'status': 'development_runs_complete',
               'evidence': 'Frozen Cows/OpenCows checkpoints, native8912..10873 previews and paired rotation'},
              {'requirement': 'Detection/tracking diagnosis and justified training choice', 'status': 'multiple_actual_controls_complete',
               'evidence': 'Reference interventions, composition and orientation controls; finalfieldchoice awaitsindependenttruth'},
              {'requirement': 'Trainable quantization and actual paired training', 'status': 'current_development_study_complete',
               'evidence': 'Three seed initial/postupdate gates, QAT360 andfloat360,12validatedconditions'},
              {'requirement': 'Independent real bidirectional event accuracy', 'status': 'incomplete',
               'needed': 'Independent reviewerJSON and fresh real bidirectional sessions'},
              {'requirement': 'Reliable identity/RF recovery and independent risks', 'status': 'partial',
               'needed': 'Sourceidentity/RFmapping, independent evaluation and measured chosenrisk/costtradeoff'},
              {'requirement': 'Real-time detector and background identity jointly onPYNQ-Z2', 'status': 'unverified',
               'needed': 'User SSH/image/toolversions, finalfixedpointmapping and measured jointboard execution'},
              {'requirement': 'Publication-ready principal contribution', 'status': 'not_yet_proven',
               'needed': 'Mechanismcomparison, independentdata and actualjointboard cost/results'}],
          'final_identity_model_adopted': False, 'source_count_accuracy_verified': False,
          'FPGA_execution_verified': False, 'whole_goal_complete': False}
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': result['status'], 'documents': 24, 'links': combined['local_links_checked'],
                  'formal_QAT_updates': 360, 'paired_float_updates': 360, 'whole_goal_complete': False}))
