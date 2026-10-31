"""Audit real startup clocks, PSS scopes and four warmup outputs; no inference."""
from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
BOARD = ROOT / 'delivery'
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
plan = load(BOARD / 'run_protocol.json')
assert sha(BOARD / 'run_protocol.json') == sha(ROOT / 'protocol/run_v1.json') == '00098eb29e29c79949bdaaa577ab7d2f49782974a90efe909ea42c48be2eebeb'
state, terminal, final = [load(BOARD / name) for name in ['results/record.json', 'results/terminal.json', 'final_state.json']]
assert state['status'] == terminal['status'] == 'ALL4_ORIGINAL_LEAN_LEAN_ORIGINAL_STARTUP_MEASUREMENTS_COMPLETE'
assert terminal['record_sha256'] == sha(BOARD / 'results/record.json')
assert state['boot_id'] == final['boot_id'] == plan['expected_boot_id']
assert final['controller_absent'] and len(final['processes']) == 4
assert all(row['parent_absent'] and row['worker_absent'] and row['formal_jobs'] == 0 and row['warmups'] == 1 for row in final['processes'])
assert final['actual_identity_warmups'] == state['identity_warmup_forwards'] == 4
assert final['formal_identity_jobs'] == state['formal_identity_jobs'] == 0
assert state['new_O8_image_forwards'] == final['O8_image_forwards'] == terminal['new_O8_image_forwards'] == 0
assert final['all_runtime_hashes_match'] and final['shared_lock_available'] and final['PL_SHA256'] == plan['O8_bit_sha256']
assert final['hardware']['core_error'] == '0x0'
assert not ((int(final['hardware']['DMA_MM2S'], 16) | int(final['hardware']['DMA_S2MM'], 16)) & 0x770)
assert not final['collection_PL_programming'] and final['collection_model_forwards'] == 0
for row in plan['payload_files']:
    path = BOARD / row['file']
    assert sha(path) == sha(ROOT / 'payload_v1' / row['file']) == row['sha256']
    ast.parse(path.read_text(encoding='utf-8'))
assert len(final['runtime_files']) == len(plan['runtime_files'])
for actual, expected in zip(final['runtime_files'], plan['runtime_files']):
    assert actual['file'] == expected['file'] and actual['actual_sha256'] == actual['expected_sha256'] == expected['sha256']
original_entry = (BOARD / 'original_entry.py').read_text(encoding='utf-8').splitlines()
lean_entry = (BOARD / 'parent_only_entry.py').read_text(encoding='utf-8').splitlines()
removed = plan['parent_entry_variants_differ_only_by_six_foreground_import_statements']
assert len(removed) == 6 and all(original_entry.count(line) == 1 for line in removed)
assert [line for line in original_entry if line not in removed] == lean_entry
support = ast.parse((BOARD / 'startup_support.py').read_text(encoding='utf-8'))
assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ['run_image', 'run'] and isinstance(node.func.value, ast.Name) and node.func.value.id == 'graph' for node in ast.walk(support))

prior = PROJECT / 'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/old_gallery_000.npz'
source = PROJECT / 'pynq_identity_ncnn_20261029/delivery/results/export_v2/vectors/old_gallery_000.npz'
assert sha(source) == plan['warmup_file_sha256']
with np.load(prior) as archive:
    reference_input = archive['runtime_body_tensor'].copy()
    reference_raw = archive['raw'].copy()
assert hashlib.sha256(reference_input.tobytes()).hexdigest() == plan['warmup_input_tensor_sha256']
assert hashlib.sha256(reference_raw.tobytes()).hexdigest() == plan['warmup_prior_actual_ARM_raw_sha256']


def kb(text, name):
    return next(int(line.split()[1]) for line in text.splitlines() if line.startswith(name + ':'))


