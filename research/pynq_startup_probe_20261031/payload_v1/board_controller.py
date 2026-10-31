"""[DEBUG-startup-20261031] Launch four new diagnostic parents, once each."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess, sys, time, traceback

ROOT = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
load = lambda path: json.loads(path.read_text())


def save(path, value):
    part = path.with_suffix(path.suffix + '.partial')
    part.write_bytes((json.dumps(value, indent=2) + '\n').encode())
    part.replace(path)


def main():
    protocol = load(ROOT / 'run_protocol.json')
    out = ROOT / 'results'
    out.mkdir(exist_ok=False)
    state = {'status': 'RUNNING', 'PID': os.getpid(), 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
             'protocol_sha256': sha(ROOT / 'run_protocol.json'), 'runs': [], 'new_O8_image_forwards': 0, 'whole_goal_complete': False}
    failure = None
    try:
        assert state['boot_id'] == protocol['expected_boot_id']
        for row in protocol['payload_files']:
            assert sha(ROOT / row['file']) == row['sha256']
        for row in protocol['runtime_files']:
            assert sha(Path(row['file'])) == row['sha256']
        for spec in protocol['runs']:
            started = time.monotonic_ns()
            with (out / (spec['run'] + '.log')).open('xb') as log:
                child = subprocess.Popen([sys.executable, '-u', str(ROOT / spec['entry_file']), spec['run']],
                                          stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                          env={**os.environ, 'XILINX_XRT': '/usr', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
                                               'PYTHONDONTWRITEBYTECODE': '1'})
                save(out / 'progress.json', {'status': 'OBSERVING_SAME_DIAGNOSTIC_PARENT', 'run': spec['run'],
                                            'controller_PID': os.getpid(), 'parent_PID': child.pid,
                                            'parent_started_monotonic_ns': started})
                code = child.wait()
            terminal = load(out / spec['run'] / 'terminal.json')
            assert not (Path('/proc') / str(child.pid)).exists()
            row = {**spec, 'parent_PID': child.pid, 'parent_exitcode': code, 'parent_absent': True,
                   'started_monotonic_ns': started, 'finished_monotonic_ns': time.monotonic_ns(), 'terminal_status': terminal['status']}
            state['runs'].append(row)
            save(out / 'record.json', state)
            assert code == 0 and terminal['status'] == 'STARTUP_MEASUREMENT_COMPLETE_WITH_40S_DEADLINE_RESULT_RECORDED'
        assert len(state['runs']) == 4
        state['identity_warmup_forwards'] = 4
        state['formal_identity_jobs'] = 0
        state['status'] = 'ALL4_ORIGINAL_LEAN_LEAN_ORIGINAL_STARTUP_MEASUREMENTS_COMPLETE'
    except BaseException as exception:
        failure = exception
        state.update({'status': 'FAILED', 'error': repr(exception), 'traceback': traceback.format_exc()})
    finally:
        save(out / 'record.json', state)
        save(out / 'terminal.json', {'status': state['status'], 'PID': os.getpid(), 'record_sha256': sha(out / 'record.json'),
                                     'new_O8_image_forwards': 0, 'whole_goal_complete': False})
        print(json.dumps(state), flush=True)
    if failure:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
