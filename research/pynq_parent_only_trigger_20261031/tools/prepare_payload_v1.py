"""Parent-only imports plus explicit provenance/budget guards for dynamic jobs."""
from pathlib import Path
from datetime import datetime, timezone
import ast, difflib, hashlib, json, tarfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
oldroot = PROJECT / 'identity_trigger_pair_20261030'
old = load(oldroot / 'protocol/run_v1.json')
pre = json.loads(load(ROOT / 'evidence/preflight01.json')['stdout'])
assert pre['active_task_processes'] == [] and pre['services'] == {'ssh': 'active', 'jupyter': 'active'}
assert pre['PL_SHA256'] == old['O8_bit_sha256'] and pre['hardware']['core_error'] == '0x0'
source_path = oldroot / 'tools/board_trigger_repeats.py'
assert sha(source_path) == next(row['sha256'] for row in old['payload_files'] if row['file'] == source_path.name)
source = source_path.read_text(encoding='utf-8')
changed = source
assert changed.count('import cv2,numpy as np\n') == 1
changed = changed.replace('import cv2,numpy as np\n', 'import numpy as np\n', 1)
imports = ['import cv2', 'from pynq import PL', 'from native_graph import NativeGraph',
           'from device_initialize import initialize', 'from board_runtime import decode', 'from frame_pipeline import FramePipeline']
for line in imports[1:]:
    assert changed.splitlines().count(line) == 1
    changed = changed.replace(line + '\n', '', 1)
assert changed.count('def main():\n') == 1
changed = changed.replace('def main():\n', 'def main():\n' + ''.join(' ' + line + '\n' for line in imports), 1)
guard_changes = [
    (" try:\n  for row in p['payload_files']:", " try:\n  assert state['boot_id']==p['expected_boot_id']\n  state['PL_before']=PL.bitfile_name\n  for row in p['payload_files']:"),
    ("  assert it['record_sha256']==sha(IDENTITY/'vectors_results_v3/record.json') and not (Path('/proc')/str(it['PID'])).exists()",
     "  assert it['record_sha256']==sha(IDENTITY/'vectors_results_v3/record.json')\n  state['historical_identity_qualification']={'saved_PID':it['PID'],'saved_boot_id':ir.get('boot_id'),'PID_compared_across_boots':False}"),
    ("  assert vt['record_sha256']==sha(VIDEO/'results/record.json') and not (Path('/proc')/str(vt['PID'])).exists()",
     "  assert vt['record_sha256']==sha(VIDEO/'results/record.json')\n  state['historical_video_qualification']={'saved_PID':vt['PID'],'saved_boot_id':vr.get('boot_id'),'PID_compared_across_boots':False}"),
    ("      requests.put_nowait(job);enqueued.append({k:v for k,v in job.items() if k!='_jpeg_payload'})",
     "      assert len(enqueued)<p['maximum_identity_jobs_per_case'],'DynamicIdentityBudgetCapReachedBeforePublish'\n      requests.put_nowait(job);enqueued.append({k:v for k,v in job.items() if k!='_jpeg_payload'})"),
]
for before, after in guard_changes:
    assert changed.count(before) == 1, before
    changed = changed.replace(before, after, 1)
ast.parse(changed)
stage = ROOT / 'payload_v1'
stage.mkdir(exist_ok=False)
(stage / source_path.name).write_bytes(changed.encode())
for name in ['background_selected_worker.py', 'causal_selector.py', 'jpeg_producer.py', 'process_cpu.py']:
    path = oldroot / 'tools' / name
    expected = next(row['sha256'] for row in old['payload_files'] if row['file'] == name)
    assert sha(path) == expected
    (stage / name).write_bytes(path.read_bytes())
    ast.parse((stage / name).read_text(encoding='utf-8'))
runtime = {row['file']: dict(row) for row in old['runtime_files']}
previous = load(PROJECT / 'pynq_parent_only_workload_20261031/protocol/run_v1.json')
for row in previous['runtime_files']:
    if row['file'] in runtime:
        assert runtime[row['file']]['sha256'] == row['sha256']
    runtime[row['file']] = dict(row)
for model in old['models'].values():
    runtime[model['gallery_features_file']] = {'file': model['gallery_features_file'], 'sha256': model['gallery_SHA256']}
runtime[old['camera_root'] + '/manifest.json'] = {'file': old['camera_root'] + '/manifest.json', 'sha256': previous['camera_manifest_SHA256']}
warm = '/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/vectors/old_gallery_000.npz'
runtime[warm] = {'file': warm, 'sha256': '3b2e3ba40bb2884f1022bc15cf1ae33a3b917bd7275fc35a89623b4ad954601f'}
for row in pre['sources']:
    for name in ['record', 'terminal']:
        path = row['folder'] + '/' + name + '.json'
        runtime[path] = {'file': path, 'sha256': row[name + '_sha256']}
