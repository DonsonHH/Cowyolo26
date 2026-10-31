"""Record the bounded phase review and retain unmet whole-project requirements."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def main():
    target = ROOT / 'results/final_review.json'
    assert not target.exists()
    combined_path = ROOT.parent / 'research_synthesis_20261027/results/review_after_video_rotation.json'
    combined = json.loads(combined_path.read_text(encoding='utf-8'))
    assert combined['whole_goal_complete'] is False
    assert len(combined['documents']) == 14 and combined['local_links_checked'] == 148
    for row in combined['documents']:
        assert sha(Path(row['path'])) == row['sha256']
    video = combined['actual_video_rotation_records_inspected']
    assert video['source_predictions_original'] == [0, 1, 0]
    assert video['source_predictions_clockwise90'] == [8, 6, 8]
    assert video['source_independent_accuracy_verified'] is False
    assert video['Z2_execution_verified'] is False
    independent = load('results/independent_verification.json')
    assert independent['delivery_files_verified'] == 177
    assert independent['all_original_event_and_track_regressions_passed'] == 6
    assert independent['pretracker_inverse_coordinate_rows_verified'] == 12542
    media = load('results/media_verification.json')
    assert media['browser_verified'] is True and media['source_accuracy_verified'] is False
    evidence = [
        'protocol/video_rotation_v1.json', 'input/checkpoint_freeze.json',
        'results/local_delivery_verification.json', 'results/independent_verification.json',
        'results/output_coverage.json', 'results/media_verification.json',
        'results/browser_verification.json', 'results/browser_source9420.png',
        'results/browser_before_jump_fix.json', 'results/browser_jump_race_fix.json',
        'results/status_08.txt', 'results/sample_contact_record.json',
        'delivery/results/nonempty_seam_smoke.json', 'delivery/results/inference/summary.json',
        '视频输入旋转配对与结论.md', 'Review与当前状态.md',
        'tools/rotation_seam.py', 'tools/replay.py', 'tools/verify_results.py',
        'tools/finalize_media_review.py', 'tools/finalize_report_review.py'
    ]
    result = {
        'status': 'VIDEO_ROTATION_PHASE_DELIVERABLES_AND_FULL_MANUAL_REPORT_REVIEW_COMPLETE',
        'created_UTC': datetime.now(timezone.utc).isoformat(),
        'phase_experiment_complete': True, 'phase_delivery_complete': True,
        'full_manual_report_and_current_master_claim_review_complete': True,
        'previous_goal_turn_classification': 'progress',
        'current_goal_turn_progress': [
            'Wrote full video rotation report and Review with failure limits',
            'Bound browser QA to final page and media hashes; preserved initial UI failure',
            'Restarted previously missing local server and verified served page/data hashes',
            'Updated research hub/master/plan and checked14documents148local links'
        ],
        'paired_results': video,
        'combined_review': {'path': str(combined_path), 'sha256': sha(combined_path)},
        'files': [{'path': p, 'bytes': (ROOT / p).stat().st_size,
                   'sha256': sha(ROOT / p)} for p in evidence],
        'whole_goal_requirement_audit': [
            {'requirement': 'Grounded research route, dataset/weight options and MD explanation with review',
             'status': 'produced_and_reviewed', 'evidence': '研究总览_从想法到论文.md and combined review'},
            {'requirement': 'Train from public manual labels, then apply to requested source range',
             'status': 'development_experiments_complete',
             'evidence': 'Cows2021 three10epoch checkpoints, native source8912..10873 videos'},
            {'requirement': 'Separate detection and tracking causes before choosing final training/model',
             'status': 'multiple_diagnostics_complete_final_choice_unproven',
             'evidence': 'Exact original regressions, pretracker traces, independent event replay and prior diagnostics'},
            {'requirement': 'Independent annotated bidirectional passage and event accuracy',
             'status': 'incomplete',
             'missing': 'Independent source review JSON and fresh real bidirectional sessions; usedToros is development'},
            {'requirement': 'Biometric identity recovery with reliable identity/RF association',
             'status': 'partial',
             'missing': 'Independently matched source identities, larger calibrated unknown/event evaluation and real synchronized RF'},
            {'requirement': 'Real-time detection and background identity jointly onPYNQ-Z2',
             'status': 'unverified',
             'missing': 'User-supplied SSH/image/tool versions, board execution and measured joint service/memory/energy'},
            {'requirement': 'Integer model numerical gate before formal QAT',
             'status': 'incomplete',
             'evidence': 'One of8original vectors still fails, formalQATupdates0 in combined review'},
            {'requirement': 'Evidence-supported primary scientific contribution and publishable complete paper',
             'status': 'not_yet_proven',
             'missing': 'Mechanism comparison, independent evaluation, joint board results and associated ablations'}
        ],
        'source_independent_accuracy_verified': False,
        'final_model_adopted': False, 'new_training_updates': 0,
        'Z2_joint_execution_verified': False, 'main_paper_contribution_verified': False,
        'whole_goal_complete': False
    }
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'files_bound': len(evidence),
                      'documents_checked': 14, 'local_links_checked': 148,
                      'phase_delivery_complete': True,
                      'source_independent_accuracy_verified': False,
                      'whole_goal_complete': False}))


if __name__ == '__main__':
    main()
