from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote
import hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
load = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
previous_path = ROOT / 'results/overview_review_20261031_v22_recovery.json'
previous = load(previous_path)
assert previous['complete_current_review_coverage']
snapshot = ROOT / 'snapshots/overview_v22_before_workload_failure/研究阶段总结_20261030.md'
assert sha(snapshot) == previous['document']['sha256']
entry_path = ROOT / 'results/entrypoint_update_20261031_v23_workload_v2.json'
entry = load(entry_path)
for row in entry['previous_files_and_snapshots']:
    assert sha(Path(row['snapshot'])) == row['sha256']
for row in entry['current_entrypoints'] + entry['new_documents'] + entry['new_review_sources']:
    assert sha(Path(row['path'])) == row['sha256']
assert sha(Path(entry['diff']['path'])) == entry['diff']['sha256']
stage_root = PROJECT / 'pynq_workload_ablation_20261031'
stage_path = stage_root / 'results/final_review_v1.json'
stage = load(stage_path)
expected = {'task_status': 'FAILED', 'planned_timed_cases': 8, 'completed_timed_cases': 5,
            'conditions': ['A', 'B', 'C', 'D', 'D'], 'actual_counts': [7, 8, 10, 10, 3],
            'processed_frames': [368, 368, 383, 343, 286], 'skipped_slots': [24, 24, 9, 49, 106],
            'deadline_misses': [16, 35, 86, 342, 286], 'all_actual_board_image_forwards': 1804,
            'actual_timed_O8_forwards': 1748, 'actual_identity_jobs': 30, 'full_association_ticks': 10663,
            'full_association_rows': 2338, 'counter_paths': 10, 'new_CPU_model_reference_forwards': 0,
            'CPU_replay_job_id': '130931', 'full5FPS_target_achieved': False,
            'power_or_memory_or_IPC_root_cause_proven': False, 'whole_goal_complete': False}
for key, value in expected.items():
    assert stage[key] == value, key
for name, digest in stage['evidence_hashes'].items():
    assert sha(stage_root / name) == digest
for row in stage['documents'] + stage['reviewed_tools']:
    assert sha(Path(row['path'])) == row['sha256']
verification = load(stage_root / 'results/independent_verification.json')
supplement = PROJECT / 'paper_readiness_20261030/论文补充_板上负载退化与启动失败_20261031.md'
main = PROJECT / '研究阶段总结_20261030.md'
text = main.read_text(encoding='utf-8')
paper_text = supplement.read_text(encoding='utf-8')
assert '### 3.15 ' in text and '八轮计划失败' in text
for case in verification['cases']:
    row = f"| {case['run']} | {int(case['input_producer'])}/{int(case['identity_workload'])} | {case['processed_frames']} | {case['skipped_slots']} | {case['deadline_misses']} | {case['processed_per_second_over_offered_duration']:.3f} | {case['P95_release_to_count_ms']:.2f} | {case['source_down_count']} |"
    assert row in text and row in paper_text
for phrase in ['FAILED', 'C11仍待验证', '1804', '10663', 'READY', '4794.70ms', '永久身份正确率']:
    assert phrase in paper_text, phrase
for row in load(PROJECT / 'paper_readiness_20261030/results/manuscript_review_v3.json')['documents']:
    assert sha(Path(row['file'])) == row['sha256']
links = []
for document in [main, supplement]:
    for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)', document.read_text(encoding='utf-8')):
        target = unquote((match[1] or match[2]).strip())
        if target.startswith(('http://', 'https://', '#')):
            continue
        path = Path(target)
        path = path if path.is_absolute() else document.parent / path
        assert path.exists(), target
        links.append(str(path.resolve()))
records = list(previous['current_numeric_record_files'])
for path in [stage_path, stage_root / 'results/independent_verification.json',
             stage_root / 'results/tracker_reference_verification.json', stage_root / 'results/shared_frame_timing.json']:
    records.append({'path': str(path), 'sha256': sha(path)})
for row in records:
    assert sha(Path(row['path'])) == row['sha256']
result = dict(previous)
result.update({'status': 'CURRENT_OVERVIEW_V23_FAILED8PLAN_FIVE_PERIODS_AND_ALL_AVAILABLE_REFERENCES_REVIEWED',
               'created_UTC': datetime.now(timezone.utc).isoformat(), 'document': {'path': str(main), 'sha256': sha(main)},
               'review_method': 'Retained V22 matches exact snapshot; all V23 changes, failed-plan report, figure and paper supplement read; numeric rows, full CPU associations and source hashes checked.',
               'previous_review_preserved': previous_path.name,
               'previous_complete_manual_read_provenance': previous_path.name,
               'previous_overview_snapshot': {'path': str(snapshot), 'sha256': sha(snapshot)},
               'entrypoint_update_evidence': {'path': str(entry_path), 'sha256': sha(entry_path)},
               'changed_text_evidence': entry['diff'], 'current_numeric_record_files': records,
               'local_overview_and_new_supplement_links_checked': len(links),
               'manual_review_topics': previous['manual_review_topics'] + [
                   'Eight-case ABCDDCBA protocol completed only ABCDD; case6 readiness failure preserved, final2 unstarted',
                   'Five processed counts368,368,383,343,286 and cattle counts7,8,10,10,3 retained without event-accuracy claim',
                   '1748 timed O8 plus8qualification12warm and30identity6warm equals1804 actual board image forwards',
                   'All available raw,1176 producer997 receipts30fixed jobs and10663 full association ticks verified',
                   'Same-photo accepts3 are repeated one image; no permanent identity ground truth',
                   'Same boot, no OOM log, clean close do not prove power/memory/IPC cause or final hardware error zero',
                   'Cumulative memory and non-atomic resource window37.018878ms offset disclosed; failed timestamp assumption preserved',
                   'Inherited1568 metadata conflicts with executable eight-run3136/3208 caps, no protocol rewrite',
                   'Actual PNG viewed with blank missing periods; no causal factor decomposition or stable5FPS claim',
                   'Paper v3 unchanged; supplemental five rows add adverse evidence with C11 still pending'],
               'workload_trial': expected, 'paper_workload_supplement': {'path': str(supplement), 'sha256': sha(supplement),
                                                                       'numeric_rows_verified': 5, 'C11_status': 'pending'},
               'current_board_loaded_O8_verified_now': True, 'new_benchmark_explicitly_loaded_existing_O8': True,
               'current_board_O8_verification_scope': 'At failed-task collection in same boot; does not alter previous recovery-only scope.',
               'current_workload_timing_complete_balanced_repetitions': False,
               'full_periodic_5FPS_target_fixed': False, 'main_paper_contribution_verified': False,
               'paper_ready_for_submission': False, 'whole_goal_complete': False})
output = ROOT / 'results/overview_review_20261031_v23_workload.json'
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'status': result['status'], 'links': len(links), 'bound_records': len(records),
                  'supplement_numeric_rows': 5, 'whole_goal_complete': False}))
