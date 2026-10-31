"""Bind manually read failed-plan prose to numeric and implementation evidence."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote
import ast, hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
verification = load(ROOT / 'results/independent_verification.json')
tracker = load(ROOT / 'results/tracker_reference_verification.json')
state = load(ROOT / 'delivery/results/record.json')
terminal = load(ROOT / 'delivery/results/terminal.json')
final = load(ROOT / 'delivery/failed_final_state_v1.json')
assert state['status'] == terminal['status'] == verification['task_status'] == 'FAILED'
assert terminal['record_sha256'] == sha(ROOT / 'delivery/results/record.json')
assert state['error'] == 'Empty()' and not state['pending_background_child']['alive']
cases = verification['cases']
assert [case['source_down_count'] for case in cases] == [7, 8, 10, 10, 3]
assert [case['processed_frames'] for case in cases] == [368, 368, 383, 343, 286]
assert [case['deadline_misses'] for case in cases] == [16, 35, 86, 342, 286]
assert verification['all_new_actual_board_forwards'] == 1804
assert tracker['observation_ticks'] == 10663 and tracker['post_tracker_rows'] == 2338 and tracker['counter_paths'] == 10
assert all(row['IDs_and_events_exact'] and row['maximum_box_difference'] == row['maximum_axis_difference'] == 0 for row in tracker['reports'])
assert final['parent_absent'] and all(not row['proc_exists'] for row in final['children'])
assert final['all_runtime_hashes_match'] and final['shared_lock_available']
assert final['kernel_log_returncode'] == 0 and final['kernel_memory_matches'] == []
assert final['services'] == {'ssh': 'active', 'jupyter': 'active'}
report = ROOT / '高分输入与身份负载_五轮结果和启动超时.md'
review = ROOT / 'Review与当前状态.md'
text = report.read_text(encoding='utf-8')
for case in cases:
    row = f"| {case['run']} | {int(case['input_producer'])}／{int(case['identity_workload'])} | {case['processed_frames']}／392 | {case['skipped_slots']} | {case['deadline_misses']} | {case['processed_per_second_over_offered_duration']:.3f} | {case['P95_release_to_count_ms']:.2f} | {case['source_down_count']} |"
    assert row in text
for phrase in ['第6轮在等待后台READY超过40秒后失败', '不是纯PL计算时间', '第5轮晚37.018878毫秒',
               '不能称找回3头奶牛', '没有最终`error=0x0`记录', '尚未宣告根因或修复完成',
               '稳定5FPS', '17分钟级', '没有独立逐事件JSON']:
    assert phrase in text, phrase
for archive, record in [('failure_delivery_v1.tar.xz', 'board_archive_verification.json'),
                        ('tracker_reference_delivery_v1.tar.xz', 'reference_archive_verification.json')]:
    verified = load(ROOT / 'results' / record)
    assert (ROOT / archive).stat().st_size == verified['archive_bytes'] and sha(ROOT / archive) == verified['archive_sha256']
visual = load(ROOT / 'results/figure_visual_review.json')
assert visual['status'] == 'ACTUAL_RENDERED_PNG_VISUALLY_REVIEWED'
assert sha(Path(visual['figure_file'])) == visual['sha256']
figure_manifest = load(ROOT / 'reference_delivery/results/figure_manifest.json')
assert figure_manifest['source_sha256'] == sha(ROOT / 'results/independent_verification.json')
for row in figure_manifest['files']:
    assert sha(ROOT / 'reference_delivery' / row['file']) == row['sha256']
links = []
for document in [report, review]:
    for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)', document.read_text(encoding='utf-8')):
        target = unquote((match[1] or match[2]).strip())
        if target.startswith(('https://', 'http://', '#')):
            continue
        path = Path(target)
        path = path if path.is_absolute() else document.parent / path
        assert path.exists(), target
        links.append(str(path.resolve()))
evidence = ['protocol/run_v2.json', 'delivery/results/record.json', 'delivery/results/terminal.json',
            'delivery/failed_final_state_v1.json', 'results/board_archive_verification.json',
            'results/reference_archive_verification.json', 'results/independent_verification.json',
            'results/tracker_reference_verification.json', 'results/shared_frame_timing.json',
            'results/figure_visual_review.json', 'reference_delivery/results/figure_manifest.json',
            'reference_delivery/results/tracker_replay/summary.json', 'reference_delivery/logs/tracker_sacct.txt',
            'evidence/protocol_metadata_review.json', 'evidence/verification_v1_failure_and_v2_correction.json']
tools = ['tools/collect_failed_results_v1.py', 'tools/verify_archive.py', 'tools/verify_partial_results_v2.py',
         'tools/verify_partial_tracker_reference_v1.py', 'tools/replay_tracker.py',
         'tools/plot_partial_results_v1.py', 'tools/write_partial_report_v1.py', 'tools/review_partial_stage_v1.py']
for name in tools:
    ast.parse((ROOT / name).read_text(encoding='utf-8'))
result = {'status': 'FAILED_EIGHT_RUN_PLAN_FIVE_COMPLETE_PERIODS_FULLY_AUDITED_NOT_5FPS_OR_CAUSAL_FACTOR_SUCCESS',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'task_status': 'FAILED',
          'planned_timed_cases': 8, 'completed_timed_cases': 5, 'sixth_prepared_period_unstarted': True,
          'last_two_cases_unstarted': True, 'conditions': [case['condition'] for case in cases],
          'actual_counts': [case['source_down_count'] for case in cases],
          'processed_frames': [case['processed_frames'] for case in cases],
          'skipped_slots': [case['skipped_slots'] for case in cases],
          'deadline_misses': [case['deadline_misses'] for case in cases],
          'actual_timed_O8_forwards': 1748, 'O8_qualification_forwards': 8, 'O8_warmups': 12,
          'actual_identity_jobs': 30, 'identity_warmups': 6, 'all_actual_board_image_forwards': 1804,
          'producer_records': 1176, 'frontend_receipts': 997, 'model_IO_overlapping_cases': 765,
          'full_association_ticks': 10663, 'full_association_rows': 2338, 'counter_paths': 10,
          'CPU_replay_job_id': '130931', 'new_CPU_model_reference_forwards': 0,
          'unique_fixed_photos': 10, 'threshold_accepts_repeated_same_photo': 3,
          'all_available_outputs_and_original_failure_received_and_verified': True,
          'same_boot_preserved': True, 'runtime_files_unchanged': True, 'O8_explicitly_loaded_for_this_new_benchmark': True,
          'current_O8_identity_verified_at_collection': True, 'native_final_error_register_not_captured': True,
          'kernel_OOM_log_found': False, 'power_or_memory_or_IPC_root_cause_proven': False,
          'first_five_not_a_complete_balanced_factorial': True, 'original_failed_experiment_restarted': False,
          'verifier_v1_incorrect_timestamp_assumption_preserved_corrected_in_v2': True,
          'inherited_protocol_budget_metadata_conflict_disclosed': True,
          'manual_report_full_read': True, 'actual_PNG_visually_reviewed': True, 'local_links_checked': len(links),
          'independent_human_event_JSON_received': False, 'permanent_passage_identity_GT_received': False,
          'full5FPS_target_achieved': False, 'actual_camera_RFID_proven': False, 'power_measurement_obtained': False,
          'main_paper_contribution_verified': False, 'whole_goal_complete': False,
          'evidence_hashes': {name: sha(ROOT / name) for name in evidence},
          'documents': [{'path': str(path.resolve()), 'sha256': sha(path)} for path in [report, review]],
          'reviewed_tools': [{'path': str((ROOT / name).resolve()), 'sha256': sha(ROOT / name)} for name in tools],
          'unused_full_eight_run_success_tools_not_executed': ['tools/collect_results.py', 'tools/verify_results.py',
                                                              'tools/prepare_tracker_replay.py', 'tools/verify_tracker_reference.py', 'tools/plot_results.py']}
with (ROOT / 'results/final_review_v1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({key: value for key, value in result.items() if key not in ['evidence_hashes', 'documents', 'reviewed_tools', 'unused_full_eight_run_success_tools_not_executed']}))
