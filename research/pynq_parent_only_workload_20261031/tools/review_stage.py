"""Bind all available device, numeric, reference and manually read prose evidence."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote
import ast, hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
v = load(ROOT / 'results/independent_verification.json')
t = load(ROOT / 'results/tracker_reference_verification.json')
drop = load(ROOT / 'results/dropped_frame_counterfactual_verification.json')
scope = load(ROOT / 'results/outcome_scope.json')
state = load(ROOT / 'delivery/results/record.json')
terminal = load(ROOT / 'delivery/results/terminal.json')
post = json.loads(load(ROOT / 'evidence/postflight01.json')['stdout'])
assert state['status'] == terminal['status'] == 'ALL8_WORKLOAD_2X2_MIRROR_ORDER_REPEATS_COMPLETE'
assert terminal['record_sha256'] == sha(ROOT / 'delivery/results/record.json') and terminal['close_error'] is None
assert not state['explicit_O8_programming']
assert v['actual_timed_O8_forwards'] == 3115 and v['all_new_actual_board_forwards'] == 3187
assert t['observation_ticks'] == 17379 and t['post_tracker_rows'] == 4162 and t['counter_paths'] == 16
assert [case['processed_frames'] for case in v['cases']] == [392, 388, 389, 387, 384, 391, 392, 392]
assert [case['source_down_count'] for case in v['cases']] == [10, 10, 10, 10, 9, 10, 10, 10]
assert [case['deadline_misses'] for case in v['cases']] == [0, 200, 79, 65, 144, 55, 0, 0]
assert post['parent_and_all8_children_and_collector_absent'] and post['lock_available'] and post['core_error'] == '0x0'
assert post['services'] == {'ssh': 'active', 'jupyter': 'active'} and post['kernel_memory_messages'] == []
assert not post['PL_programmed'] and post['new_model_forwards'] == 0
assert not scope['all_slots_processed'] and not scope['all_offered_deadlines_met'] and not scope['all8_total_count_equals_human12']
jobs = load(ROOT / 'results/actual_job_rows.json')
accepted = [row for row in jobs if row['accepted']]
assert len(jobs) == 40 and len(accepted) == 4 and len({row['photo_sha256'] for row in accepted}) == 1
assert drop['observation_ticks'] == 19519 and drop['counter_paths'] == 18
single_recoveries = [row['restored_frames'][0] for row in drop['reports'] if len(row['restored_frames']) == 1 and row['down_count'] == 10]
assert single_recoveries == [9515] and drop['reports'][-1]['down_count'] == 10
report = ROOT / '精简后台导入_八轮负载与剩余问题.md'
review = ROOT / 'Review与当前状态.md'
text = report.read_text(encoding='utf-8')
for case in v['cases']:
    row = f"| {case['run']} | {int(case['input_producer'])}/{int(case['identity_workload'])} | {case['processed_frames']} | {case['skipped_slots']} | {case['deadline_misses']} | {case['processed_per_second_over_offered_duration']:.3f} | {case['P95_release_to_count_ms']:.2f} | {case['source_down_count']} |"
    assert row in text
for phrase in ['4.936／4.898FPS', '未收到独立事件JSON', '原40秒超时的唯一根因仍未证明',
               '不是纯PL时间', '19519观察／18事件状态路径', '不是人工12', '四次启动探针另计4']:
    assert phrase in text, phrase
figure_manifest = load(ROOT / 'reference_delivery/results/figure_manifest.json')
assert figure_manifest['source_sha256'] == sha(ROOT / 'results/independent_verification.json')
for row in figure_manifest['files']:
    assert sha(ROOT / 'reference_delivery' / row['file']) == row['sha256']
visual = {'status': 'ACTUAL_EIGHT_POINT_PNG_VISUALLY_REVIEWED', 'created_UTC': datetime.now(timezone.utc).isoformat(),
          'file': str((ROOT / 'reference_delivery/results/figures/chronological_workload.png').resolve()),
          'sha256': figure_manifest['files'][0]['sha256'],
          'observations': ['Eight FPS annotations and condition labels fit.', 'Zero/positive deadline bars and skipped markers retained.',
                           'VmSwap axis, units and ready-input replay scope legible; no clipping.'], 'new_model_forwards': 0}
with (ROOT / 'results/figure_visual_review.json').open('x', encoding='utf-8') as stream:
    json.dump(visual, stream, indent=2)
    stream.write('\n')
links = []
for document in [report, review]:
    for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)', document.read_text(encoding='utf-8')):
        target = unquote((match[1] or match[2]).strip())
        if target.startswith(('http://', 'https://', '#')):
            continue
        path = Path(target)
        path = path if path.is_absolute() else document.parent / path
        assert path.exists(), target
        links.append(str(path.resolve()))
evidence = ['protocol/run_v1.json', 'delivery/results/record.json', 'delivery/results/terminal.json',
            'delivery/final_state.json', 'delivery/preflight.json', 'results/independent_verification.json',
            'results/tracker_reference_verification.json', 'results/dropped_frame_counterfactual_verification.json',
            'results/board_archive_verification.json', 'results/reference_archive_verification.json',
            'results/descriptive_contrasts.json', 'results/outcome_scope.json', 'results/figure_visual_review.json',
            'reference_delivery/results/figure_manifest.json', 'reference_delivery/results/tracker_replay/summary.json',
            'reference_delivery/results/dropped_frame_counterfactual/summary.json', 'reference_delivery/logs/tracker_sacct.txt',
            'evidence/input_bundle_review_v1.json', 'evidence/postflight01.json']
tools = ['tools/prepare_payload_v1.py', 'tools/verify_results.py', 'tools/verify_tracker_reference.py',
         'tools/verify_drop_reference.py', 'tools/drop_counterfactual.py', 'tools/collect_results.py',
         'tools/write_report.py', 'tools/review_stage.py', 'tools/plot_results.py']
for name in tools:
    ast.parse((ROOT / name).read_text(encoding='utf-8'))
result = {'status': 'ALL8_PARENT_ONLY_IMPORT_WORKLOAD_AND_POSTHOC_DROP_DIAGNOSIS_FULLY_REVIEWED_REMAINING_5FPS_AND12_GT_GAPS',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'all8_complete': True,
          'actual_counts': [case['source_down_count'] for case in v['cases']],
          'processed_frames': [case['processed_frames'] for case in v['cases']],
          'skipped_slots': [case['skipped_slots'] for case in v['cases']],
          'deadline_misses': [case['deadline_misses'] for case in v['cases']],
          'actual_timed_O8_forwards': 3115, 'O8_qualification_forwards': 8, 'O8_warmups': 16,
          'formal_identity_jobs': 40, 'identity_warmups': 8, 'all_actual_board_image_forwards': 3187,
          'separate_startup_probe_warmups': 4, 'new_CPU_model_forwards': 0,
          'producer_records': 1568, 'frontend_receipts': 1551, 'overlapping_model_IO_cases': 1394,
          'full_association_ticks': 17379, 'full_association_rows': 4162, 'full_association_event_paths': 16,
          'CPU_reference_job_id': t['Slurm_job_id'], 'accepted_same_fixed_photo_repeats': 4,
          'drop_diagnosis_variants': 9, 'drop_diagnosis_observation_ticks': 19519, 'drop_diagnosis_event_paths': 18,
          'single_backfill_9515_restores_model_reference10_not_human12': True,
          'same_boot_but_not_initial_overlay_cache_swap_matched_to_old_failed_trial': True,
          'source_only_moves_six_foreground_imports': True, 'original_failed_trial_restarted_or_overwritten': False,
          'current_devices_clean_services_active_all_task_PIDs_absent': True,
          'original40s_timeout_root_cause_proven': False,
          'no_new_periodic_ready_timeout_observed': True, 'all_offered_slots_processed': False,
          'all_offered_200ms_deadlines_met': False, 'human_total12_consistently_recovered': False,
          'independent_event_or_permanent_identity_GT_received': False, 'real_camera_RFID_5FPS_proven': False,
          'main_paper_contribution_verified': False, 'whole_goal_complete': False,
          'manual_full_report_read': True, 'actual_result_PNG_viewed': True, 'local_links_checked': len(links),
          'evidence_hashes': {name: sha(ROOT / name) for name in evidence},
          'documents': [{'path': str(path.resolve()), 'sha256': sha(path)} for path in [report, review]],
          'reviewed_tools': [{'path': str((ROOT / name).resolve()), 'sha256': sha(ROOT / name)} for name in tools]}
with (ROOT / 'results/final_review_v1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({key: value for key, value in result.items() if key not in ['evidence_hashes', 'documents', 'reviewed_tools']}))