keys = ['video', 'tracker_config', 'counter_kwargs', 'registered_IDs', 'fixed_identity_threshold',
        'backend_nice_increment', 'foreground_source_model', 'O8_bit_sha256', 'camera_root',
        'graph_sha256', 'resident_plan_sha256', 'selector', 'period_ns', 'runs',
        'foreground_affinity', 'background_affinity', 'models', 'secondary_Cows_threshold']
plan = {key: old[key] for key in keys}
plan.update({'status': 'FROZEN_BEFORE_PARENT_ONLY_ACTUAL_COUNT_TRIGGER_REPEATS',
             'created_UTC': datetime.now(timezone.utc).isoformat(), 'expected_boot_id': pre['boot_id'],
             'source_original_protocol_sha256': sha(oldroot / 'protocol/run_v1.json'),
             'source_original_driver_sha256': sha(source_path),
             'source_parent_only_fixed8_review_sha256': sha(PROJECT / 'pynq_parent_only_workload_20261031/results/final_review_v1.json'),
             'runtime_files': list(runtime.values()), 'O8_hwh_sha256': previous['O8_hwh_sha256'],
             'cases': ['low_priority_parallel'], 'offered_slots_per_case': 392,
             'maximum_identity_jobs_per_case': 16, 'maximum_formal_identity_queries': 64,
             'expected_qualification_O8_forwards': 8, 'expected_detection_warmups': 8,
             'maximum_timed_O8_forwards': 1568, 'expected_identity_warmups': 4,
             'maximum_total_board_image_forwards': 1652,
             'maximum_new_CPU_query_reference_forwards': 64, 'reuse_verified_CPU_galleries_if_hashes_match': True,
             'source_change_scope': 'Split combined cv2/numpy import; move six foreground imports into main. Add current-boot and dynamic-job budget guards; historical source PID checks replaced by boot-aware provenance metadata. Numeric paths and four helper files unchanged.',
             'historical_qualification_PIDs_not_compared_to_current_boot': True,
             'PNG_compress_level': 0, 'lowres192_is_ready_replay_not_derived_from_current_JPEG_at_runtime': True,
             'simulated_RFID_all_unread': True, 'jobs_decoupled_from_current_counter': False,
             'exactly10_identity_jobs_forced': False, 'actual_camera_or_RFID_hardware': False,
             'source_all_JPEG_integrity_hash_read_before_first_period': True,
             'same_replay_repeats_not_independent_sessions': True, 'global_cache_or_swap_controls': False,
             'selector_or_counter_or_identity_threshold_changed': False,
             'default_model_or_threshold_changed': False, 'new_training_updates': 0,
             'new_independent_test': False, 'posthoc_development_after_fixed8_and_startup_probe': True,
             'whole_goal_complete': False})
plan['payload_files'] = [{'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)} for path in sorted(stage.glob('*.py'))]
folder = ROOT / 'protocol'
folder.mkdir(exist_ok=False)
encoded = (json.dumps(plan, indent=2) + '\n').encode()
(folder / 'run_v1.json').write_bytes(encoded)
(stage / 'run_protocol.json').write_bytes(encoded)
diff = list(difflib.unified_diff(source.splitlines(), changed.splitlines(), fromfile='original_trigger_driver.py', tofile='parent_only_trigger_driver.py'))
(ROOT / 'evidence/driver_imports_and_guard_diff.txt').write_bytes(('\n'.join(diff) + '\n').encode())
archive = ROOT / 'parent_only_trigger_input_v1.tar.gz'
assert not archive.exists()
with tarfile.open(archive, 'w:gz') as tar:
    for path in sorted(stage.iterdir()):
        tar.add(path, arcname=path.name, recursive=False)
review = {'status': 'PARENT_ONLY_DYNAMIC_TRIGGER_IMPORTS_GUARDS_FOUR_UNCHANGED_HELPERS_AND1652_BUDGET_REVIEWED',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': sha(folder / 'run_v1.json'),
          'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha(archive), 'members': len(list(stage.iterdir())),
          'four_helper_files_byte_identical_to_original': True, 'maximum_board_image_forwards': 1652,
          'new_model_forwards': 0, 'historical_source_boots': [row['historical_boot_id'] for row in pre['sources']]}
with (ROOT / 'evidence/input_bundle_review_v1.json').open('x', encoding='utf-8') as stream:
    json.dump(review, stream, indent=2)
    stream.write('\n')
print(json.dumps(review))
