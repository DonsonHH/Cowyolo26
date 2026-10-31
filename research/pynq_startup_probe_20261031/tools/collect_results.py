"""[DEBUG-startup-20261031] Collect only after the controller and children exit."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl, hashlib, json, os, subprocess, tarfile
from pynq import PL, Overlay

ROOT = Path('/home/xilinx/jupyter_notebooks/cow_research_startup_probe_20261031')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
load = lambda path: json.loads(path.read_text())
plan = load(ROOT / 'run_protocol.json')
launch = load(ROOT / 'launch.json')
state = load(ROOT / 'results/record.json')
terminal = load(ROOT / 'results/terminal.json')
assert terminal['record_sha256'] == sha(ROOT / 'results/record.json')
assert terminal['status'] == state['status']
assert not (Path('/proc') / str(launch['PID'])).exists()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == plan['expected_boot_id'] == launch['boot_id']
processes = []
warmups = formal = 0
for spec in plan['runs']:
    folder = ROOT / 'results' / spec['run']
    if not folder.exists():
        continue
    end = load(folder / 'terminal.json')
    record = load(folder / 'record.json')
    assert end['record_sha256'] == sha(folder / 'record.json')
    assert not (Path('/proc') / str(end['PID'])).exists()
    worker_file = folder / 'background/record.json'
    if worker_file.exists():
        worker = load(worker_file)
        worker_end = load(folder / 'background/terminal.json')
        assert worker_end['record_sha256'] == sha(worker_file)
        assert not (Path('/proc') / str(worker['PID'])).exists()
        warmups += len(worker['warmups'])
        formal += worker['model_forwards']
        processes.append({'run': spec['run'], 'parent_PID': end['PID'], 'worker_PID': worker['PID'],
                          'parent_absent': True, 'worker_absent': True, 'warmups': len(worker['warmups']),
                          'formal_jobs': worker['model_forwards']})
assert formal == 0 and warmups <= 4
if state['status'] == 'ALL4_ORIGINAL_LEAN_LEAN_ORIGINAL_STARTUP_MEASUREMENTS_COMPLETE':
    assert warmups == 4 and len(processes) == 4
runtime = [{'file': row['file'], 'expected_sha256': row['sha256'], 'actual_sha256': sha(Path(row['file']))} for row in plan['runtime_files']]
assert all(row['expected_sha256'] == row['actual_sha256'] for row in runtime)
with Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('rb') as stream:
    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(stream, fcntl.LOCK_UN)
assert PL.bitfile_name and sha(Path(PL.bitfile_name)) == plan['O8_bit_sha256']
overlay = Overlay(PL.bitfile_name, download=False)
hardware = {'core_version': hex(overlay.conv_accel_0.read(4)), 'core_error': hex(overlay.conv_accel_0.read(0x64)),
            'DMA_MM2S': hex(overlay.axi_dma_0.read(4)), 'DMA_S2MM': hex(overlay.axi_dma_0.read(0x34))}
kernel = subprocess.run(['dmesg'], capture_output=True, text=True)
memory_messages = [line for line in kernel.stdout.splitlines() if any(word in line.lower() for word in ['out of memory', 'oom-kill', 'killed process', 'allocation failure'])]
final = {'status': 'STARTUP_TASK_TERMINAL_COLLECTED_WITH_CURRENT_RUNTIME_AND_DEVICE_STATE',
         'created_UTC': datetime.now(timezone.utc).isoformat(), 'boot_id': plan['expected_boot_id'],
         'controller_PID': launch['PID'], 'controller_absent': True, 'processes': processes,
         'actual_identity_warmups': warmups, 'formal_identity_jobs': formal, 'O8_image_forwards': 0,
         'runtime_files': runtime, 'all_runtime_hashes_match': True, 'shared_lock_available': True,
         'PL_SHA256': sha(Path(PL.bitfile_name)), 'hardware': hardware, 'kernel_log_returncode': kernel.returncode,
         'kernel_memory_messages': memory_messages, 'services': {name: subprocess.run(['systemctl', 'is-active', name], capture_output=True, text=True).stdout.strip() for name in ['ssh', 'jupyter']},
         'collection_model_forwards': 0, 'collection_PL_programming': False, 'whole_goal_complete': False}
def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
save(ROOT / 'final_state.json', final)
paths = sorted([path for path in (ROOT / 'results').rglob('*') if path.is_file()] +
               [ROOT / 'run_protocol.json', ROOT / 'launch.json', ROOT / 'controller.log', ROOT / 'final_state.json'] +
               [ROOT / row['file'] for row in plan['payload_files']] + [Path(__file__)])
assert len(paths) == len(set(paths))
manifest = ROOT / 'result_manifest.json'
save(manifest, [{'file': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)} for path in paths])
archive = ROOT / 'startup_delivery_v1.tar.xz'
assert not archive.exists()
with tarfile.open(archive, 'w:xz', preset=3) as tar:
    for path in paths + [manifest]:
        tar.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
for row in load(manifest):
    assert sha(ROOT / row['file']) == row['sha256']
os.sync()
transfer = {'status': 'STARTUP_RESULTS_ARCHIVE_CLOSED_AND_HASHED', 'archive': str(archive), 'bytes': archive.stat().st_size,
            'sha256': sha(archive), 'members': len(paths) + 1, 'manifest_files': len(paths),
            'actual_identity_warmups': warmups, 'new_forwards_by_collection': 0}
save(ROOT / 'transfer.json', transfer)
print(json.dumps(transfer), flush=True)
