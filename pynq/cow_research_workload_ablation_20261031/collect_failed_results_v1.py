"""Preserve the original FAILED task, including its sixth preparation-only run."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl, hashlib, json, os, subprocess, tarfile
from pynq import PL

ROOT = Path('/home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
load = lambda path: json.loads(path.read_text())
assert sha(ROOT / 'run_protocol.json') == '9329f1fc27a2059ffbddd459b289b69061d9f05f4f51e1e1ca840e5528456cb8'
plan = load(ROOT / 'run_protocol.json')
state = load(ROOT / 'results/record.json')
terminal = load(ROOT / 'results/terminal.json')
launch = load(ROOT / 'launch.json')
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == launch['boot_id'] == state['boot_id'] == plan['expected_boot_id']
assert state['status'] == terminal['status'] == 'FAILED'
assert terminal['record_sha256'] == sha(ROOT / 'results/record.json')
assert terminal['close_error'] is state['close_error'] is None
assert state['error'] == 'Empty()' and 'ready.get(timeout=40)' in state['traceback']
assert len(state['cases']) == 5 and state['actual_O8_forwards'] == 1748
assert not (Path('/proc') / str(launch['PID'])).exists()
children = []
for spec in plan['runs'][:6]:
    folder = ROOT / 'results' / spec['run'] / 'background'
    record = load(folder / 'record.json')
    end = load(folder / 'terminal.json')
    assert end['record_sha256'] == sha(folder / 'record.json')
    assert record['status'] == end['status'] == 'ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'
    assert not (Path('/proc') / str(end['PID'])).exists()
    children.append({'run': spec['run'], 'PID': end['PID'], 'proc_exists': False,
                     'formal_jobs': record['model_forwards'], 'warmups': len(record['warmups'])})
assert sum(row['formal_jobs'] for row in children) == 30
assert sum(row['warmups'] for row in children) == 6
runtime = [{'file': row['file'], 'expected_sha256': row['sha256'], 'actual_sha256': sha(Path(row['file']))} for row in plan['runtime_files']]
assert all(row['expected_sha256'] == row['actual_sha256'] for row in runtime)
with Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('rb') as stream:
    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(stream, fcntl.LOCK_UN)
assert PL.bitfile_name and sha(Path(PL.bitfile_name)) == plan['O8_bit_sha256'] == state['PL_after_sha256']
diagnostics = ROOT / 'failure_diagnostics'
diagnostics.mkdir(exist_ok=False)
kernel = subprocess.run(['dmesg'], capture_output=True, text=True)
(diagnostics / 'dmesg.txt').write_text(kernel.stdout)
(diagnostics / 'dmesg_stderr.txt').write_text(kernel.stderr)
matches = [line for line in kernel.stdout.splitlines() if any(word in line.lower() for word in ['out of memory', 'oom-kill', 'killed process', 'allocation failure'])]
services = {name: subprocess.run(['systemctl', 'is-active', name], capture_output=True, text=True).stdout.strip() for name in ['ssh', 'jupyter']}
def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
final = {'status': 'ORIGINAL_FAILED_TASK_FIVE_TIMED_CASES_AND_SIXTH_WARMUP_PRESERVED_ALL_PROCESSES_TERMINAL',
         'created_board_UTC': datetime.now(timezone.utc).isoformat(), 'boot_id': boot,
         'parent_PID': launch['PID'], 'parent_absent': True, 'children': children,
         'runtime_files': runtime, 'all_runtime_hashes_match': True, 'shared_lock_available': True,
         'PL_bitfile_name': PL.bitfile_name, 'PL_SHA256': sha(Path(PL.bitfile_name)),
         'services': services, 'kernel_log_returncode': kernel.returncode, 'kernel_memory_matches': matches,
         'meminfo': Path('/proc/meminfo').read_text(), 'vmstat': Path('/proc/vmstat').read_text(),
         'collector_PID': os.getpid(), 'collection_programmed_PL_or_ran_models': False,
         'new_model_forwards': 0, 'whole_goal_complete': False}
save(ROOT / 'failed_final_state_v1.json', final)
paths = sorted([path for directory in ['results', 'failure_diagnostics'] for path in (ROOT / directory).rglob('*') if path.is_file()] +
               [ROOT / 'run_protocol.json', ROOT / 'launch.json', ROOT / 'run.log', ROOT / 'failed_final_state_v1.json'] +
               [ROOT / row['file'] for row in plan['payload_files']] + [Path(__file__)])
assert len(paths) == len(set(paths))
manifest = ROOT / 'result_manifest.json'
save(manifest, [{'file': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)} for path in paths])
archive = ROOT / 'failure_delivery_v1.tar.xz'
assert not archive.exists()
with tarfile.open(archive, 'w:xz', preset=3) as tar:
    for path in paths + [manifest]:
        tar.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
for row in load(manifest):
    assert sha(ROOT / row['file']) == row['sha256']
os.sync()
transfer = {'status': 'FAILED_TASK_ARCHIVE_FINISHED_NO_REPLAY_OR_MODEL_FORWARD',
            'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha(archive),
            'members': len(paths) + 1, 'manifest_files': len(paths), 'new_model_forwards': 0}
save(ROOT / 'failure_transfer_v1.json', transfer)
print(json.dumps(transfer), flush=True)
