"""Keep the unused eight-run verifier; derive an explicitly failed-plan audit."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
source = (root / 'tools/verify_results.py').read_text(encoding='utf-8')
replacements = [
    ("final = load(BOARD / 'final_state.json')", "final = load(BOARD / 'failed_final_state_v1.json')"),
    ("assert state['status'] == terminal['status'] == 'ALL8_WORKLOAD_2X2_MIRROR_ORDER_REPEATS_COMPLETE'",
     "assert state['status'] == terminal['status'] == 'FAILED'\nassert state['error'] == 'Empty()' and 'ready.get(timeout=40)' in state['traceback']"),
    ("assert state['qualification_forwards'] == 8 and state['warmup_forwards'] == 16",
     "assert state['qualification_forwards'] == 8 and state['warmup_forwards'] == 12"),
    ("assert state['hardware_status']['error'] == '0x0'",
     "assert state.get('hardware_status') is None  # Failed before final status sampling; no clean-error claim."),
    ("assert len(state['cases']) == 8", "assert len(state['cases']) == 5"),
    ("for spec, case in zip(plan['runs'], state['cases']):", "for spec, case in zip(plan['runs'][:5], state['cases']):"),
    ("assert len(actual_jobs) == 40 and len({row['photo_sha256'] for row in actual_jobs}) == 10",
     "assert len(actual_jobs) == 30 and len({row['photo_sha256'] for row in actual_jobs}) == 10"),
    ("assert total_produced == 4 * 392 and total_ticks == 8 * 1783 + total_raw and total_paths == 16",
     "assert total_produced == 3 * 392 and total_ticks == 5 * 1783 + total_raw and total_paths == 10"),
    ("actual_total = total_raw + 8 + 16 + 40 + 8",
     "assert len(final['children']) == 6\nassert sum(row['formal_jobs'] for row in final['children']) == 30\nassert sum(row['warmups'] for row in final['children']) == 6\nsixth = BOARD / 'results/r6_C'\nassert load(sixth / 'prewarm_history_gate.json')['cached_ticks'] == 1783\nsixth_worker = load(sixth / 'background/record.json')\nassert sixth_worker['model_forwards'] == 0 and len(sixth_worker['warmups']) == 1\nassert not (sixth / 'actual_raw.npz').exists()\nassert not (BOARD / 'results/r7_B').exists() and not (BOARD / 'results/r8_A').exists()\nactual_total = total_raw + 8 + 12 + 30 + 6\nassert actual_total == 1804"),
    ("ALL8_SAVED_RAW_TIMING_EVENTS_PRODUCER_FIXED40_IDENTITY_AND_RESOURCE_COUNTERS_VERIFIED_WITH_DISCLOSED_PROTOCOL_METADATA_INCONSISTENCY",
     "FAILED_EIGHT_RUN_PLAN_FIRST5_COMPLETE_CASES_RAW_TIMING_EVENTS_PRODUCER_FIXED30_IDENTITY_AND_RESOURCE_COUNTERS_VERIFIED"),
    ("'actual_O8_qualification_forwards': 8, 'actual_O8_warmups': 16,",
     "'actual_O8_qualification_forwards': 8, 'actual_O8_warmups': 12,"),
    ("'actual_ARM_timed_queries': 40, 'actual_ARM_warmups': 8,",
     "'actual_ARM_timed_queries': 30, 'actual_ARM_warmups': 6,"),
    ("'fixed_photo_tensor_raw_feature_score_jobs_verified': 40, 'unique_fixed_photos': 10,",
     "'fixed_photo_tensor_raw_feature_score_jobs_verified': 30, 'unique_fixed_photos': 10,\n          'planned_timed_cases': 8, 'completed_timed_cases': 5, 'task_status': 'FAILED',\n          'sixth_case_prepared_but_period_not_started': True, 'last2_cases_not_started': True,\n          'sixth_case_cached_history_gate_ticks': 1783, 'native_device_final_error_status_not_captured': True,"),
]
for before, after in replacements:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
source = source.replace('"""Independently recompute saved 2x2 timing, events, input and identity outputs.',
                        '"""Audit five saved periods from an eight-case plan that FAILED in case6 preparation.')
ast.parse(source)
with (root / 'tools/verify_partial_results_v1.py').open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Explicit failed-plan verification script created; no models run.')