cases = []
working_set_hashes = set()
for spec, run in zip(plan['runs'], state['runs']):
    assert all(run[key] == value for key, value in spec.items())
    assert run['parent_exitcode'] == 0 and run['parent_absent']
    folder = BOARD / 'results' / spec['run']
    parent = load(folder / 'record.json')
    parent_end = load(folder / 'terminal.json')
    worker = load(folder / 'background/record.json')
    worker_end = load(folder / 'background/terminal.json')
    assert parent_end['record_sha256'] == sha(folder / 'record.json')
    assert worker_end['record_sha256'] == sha(folder / 'background/record.json')
    assert parent['status'] == parent_end['status'] == 'STARTUP_MEASUREMENT_COMPLETE_WITH_40S_DEADLINE_RESULT_RECORDED'
    assert worker['status'] == worker_end['status'] == 'ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'
    assert parent['PID'] == run['parent_PID'] and parent['child_PID'] == worker['PID'] == worker_end['PID']
    assert parent['child_exitcode'] == 0 and parent['child_absent_after_join'] and parent['close_error'] is None
    assert parent['graph_status_before_close']['error'] == '0x0'
    assert parent['stationary_foreground']['new_O8_image_forwards'] == 0
    assert parent['stationary_foreground']['framebank_bytes'] == 392 * 192 * 192 * 3
    assert parent['stationary_foreground']['prehistory_ticks'] == 1783 and parent['stationary_foreground']['prehistory_four_traces_exact']
    working_set_hashes.add(parent['stationary_foreground']['framebank_sha256'])
    assert worker['jobs'] == [] and worker['model_forwards'] == worker_end['model_forwards'] == 0 and len(worker['warmups']) == 1
    assert worker['actual_nice'] == 10 and worker['actual_CPU_affinity'] == [0, 1] and worker['NCNN_threads'] == 1
    assert all(mask == [0, 1] for mask in worker['after_warmup_thread_affinities'].values())
    assert worker['PL_actions'] == 0 and not worker['torch_imported']
    assert worker['encoder_bin_sha256'] == plan['models']['old']['encoder_bin_sha256']
    with np.load(folder / 'background/warmup_actual.npz') as archive:
        assert archive['input'].tobytes() == reference_input.tobytes()
        assert archive['raw'].tobytes() == reference_raw.tobytes()
    warm = worker['warmups'][0]
    assert warm['input_tensor_sha256'] == plan['warmup_input_tensor_sha256'] and warm['raw_sha256'] == plan['warmup_prior_actual_ARM_raw_sha256']
    times = worker['startup_probe']
    expected_imported = spec['variant'] == 'original'
    assert times['pynq_imported'] is times['cv2_imported'] is times['frame_pipeline_imported'] is expected_imported
    phases = ['module_begin_monotonic_ns', 'module_end_monotonic_ns', 'worker_entered_monotonic_ns',
              'before_encoder_init_monotonic_ns', 'after_encoder_init_monotonic_ns', 'gallery_and_input_ready_monotonic_ns',
              'warm_started_monotonic_ns', 'warm_finished_monotonic_ns', 'before_READY_put_monotonic_ns', 'after_READY_put_return_monotonic_ns']
    assert [times[key] for key in phases] == sorted(times[key] for key in phases)
    assert parent['before_child_start_monotonic_ns'] <= times['module_begin_monotonic_ns']
    assert parent['before_child_start_monotonic_ns'] <= parent['after_child_start_return_monotonic_ns'] <= parent['before_READY_wait_monotonic_ns'] <= parent['ready_received_monotonic_ns']
    assert parent['ready_response']['before_READY_put_monotonic_ns'] == times['before_READY_put_monotonic_ns'] <= parent['ready_received_monotonic_ns']
    assert warm['ms'] == (times['warm_finished_monotonic_ns'] - times['warm_started_monotonic_ns']) / 1e6
    for key, pid in [('child_at_READY', worker['PID']), ('parent_at_READY', parent['PID'])]:
        snapshot = parent[key]
        assert snapshot['PID'] == pid and parent['ready_received_monotonic_ns'] <= snapshot['sample_started_monotonic_ns'] <= snapshot['sample_finished_monotonic_ns'] <= parent['stop_requested_monotonic_ns']
    cp = kb(parent['child_at_READY']['smaps_rollup'], 'Pss')
    pp = kb(parent['parent_at_READY']['smaps_rollup'], 'Pss')
    cases.append({'run': spec['run'], 'variant': spec['variant'], 'parent_PID': parent['PID'], 'worker_PID': worker['PID'],
                  'start_to_READY_received_ms': (parent['ready_received_monotonic_ns'] - parent['before_child_start_monotonic_ns']) / 1e6,
                  'READY_queue_wait_ms': (parent['ready_received_monotonic_ns'] - parent['before_READY_wait_monotonic_ns']) / 1e6,
                  'READY_queue_wait_40s_expired': parent['ready_wait_40s_expired'],
                  'start_to_READY_received_within_40s': parent['ready_received_monotonic_ns'] <= parent['before_child_start_monotonic_ns'] + 40000000000,
                  'module_import_ms': (times['module_end_monotonic_ns'] - times['module_begin_monotonic_ns']) / 1e6,
                  'encoder_construct_and_bin_hash_ms': (times['after_encoder_init_monotonic_ns'] - times['before_encoder_init_monotonic_ns']) / 1e6,
                  'gallery_and_input_read_ms': (times['gallery_and_input_ready_monotonic_ns'] - times['after_encoder_init_monotonic_ns']) / 1e6,
                  'warm_network_ms': warm['ms'],
                  'post_warm_to_READY_put_ms': (times['before_READY_put_monotonic_ns'] - times['warm_finished_monotonic_ns']) / 1e6,
                  'READY_put_call_to_parent_received_ms': (parent['ready_received_monotonic_ns'] - times['before_READY_put_monotonic_ns']) / 1e6,
                  'child_Pss_kB': cp, 'parent_Pss_kB': pp, 'two_sample_Pss_sum_kB': cp + pp,
                  'child_VmRSS_kB': kb(parent['child_at_READY']['status'], 'VmRSS'),
                  'child_VmSwap_kB': kb(parent['child_at_READY']['status'], 'VmSwap'),
                  'parent_VmSwap_kB': kb(parent['parent_at_READY']['status'], 'VmSwap'),
                  'foreground_imports_in_child': expected_imported, 'warmup_raw_prior_ARM_byte_exact': True})
