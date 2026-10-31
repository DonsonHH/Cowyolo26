"""Move only six foreground imports; freeze a fresh complete workload protocol."""
from pathlib import Path
from datetime import datetime, timezone
import ast, copy, difflib, hashlib, json, tarfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
prior = PROJECT / 'pynq_workload_ablation_20261031'
probe = PROJECT / 'pynq_startup_probe_20261031'
verified = load(probe / 'results/independent_verification.json')
assert verified['actual_ARM_identity_warmups'] == 4 and verified['source_import_only_difference_verified']
assert not verified['periodic_5FPS_tested'] and not verified['original_40s_queue_timeout_reproduced']
source_plan = load(prior / 'protocol/run_v2.json')
source_path = prior / 'payload_v2/board_workload_ablation.py'
assert sha(source_path) == next(row['sha256'] for row in source_plan['payload_files'] if row['file'] == source_path.name)
source = source_path.read_text(encoding='utf-8')
imports = load(probe / 'protocol/run_v1.json')['parent_entry_variants_differ_only_by_six_foreground_import_statements']
assert len(imports) == 6
changed = source
for line in imports:
    assert changed.splitlines().count(line) == 1
    changed = changed.replace(line + '\n', '', 1)
assert changed.count('def main():\n') == 1
changed = changed.replace('def main():\n', 'def main():\n' + ''.join('    ' + line + '\n' for line in imports), 1)
old_tree, new_tree = ast.parse(source), ast.parse(changed)
expected = copy.deepcopy(old_tree)
def statement(node):
    return ast.unparse(node) if isinstance(node, (ast.Import, ast.ImportFrom)) else None
moved = [node for node in expected.body if statement(node) in imports]
assert len(moved) == 6
expected.body = [node for node in expected.body if statement(node) not in imports]
main = next(node for node in expected.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
main.body = moved + main.body
assert ast.dump(expected, include_attributes=False) == ast.dump(new_tree, include_attributes=False)
stage = ROOT / 'payload_v1'
stage.mkdir(exist_ok=False)
(stage / source_path.name).write_bytes(changed.encode())
for name in ['background_fixed_worker.py', 'fixed_arrivals.py', 'jpeg_producer.py', 'process_cpu.py']:
    (stage / name).write_bytes((prior / 'payload_v2' / name).read_bytes())
    assert sha(stage / name) == sha(prior / 'payload_v2' / name)
for path in stage.glob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'))
keep = ['video', 'tracker_config', 'counter_kwargs', 'registered_IDs', 'fixed_identity_threshold',
        'backend_nice_increment', 'foreground_source_model', 'O8_bit_sha256', 'O8_hwh_sha256',
        'camera_root', 'period_ns', 'foreground_affinity', 'runtime_files', 'fixed_jobs',
        'identity_reference_images', 'models', 'secondary_Cows_threshold', 'camera_manifest_SHA256', 'runs']
plan = {key: source_plan[key] for key in keep}
plan.update({'status': 'FROZEN_BEFORE_FIRST_PARENT_ONLY_FULL_WORKLOAD_FORWARD',
             'created_UTC': datetime.now(timezone.utc).isoformat(), 'expected_boot_id': source_plan['expected_boot_id'],
             'task_root': '/home/xilinx/jupyter_notebooks/cow_research_parent_only_workload_20261031',
             'source_failed_protocol_sha256': sha(prior / 'protocol/run_v2.json'),
             'source_driver_sha256': sha(source_path),
             'startup_probe_verification_sha256': sha(probe / 'results/independent_verification.json'),
             'only_runtime_source_change': 'Move six foreground import statements into main; original worker and all numeric paths unchanged.',
             'import_statements_moved': imports, 'source_AST_difference_only_these_moved_imports': True,
             'all_workers_resident_and_same_warmup_even_when_zero_jobs': True,
             'identity_jobs_if_workload_on': 10, 'identity_jobs_if_workload_off': 0,
             'fixed_jobs_independent_of_current_counter': True, 'offered_slots_per_case': 392,
             'expected_qualification_O8_forwards': 8, 'expected_O8_warmups': 16,
             'maximum_timed_O8_forwards': 3136, 'expected_identity_queries': 40,
             'expected_identity_warmups': 8, 'maximum_total_board_image_forwards': 3208,
             'input_factor_scope': 'Release gated JPEG producer/read/SHA/bounded bank/pin/take; fixed identity jobs still read same source file in C and D.',
             'original_framebank_is_ready_lowres_replay': True,
             'common_full_JPEG_hash_read_before_each_period': True,
             'no_global_cache_swap_frequency_or_service_controls': True,
             'actual_camera_or_RFID_hardware': False,
             'explicit_existing_O8_download_permitted_for_new_benchmark_if_required': True,
             'same_boot_but_not_same_initial_cache_swap_or_overlay_state_as_prior_failed_trial': True,
             'posthoc_development_after_failed_workload_and_startup_probe': True,
             'new_independent_test': False, 'default_model_or_threshold_changed': False,
             'new_training_updates': 0, 'whole_goal_complete': False})
plan['payload_files'] = [{'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)} for path in sorted(stage.glob('*.py'))]
folder = ROOT / 'protocol'
folder.mkdir(exist_ok=False)
encoded = (json.dumps(plan, indent=2) + '\n').encode()
(folder / 'run_v1.json').write_bytes(encoded)
(stage / 'run_protocol.json').write_bytes(encoded)
evidence = ROOT / 'evidence'
evidence.mkdir(exist_ok=False)
diff = list(difflib.unified_diff(source.splitlines(), changed.splitlines(), fromfile='failed_driver.py', tofile='parent_only_driver.py'))
(evidence / 'six_imports_only_diff.txt').write_bytes(('\n'.join(diff) + '\n').encode())
archive = ROOT / 'parent_only_input_v1.tar.gz'
assert not archive.exists()
with tarfile.open(archive, 'w:gz') as tar:
    for path in sorted(stage.iterdir()):
        tar.add(path, arcname=path.name, recursive=False)
record = {'status': 'ONLY_SIX_IMPORTS_MOVED_AST_EXACT_AND_COMPLETE_8CASE_3208_BUDGET_REVIEWED_BEFORE_EXECUTION',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': sha(folder / 'run_v1.json'),
          'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha(archive), 'members': len(list(stage.iterdir())),
          'maximum_total_board_image_forwards': 3208, 'new_model_forwards': 0}
with (evidence / 'input_bundle_review_v1.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record))
