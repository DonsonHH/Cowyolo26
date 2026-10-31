"""[DEBUG-startup-20261031] Isolated diagnostic support, not product code."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl, gzip, hashlib, json, multiprocessing, os, queue, sys, time, traceback
import numpy as np

ROOT = Path(__file__).resolve().parent
BASE = Path('/home/xilinx/jupyter_notebooks')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
load = lambda path: json.loads(Path(path).read_text())


def save(path, value):
    part = path.with_suffix(path.suffix + '.partial')
    with part.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    part.replace(path)


def process_memory(pid):
    proc = Path('/proc') / str(pid)
    return {'PID': pid, 'sample_started_monotonic_ns': time.monotonic_ns(),
            'status': (proc / 'status').read_text(), 'smaps_rollup': (proc / 'smaps_rollup').read_text(),
            'stat': (proc / 'stat').read_text(), 'sample_finished_monotonic_ns': time.monotonic_ns()}


def prepare_foreground(protocol):
    """Same imports and stationary working set in both parent variants."""
    import cv2
    from pynq import PL
    from native_graph import NativeGraph
    from device_initialize import initialize
    from frame_pipeline import FramePipeline
    cv2.setNumThreads(1)
    assert PL.bitfile_name and sha(PL.bitfile_name) == protocol['O8_bit_sha256']
    video = BASE / 'cow_research_mosaic192_video_20261030'
    model = BASE / 'cow_research_o8_mosaic192_qual_20261030'
    assert sha(video / 'board_input_manifest.json') == protocol['input_manifest_sha256']
    inputs = load(video / 'board_input_manifest.json')
    selected = [row for row in inputs if row['scene'] == 'original' and 8912 <= row['frame0'] <= 10873]
    assert len(selected) == 392
    framebank = np.empty((392, 192, 192, 3), np.uint8)
    for index, row in enumerate(selected):
        assert sha(video / row['file']) == row['sha256']
        image = cv2.imread(str(video / row['file']))
        assert image.shape == (192, 192, 3)
        framebank[index] = image
    history_path = video / 'results/original/raw_predictions.json.gz'
    trace_path = video / 'results/original/stride5_counter_trace.json.gz'
    assert sha(history_path) == protocol['history_predictions_sha256']
    assert sha(trace_path) == protocol['history_trace_sha256']
    history = json.loads(gzip.decompress(history_path.read_bytes()))
    old_trace = json.loads(gzip.decompress(trace_path.read_bytes()))
    pipeline = FramePipeline(protocol['video'], protocol['tracker_config'], protocol['counter_kwargs'])
    observed = {key: [] for key in ['observations', 'post_tracker', 'confirmed_only_events', 'handoff_events']}
    before = [row for row in history if row['frame0'] < 8915]
    assert len(before) == 1783
    for row in before:
        result = pipeline.update(row['frame0'], row['predictions'])
        observed['observations'].append(result['observation'])
        for key in observed:
            if key != 'observations':
                observed[key].extend(result[key])
    observed = json.loads(json.dumps(observed))
    for key in observed:
        assert observed[key] == [row for row in old_trace[key] if row['frame0'] < 8915]
    initialization = initialize(BASE / 'yolo26_optimization_8')
    graph = NativeGraph(192, program=str(model / 'program'), plan=str(model / 'resident_plan/resident_plan.bin'),
                        options=4, firmware_manifest='hardware/accepted/firmware_manifest.json')
    raw_mmap = np.load(video / 'results/original/all_raw.npy', mmap_mode='r')
    return {'graph': graph, 'framebank': framebank, 'history': history, 'old_trace': old_trace,
            'pipeline': pipeline, 'observed': observed, 'old_raw_mmap': raw_mmap,
            'summary': {'framebank_bytes': framebank.nbytes,
                        'framebank_sha256': hashlib.sha256(memoryview(framebank)).hexdigest(),
                        'prehistory_ticks': 1783, 'prehistory_four_traces_exact': True,
                        'graph_memory': graph.memory(), 'graph_status_before_child': graph.status(),
                        'initialization': initialization, 'new_O8_image_forwards': 0}}


def run_parent(entry_file):
    from background_fixed_worker import worker
    assert len(sys.argv) == 2
    protocol = load(ROOT / 'run_protocol.json')
    spec = next(row for row in protocol['runs'] if row['run'] == sys.argv[1])
    assert spec['entry_file'] == entry_file
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == protocol['expected_boot_id']
    os.sched_setaffinity(0, {0, 1})
    out = ROOT / 'results' / spec['run']
    out.mkdir(exist_ok=False)
    state = {'status': 'RUNNING', 'run': spec['run'], 'variant': spec['variant'], 'PID': os.getpid(),
             'boot_id': protocol['expected_boot_id'], 'protocol_sha256': sha(ROOT / 'run_protocol.json'),
             'new_O8_image_forwards': 0, 'formal_identity_jobs': 0, 'whole_goal_complete': False}
    foreground = child = lock = None
    error = None
    try:
        lock = (BASE / 'yolo26_stage_d/reports/accelerator_job.lock').open('a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        foreground = prepare_foreground(protocol)
        state['stationary_foreground'] = foreground['summary']
        state['parent_before_child'] = process_memory(os.getpid())
        context = multiprocessing.get_context('spawn')
        requests, ready = context.Queue(maxsize=16), context.Queue(maxsize=2)
        child_protocol = {**protocol, 'startup_probe': True, 'worker_idle_gated': False, 'identity_model': 'old',
                          'background_affinity': [0, 1], 'CPU_assignment_policy': 'shared'}
        child = context.Process(target=worker, args=(requests, ready, str(out / 'background'),
                                                     str(BASE / 'cow_research_periodic_joint_20261030'), child_protocol))
        save(out / 'progress.json', {**state, 'status': 'WORKSET_PREPARED_BEFORE_CHILD_START'})
        state['before_child_start_monotonic_ns'] = time.monotonic_ns()
        child.start()
        state['after_child_start_return_monotonic_ns'] = time.monotonic_ns()
        state['child_PID'] = child.pid
        state['before_READY_wait_monotonic_ns'] = time.monotonic_ns()
        try:
            response = ready.get(timeout=40)
            state['ready_wait_40s_expired'] = False
        except queue.Empty:
            state['ready_wait_40s_expired'] = True
            state['deadline_observed_monotonic_ns'] = time.monotonic_ns()
            state['same_child_at_deadline'] = process_memory(child.pid) if child.is_alive() else {'PID': child.pid, 'alive': False}
            save(out / 'progress.json', {**state, 'status': '40S_EXPIRED_OBSERVING_SAME_CHILD_NOT_RESTARTED'})
            response = ready.get(timeout=120)
        state['ready_received_monotonic_ns'] = time.monotonic_ns()
        state['ready_response'] = response
        assert response['status'] == 'READY' and response['PID'] == child.pid, response
        state['child_at_READY'] = process_memory(child.pid)
        state['parent_at_READY'] = process_memory(os.getpid())
        state['meminfo_at_READY'] = Path('/proc/meminfo').read_text()
        state['stop_requested_monotonic_ns'] = time.monotonic_ns()
        requests.put(None)
        child.join(timeout=45)
        assert not child.is_alive(), 'Keep same worker PID; no repeat experiment'
        state['child_exitcode'] = child.exitcode
        worker_state = load(out / 'background/record.json')
        worker_end = load(out / 'background/terminal.json')
        assert worker_state['status'] == worker_end['status'] == 'ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'
        assert worker_end['record_sha256'] == sha(out / 'background/record.json')
        assert worker_state['model_forwards'] == 0 and len(worker_state['warmups']) == 1 and child.exitcode == 0
        state['identity_warmup_forwards'] = 1
        state['child_absent_after_join'] = not (Path('/proc') / str(child.pid)).exists()
        assert state['child_absent_after_join']
        child = None
        state['status'] = 'STARTUP_MEASUREMENT_COMPLETE_WITH_40S_DEADLINE_RESULT_RECORDED'
    except BaseException as exception:
        error = exception
        state.update({'status': 'FAILED', 'error': repr(exception), 'traceback': traceback.format_exc()})
    finally:
        if child is not None:
            try:
                requests.put_nowait(None)
            except Exception:
                pass
            # Keep this exact process handle. Do not reinterpret an observer
            # timeout as a terminal child or start a replacement worker.
            child.join(timeout=10)
            state['pending_same_child'] = {'PID': child.pid, 'alive': child.is_alive(), 'exitcode': child.exitcode}
        if foreground is not None:
            try:
                state['graph_status_before_close'] = foreground['graph'].status()
                foreground['graph'].close()
                state['close_error'] = None
            except BaseException as close_exception:
                error = close_exception
                state.update({'status': 'DEVICE_CLOSE_FAILED_NOT_SAFE_TO_RETRY', 'close_error': repr(close_exception)})
        if lock:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
        state['parent_after_child'] = process_memory(os.getpid())
        save(out / 'record.json', state)
        save(out / 'terminal.json', {'status': state['status'], 'PID': os.getpid(), 'record_sha256': sha(out / 'record.json'),
                                     'new_O8_image_forwards': 0, 'whole_goal_complete': False})
        print(json.dumps({'run': spec['run'], 'status': state['status'], 'child_PID': state.get('child_PID'),
                          'ready_wait_40s_expired': state.get('ready_wait_40s_expired')}), flush=True)
    if error:
        raise SystemExit(1)
