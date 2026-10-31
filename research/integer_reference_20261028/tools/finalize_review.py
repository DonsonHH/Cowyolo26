from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = ROOT / 'results/final_review.json'
    assert not output.exists()
    combined_path = ROOT.parent / 'research_synthesis_20261027/results/review_after_integer_reference_v2.json'
    combined = json.loads(combined_path.read_text(encoding='utf-8'))
    assert len(combined['documents']) == 18 and combined['local_links_checked'] == 176
    for row in combined['documents']:
        assert sha(Path(row['path'])) == row['sha256']
    actual = combined['actual_integer_reference_records_inspected']
    assert actual['old_QDQ_passes'] == 7 and actual['old_failure_index'] == 3
    assert actual['new_candidate_disabled_passes'] == 8 and actual['new_candidate_default_passes'] == 6
    assert actual['all_seeds_gradients_or_FPGA_verified'] is False
    assert actual['candidate_is_changed_numerical_contract'] is True
    assert actual['new_training_updates'] == 0
    local_path = ROOT / 'results/local_delivery_verification.json'
    local = json.loads(local_path.read_text(encoding='utf-8'))
    assert local['manifest_files'] == 35 and local['local_metric_conditions'] == 16
    bound = [
        ROOT / '整数卷积参考与导出边界.md', ROOT / 'Review与当前状态.md',
        ROOT / 'protocol/integer_conv_v1.json', local_path,
        ROOT / 'delivery/results/reference/summary.json',
        ROOT / 'delivery/results/reference/original_failure_reproduction.json',
        ROOT / 'delivery/results/independent_verification.json',
        ROOT / 'results/eight_vector_numeric_comparison.csv',
        ROOT / 'results/status_04.txt', ROOT / 'results/environment_retry_submission.txt',
        ROOT / 'results/delivery_record.json',
        ROOT / 'tools/run_reference.py', ROOT / 'tools/integer_math.py',
        ROOT / 'tools/independent_verify.py', ROOT / 'tools/verify_local_delivery.py'
    ]
    result = {
        'status': 'INTEGER_REFERENCE_PHASE_NUMERICAL_DELIVERY_AND_FULL_MANUAL_REPORT_REVIEW_COMPLETE',
        'created_UTC': datetime.now(timezone.utc).isoformat(),
        'phase_experiment_and_delivery_complete': True,
        'full_manual_report_and_updated_master_scope_review_complete': True,
        'previous_goal_turn_classification': 'progress',
        'current_goal_turn_classification': 'progress',
        'actual_progress': actual,
        'synthesis_review': {'path': str(combined_path), 'sha256': sha(combined_path)},
        'evidence': [{'path': str(p), 'sha256': sha(p)} for p in bound],
        'remaining_original_scope': [
            {'requirement': 'Independent bidirectional count quality', 'status': 'incomplete',
             'needed': 'Independent reviewJSON and fresh real bidirectional events'},
            {'requirement': 'Trainable identity quantisation and calibrated eventidentity', 'status': 'partial',
             'needed': 'Allseed forward/STE/postupdate export gates, actual pairedtraining and independent identity/RF mapping'},
            {'requirement': 'Detection and background identity jointly onPYNQ-Z2', 'status': 'unverified',
             'needed': 'User-supplied SSH/image/toolversions, final arithmetic mapping and measured board execution'},
            {'requirement': 'Complete publication evidence', 'status': 'not_yet_proven',
             'needed': 'Independent evaluation, principalmechanism/ablations and actual jointboard results'}
        ],
        'new_numerical_contract_not_old_QDQ_repair': True,
        'formal_QAT_or_paired_float_training_updates': 0,
        'all_seeds_gradients_or_training_completed': False,
        'identity_accuracy_improved': None, 'FPGA_execution_verified': False,
        'whole_goal_complete': False
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'documents_checked': 18, 'local_links_checked': 176,
                      'evidence_files_bound': len(bound), 'formal_QAT_updates': 0,
                      'whole_goal_complete': False}))


if __name__ == '__main__':
    main()