assert len(cases) == len(state['runs']) == 4 and len(working_set_hashes) == 1
pairs = []
for old_index, lean_index in [(0, 1), (3, 2)]:
    old, lean = cases[old_index], cases[lean_index]
    pairs.append({'original_run': old['run'], 'parent_only_run': lean['run'],
                  'original_minus_parent_only_start_to_READY_ms': old['start_to_READY_received_ms'] - lean['start_to_READY_received_ms'],
                  'original_minus_parent_only_child_Pss_kB': old['child_Pss_kB'] - lean['child_Pss_kB'],
                  'original_minus_parent_only_two_sample_Pss_sum_kB': old['two_sample_Pss_sum_kB'] - lean['two_sample_Pss_sum_kB']})
result = {'status': 'ALL4_STARTUP_CLOCKS_IMPORT_VARIANTS_PSS_AND_FOUR_KNOWN_ARM_WARMUP_VECTORS_VERIFIED',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'cases': cases, 'mirrored_adjacent_pairs': pairs,
          'actual_ARM_identity_warmups': 4, 'actual_O8_image_forwards': 0, 'actual_formal_identity_jobs': 0,
          'new_CPU_model_forwards': 0, 'models_or_thresholds_changed': False,
          'source_import_only_difference_verified': True, 'framebank_bytes': 43352064,
          'framebank_identical_across_four_parents': True, 'current_error_register_zero_at_collection': True,
          'two_process_Pss_sum_is_sequential_samples_not_whole_system_or_CMA_peak': True,
          'original_40s_queue_timeout_reproduced': any(case['READY_queue_wait_40s_expired'] for case in cases),
          'same_accumulated_five_period_state_reproduced': False, 'periodic_5FPS_tested': False,
          'original_full_system_timeout_root_cause_proven': False, 'whole_goal_complete': False}
output = ROOT / 'results/independent_verification.json'
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
