"""Freeze import-only variants and identical startup instrumentation."""
from pathlib import Path
from datetime import datetime, timezone
import ast, difflib, hashlib, json, tarfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
preflight = json.loads(load(ROOT / 'evidence/preflight01.json')['stdout'])
assert preflight['task_processes'] == [] and preflight['shared_lock_available']
assert preflight['services'] == {'ssh': 'active', 'jupyter': 'active'}
original_root = PROJECT / 'pynq_workload_ablation_20261031'
original = load(original_root / 'protocol/run_v2.json')
assert preflight['PL_SHA256'] == original['O8_bit_sha256']
metadata = {Path(row['file']).name: row for row in preflight['files']}
source_driver = original_root / 'payload_v2/board_workload_ablation.py'
source_worker = original_root / 'payload_v2/background_fixed_worker.py'
assert sha(source_driver) == metadata[source_driver.name]['sha256']
assert sha(source_worker) == metadata[source_worker.name]['sha256']
stage = ROOT / 'payload_v1'
stage.mkdir(exist_ok=False)
driver = source_driver.read_text(encoding='utf-8')
marker = '\n\n\ndef load(path):'
assert driver.count(marker) == 1
header = driver.split(marker, 1)[0]
removed = ['import cv2', 'from pynq import PL, Overlay', 'from native_graph import NativeGraph',
           'from device_initialize import initialize', 'from board_runtime import decode',
           'from frame_pipeline import FramePipeline']
lean_header = header
for line in removed:
    assert lean_header.splitlines().count(line) == 1
    lean_header = lean_header.replace(line + '\n', '', 1)
entry_prefix = 'import time as _startup_time\nBOOTSTRAP_MODULE_BEGIN_NS = _startup_time.monotonic_ns()\n'
entry_suffix = '''
from startup_support import run_parent
BOOTSTRAP_MODULE_END_NS = _startup_time.monotonic_ns()

if __name__ == '__main__':
    run_parent(Path(__file__).name)
'''
for name, text in [('original_entry.py', entry_prefix + header + '\n' + entry_suffix),
                   ('parent_only_entry.py', entry_prefix + lean_header + '\n' + entry_suffix)]:
    (stage / name).write_bytes(text.encode())
diff = list(difflib.unified_diff((stage / 'original_entry.py').read_text().splitlines(),
                                (stage / 'parent_only_entry.py').read_text().splitlines(),
                                fromfile='original_entry.py', tofile='parent_only_entry.py'))
assert [line[1:] for line in diff if line.startswith('-') and not line.startswith('---')] == removed
assert not [line for line in diff if line.startswith('+') and not line.startswith('+++')]
(ROOT / 'evidence/import_only_diff.txt').write_bytes(('\n'.join(diff) + '\n').encode())

worker = source_worker.read_text(encoding='utf-8')
replacements = [
    (" try:\n  model=protocol['models'][protocol['identity_model']]", " probe_module=sys.modules['__main__'];state['startup_probe']={'worker_entered_monotonic_ns':time.monotonic_ns(),'module_begin_monotonic_ns':probe_module.BOOTSTRAP_MODULE_BEGIN_NS,'module_end_monotonic_ns':probe_module.BOOTSTRAP_MODULE_END_NS,'pynq_imported':'pynq'in sys.modules,'cv2_imported':'cv2'in sys.modules,'frame_pipeline_imported':'frame_pipeline'in sys.modules};state['startup_probe']['before_encoder_init_monotonic_ns']=time.monotonic_ns()\n try:\n  model=protocol['models'][protocol['identity_model']]"),
    ("  gallery_path=Path(model['gallery_features_file']);assert gallery_path.is_file()", "  state['startup_probe']['after_encoder_init_monotonic_ns']=time.monotonic_ns()\n  gallery_path=Path(model['gallery_features_file']);assert gallery_path.is_file()"),
    ("  t=time.monotonic_ns();encoder.run(x);state['warmups'].append({'ms':(time.monotonic_ns()-t)/1e6})", "  state['startup_probe']['gallery_and_input_ready_monotonic_ns']=time.monotonic_ns()\n  t=time.monotonic_ns();warm_raw=encoder.run(x);warm_end=time.monotonic_ns();state['warmups'].append({'ms':(warm_end-t)/1e6,'input_tensor_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'raw_sha256':hashlib.sha256(warm_raw.tobytes()).hexdigest()});state['startup_probe']['warm_started_monotonic_ns']=t;state['startup_probe']['warm_finished_monotonic_ns']=warm_end\n  assert state['warmups'][0]['input_tensor_sha256']==protocol['warmup_input_tensor_sha256'] and state['warmups'][0]['raw_sha256']==protocol['warmup_prior_actual_ARM_raw_sha256']"),
    ("  ready.put({'status':'READY','PID':os.getpid()})", "  state['startup_probe']['before_READY_put_monotonic_ns']=time.monotonic_ns()\n  ready.put({'status':'READY','PID':os.getpid(),'before_READY_put_monotonic_ns':state['startup_probe']['before_READY_put_monotonic_ns']})\n  state['startup_probe']['after_READY_put_return_monotonic_ns']=time.monotonic_ns()"),
    ("  assert 'torch' not in sys.modules", "  assert 'torch' not in sys.modules\n  np.savez_compressed(out/'warmup_actual.npz',input=x,raw=warm_raw)"),
]
for old, new in replacements:
    assert worker.count(old) == 1, old
    worker = worker.replace(old, new)
(stage / 'background_fixed_worker.py').write_bytes(worker.encode())
for name in ['fixed_arrivals.py', 'jpeg_producer.py', 'process_cpu.py']:
    (stage / name).write_bytes((original_root / 'payload_v2' / name).read_bytes())
for name in ['startup_support.py', 'board_controller.py']:
    (stage / name).write_bytes((ROOT / 'tools' / name).read_bytes())
for path in stage.glob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
warm_source = PROJECT / 'pynq_identity_ncnn_20261029/delivery/results/export_v2/vectors/old_gallery_000.npz'
warm_reference = PROJECT / 'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/old_gallery_000.npz'
assert sha(warm_source) == metadata['old_gallery_000.npz']['sha256']
with np.load(warm_source) as old, np.load(warm_reference) as actual:
    assert old['input'].tobytes() == actual['runtime_body_tensor'].tobytes()
    input_sha = hashlib.sha256(old['input'].tobytes()).hexdigest()
    raw_sha = hashlib.sha256(actual['raw'].tobytes()).hexdigest()
runtime = list(original['runtime_files'])
for row in preflight['files']:
    if not any(item['file'] == row['file'] for item in runtime):
        runtime.append({'file': row['file'], 'sha256': row['sha256']})
history = PROJECT / 'pynq_mosaic192_eval_20261030/board_delivery/results/original'
plan = {key: original[key] for key in ['video', 'tracker_config', 'counter_kwargs', 'registered_IDs',
                                     'fixed_identity_threshold', 'secondary_Cows_threshold', 'models',
                                     'backend_nice_increment', 'O8_bit_sha256', 'O8_hwh_sha256']}
plan.update({'status': 'FROZEN_BEFORE_FIRST_STARTUP_DIAGNOSTIC_WARMUP', 'created_UTC': datetime.now(timezone.utc).isoformat(),
             'expected_boot_id': preflight['boot_id'], 'runtime_files': runtime,
             'source_driver_sha256': sha(source_driver), 'source_worker_sha256': sha(source_worker),
             'parent_entry_variants_differ_only_by_six_foreground_import_statements': removed,
             'original_unused_function_bodies_omitted_from_both_probe_entries': True,
             'input_manifest_sha256': metadata['board_input_manifest.json']['sha256'],
             'history_predictions_sha256': sha(history / 'raw_predictions.json.gz'),
             'history_trace_sha256': sha(history / 'stride5_counter_trace.json.gz'),
             'warmup_file_sha256': sha(warm_source), 'warmup_input_tensor_sha256': input_sha,
             'warmup_prior_actual_ARM_raw_sha256': raw_sha,
             'READY_queue_wait_timeout_s': 40, 'after_deadline_same_child_observation_timeout_s': 120,
             'stationary_foreground_workset_not_periodic_replay': True,
             'expected_identity_warmups': 4, 'maximum_all_new_board_image_forwards': 4,
             'formal_identity_jobs': 0, 'O8_image_forwards': 0, 'PL_programming_permitted': False,
             'new_closed_pixels_or_training_updates': 0, 'whole_goal_complete': False,
             'measurement_scope': 'Known identity warmup with paused native graph, ready framebank and cached prehistory resident; not same accumulated five-period state, full load or field startup.',
             'measurement_overheads': 'Identical phase clocks/hash checks and post-READY PSS sampling; warmup vectors saved only after parent requests stop. Warm-end to READY interval retains hash/affinity overhead.',
             'runs': [{'run': f'r{i}_{variant}', 'variant': variant, 'entry_file': entry} for i, (variant, entry) in enumerate([
                 ('original', 'original_entry.py'), ('parent_only', 'parent_only_entry.py'),
                 ('parent_only', 'parent_only_entry.py'), ('original', 'original_entry.py')], 1)]})
plan['payload_files'] = [{'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)} for path in sorted(stage.glob('*.py'))]
protocol_folder = ROOT / 'protocol'
protocol_folder.mkdir(exist_ok=False)
data = (json.dumps(plan, indent=2) + '\n').encode()
(protocol_folder / 'run_v1.json').write_bytes(data)
(stage / 'run_protocol.json').write_bytes(data)
archive = ROOT / 'startup_input_v1.tar.gz'
assert not archive.exists()
with tarfile.open(archive, 'w:gz') as tar:
    for path in sorted(stage.iterdir()):
        tar.add(path, arcname=path.name, recursive=False)
review = {'status': 'IMPORT_ONLY_VARIANT_DIFF_AST_ALL8PY_BUDGET4_AND_PRIOR_ARM_WARMUP_REFERENCE_REVIEWED_BEFORE_EXECUTION',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': sha(protocol_folder / 'run_v1.json'),
          'archive': str(archive), 'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive),
          'members': len(list(stage.iterdir())), 'new_model_forwards': 0, 'max_planned_board_image_forwards': 4,
          'variants_only_remove_six_imports': True, 'no_new_periodic_performance_or_root_cause_claim': True}
with (ROOT / 'evidence/input_bundle_review_v1.json').open('x', encoding='utf-8') as stream:
    json.dump(review, stream, indent=2)
    stream.write('\n')
print(json.dumps(review))
