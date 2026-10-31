"""Independently recompute saved 2x2 timing, events, input and identity outputs.

No neural inference, threshold fitting or new data selection occurs here.
Full tracker association is a separate replay; this checks recorded positions
and both event state machines before that replay is available.
"""
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import gzip, hashlib, importlib.util, json, math, sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
BOARD = ROOT / 'delivery'
load = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
gz = lambda path: json.loads(gzip.decompress(Path(path).read_bytes()))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def proc_kb(status, key):
    for line in status.splitlines():
        if line.startswith(key + ':'):
            return int(line.split()[1])
    raise AssertionError(key)


scanner = module('workload_event_scanner', PROJECT / 'long_video_fixed_replay_20261029/tools/verify_delivery.py')
body = module('workload_body_reference', PROJECT / 'identity_domain_ncnn_20261030/tools/frozen_body_tensor.py')
plan = load(BOARD / 'run_protocol.json')
assert sha(BOARD / 'run_protocol.json') == sha(ROOT / 'protocol/run_v2.json')
assert sha(BOARD / 'run_protocol.json') == '9329f1fc27a2059ffbddd459b289b69061d9f05f4f51e1e1ca840e5528456cb8'
assert ''.join(row['condition'] for row in plan['runs']) == 'ABCDDCBA'
state = load(BOARD / 'results/record.json')
terminal = load(BOARD / 'results/terminal.json')
final = load(BOARD / 'final_state.json')
assert state['status'] == terminal['status'] == 'ALL8_WORKLOAD_2X2_MIRROR_ORDER_REPEATS_COMPLETE'
assert terminal['record_sha256'] == sha(BOARD / 'results/record.json')
assert terminal['close_error'] is state['close_error'] is None
assert state['boot_id'] == final['boot_id'] == plan['expected_boot_id']
assert state['qualification_forwards'] == 8 and state['warmup_forwards'] == 16
assert len(state['qualification_gate']) == 8 and all(row['raw_byte_exact'] for row in state['qualification_gate'])
assert state['hardware_status']['error'] == '0x0'
assert final['parent_absent'] and final['all_runtime_hashes_match'] and final['shared_lock_available']
assert all(not row['proc_exists'] for row in final['children'])
assert final['PL_SHA256'] == state['PL_after_sha256'] == plan['O8_bit_sha256']
assert state['parent_affinity_restored_before_exit'] == [0, 1]
assert not final['collection_programmed_PL_or_ran_models'] and final['new_model_forwards'] == 0
for row in plan['payload_files']:
    assert sha(BOARD / row['file']) == sha(ROOT / 'payload_v2' / row['file']) == row['sha256']
for actual, frozen in zip(final['runtime_files'], plan['runtime_files']):
    assert actual['file'] == frozen['file'] and actual['actual_sha256'] == actual['expected_sha256'] == frozen['sha256']
assert len(final['runtime_files']) == len(plan['runtime_files'])

source = PROJECT / 'pynq_mosaic192_eval_20261030/board_delivery/results/original'
old_raw = np.load(source / 'all_raw.npy', mmap_mode='r')
old_trace = gz(source / 'stride5_counter_trace.json.gz')
camera_root = PROJECT / 'pynq_periodic_joint_20261030/camera_delivery'
assert sha(camera_root / 'manifest.json') == plan['camera_manifest_SHA256']
camera = {row['frame0']: row for row in load(camera_root / 'manifest.json')}
max_jpeg = max(row['bytes'] for row in camera.values())
prior_root = PROJECT / 'backend_service_20261030/delivery/results/r1_idle_gate/background'
prior_jobs = load(prior_root / 'record.json')['jobs']
with np.load(PROJECT / 'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz') as archive:
    gallery = archive['new_gallery'].astype(float)
gallery_rows = plan['identity_reference_images'][:30]
labels = plan['registered_IDs']
cases, actual_jobs = [], []
total_raw = total_ticks = total_paths = total_produced = total_received = total_overlap = 0
assert len(state['cases']) == 8
for spec, case in zip(plan['runs'], state['cases']):
    assert all(case[key] == value for key, value in spec.items())
    run = spec['run']
    folder = BOARD / 'results' / run
    rows = load(folder / 'timing_rows.json')
    skips = load(folder / 'skipped_slots.json')
    trace = gz(folder / 'counter_trace.json.gz')
    epoch = case['clock_start_monotonic_ns']
    assert case['period_end_monotonic_ns'] == epoch + 392 * 200000000
    assert sorted([row['slot'] for row in rows] + [row['slot'] for row in skips]) == list(range(392))
    assert len(rows) == case['processed_frames'] and len(skips) == case['skipped_slots']
    assert [row['slot'] for row in rows] == sorted(row['slot'] for row in rows)
    for row in rows:
        assert row['frame0'] == 8915 + 5 * row['slot']
        assert row['release_monotonic_ns'] == epoch + row['slot'] * 200000000
        assert row['release_monotonic_ns'] <= row['started_monotonic_ns'] <= row['completed_monotonic_ns']
        assert row['release_to_count_ms'] == (row['completed_monotonic_ns'] - row['release_monotonic_ns']) / 1e6
        assert row['processing_ms'] == (row['completed_monotonic_ns'] - row['started_monotonic_ns']) / 1e6
        assert 0 <= row['model_ms'] <= row['processing_ms']
        assert row['deadline_met'] == (row['completed_monotonic_ns'] <= row['release_monotonic_ns'] + 200000000)
        before, after = row['worker_CPU_before'], row['worker_CPU_after']
        assert before['PID'] == after['PID'] and before['starttime_ticks'] == after['starttime_ticks']
        assert before['nice'] == after['nice'] == 10
        assert before['clock_ticks_per_second'] == after['clock_ticks_per_second'] == 100
        assert before['snapshot_finished_monotonic_ns'] <= row['started_monotonic_ns']
        assert after['snapshot_finished_monotonic_ns'] <= row['completed_monotonic_ns']
        assert row['worker_CPU_tick_delta'] == after['total_CPU_ticks'] - before['total_CPU_ticks'] >= 0
    for row in skips:
        assert row['source_frame0'] == 8915 + 5 * row['slot']
        assert row['release_monotonic_ns'] == epoch + row['slot'] * 200000000
        assert row['skip_observed_monotonic_ns'] >= row['release_monotonic_ns'] + 200000000
    assert sum(not row['deadline_met'] for row in rows) == case['deadline_misses']
    assert len(rows) / 78.4 == case['processed_per_second_over_offered_duration']
    assert float(np.mean([row['processing_ms'] for row in rows])) == case['mean_processing_ms']
    assert float(np.quantile([row['release_to_count_ms'] for row in rows], .95)) == case['P95_release_to_count_ms']
    with np.load(folder / 'actual_raw.npz') as archive:
        assert archive['frame0'].tolist() == [row['frame0'] for row in rows]
        for frame, raw in zip(archive['frame0'], archive['raw']):
            assert raw.tobytes() == old_raw[int(frame) // 5].tobytes()
            total_raw += 1
    assert [row['frame0'] for row in trace['observations']] == list(range(0, 8915, 5)) + [row['frame0'] for row in rows]
    assert load(folder / 'prewarm_history_gate.json') == {'cached_ticks': 1783, 'all_four_traces_exact': True, 'new_model_forwards': 0}
    for key in trace:
        assert [row for row in trace[key] if row['frame0'] < 8915] == [row for row in old_trace[key] if row['frame0'] < 8915]
    post = defaultdict(list)
    for row in trace['post_tracker']:
        post[row['frame0']].append(row)
    for observation in trace['observations']:
        positions, ids = {}, set()
        for row in post[observation['frame0']]:
            tid = row['track_id']
            if tid is None:
                continue
            ids.add(tid)
            x1, y1, x2, y2 = row['xyxy']
            if .34 < (x1 + x2) / (2 * 2560) < .75:
                positions[str(tid)] = (y1 + y2) / (2 * 1440)
        assert observation['confirmed_positions'] == positions and observation['confirmed_IDs'] == sorted(ids)
    total_ticks += len(trace['observations'])
    for key, handoff in [('confirmed_only_events', False), ('handoff_events', True)]:
        events, _ = scanner.batch_events(trace['observations'], handoff)
        assert events == trace[key]
        total_paths += 1
        if handoff:
            scoped = [event for event in events if 8912 <= event['frame0'] <= 10873]
            assert scoped == case['periodic_events']
            assert sum(event['direction'] == 'A->B' for event in scoped) == case['source_down_count']
            assert sum(event['direction'] == 'B->A' for event in scoped) == case['source_up_count']

    producer = load(folder / 'producer_record.json')
    packets = load(folder / 'input_packets.json')
    io_overlaps = 0
    if spec['input_producer']:
        assert producer['status'] == 'JPEG_PRODUCER_COMPLETE' and not producer['thread_alive']
        assert producer['error'] is None and producer['pinned_at_end'] is None and producer['producer_affinity'] == [0, 1]
        assert len(producer['records']) == case['actual_producer_frames'] == 392
        assert len(packets) == len(rows) and producer['peak_retained_frames'] <= 7
        assert producer['peak_retained_payload_bytes'] <= 7 * max_jpeg
        assert producer['peak_transient_payload_bytes'] <= 8 * max_jpeg
        byframe = {}
        for slot, record in enumerate(producer['records']):
            frame = 8915 + 5 * slot
            assert record['frame0'] == frame and record['slot'] == slot
            assert record['release_monotonic_ns'] == epoch + slot * 200000000
            assert record['release_monotonic_ns'] <= record['read_started_monotonic_ns'] <= record['read_finished_monotonic_ns'] <= record['verified_monotonic_ns'] <= record['published_monotonic_ns']
            assert record['JPEG_bytes'] == camera[frame]['bytes'] and record['JPEG_sha256'] == camera[frame]['sha256']
            assert record['read_ms'] == (record['read_finished_monotonic_ns'] - record['read_started_monotonic_ns']) / 1e6
            assert record['verification_ms'] == (record['verified_monotonic_ns'] - record['read_finished_monotonic_ns']) / 1e6
            assert record['retained_frames_after_publish'] <= 7 and record['retained_payload_bytes_after_publish'] <= 7 * max_jpeg
            byframe[frame] = record
        for row, packet in zip(rows, packets):
            assert packet['frame0'] == row['frame0'] and packet['slot'] == row['slot']
            assert all(packet[key] == value for key, value in byframe[row['frame0']].items())
            assert packet['published_monotonic_ns'] <= packet['foreground_received_monotonic_ns'] <= row['completed_monotonic_ns']
            assert packet['foreground_wait_started_monotonic_ns'] <= packet['foreground_received_monotonic_ns']
            assert row['JPEG_input_wait_ms'] == (packet['foreground_received_monotonic_ns'] - packet['foreground_wait_started_monotonic_ns']) / 1e6
            model_end = row['started_monotonic_ns'] + round(row['model_ms'] * 1e6)
            io_overlaps += min(model_end, packet['read_finished_monotonic_ns']) > max(row['started_monotonic_ns'], packet['read_started_monotonic_ns'])
    else:
        assert producer == {'status': 'INPUT_PRODUCER_DISABLED', 'thread_alive': False, 'records': []}
        assert packets == [] and case['actual_producer_frames'] == 0 and all(row['JPEG_input_wait_ms'] == 0 for row in rows)
    total_produced += len(producer['records'])
    total_received += len(packets)
    total_overlap += io_overlaps

    publications = load(folder / 'fixed_job_publication.json')
    worker = load(folder / 'background/record.json')
    worker_end = load(folder / 'background/terminal.json')
    jobs = worker['jobs']
    count = 10 if spec['identity_workload'] else 0
    assert publications['status'] == 'ALL_FIXED_JOBS_PUBLISHED' and not publications['thread_alive']
    assert len(jobs) == len(publications['records']) == worker['model_forwards'] == case['actual_background_jobs'] == count
    assert worker['status'] == worker_end['status'] == 'ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'
    assert worker_end['record_sha256'] == sha(folder / 'background/record.json') and worker_end['PID'] == worker['PID']
    assert len(worker['warmups']) == case['resident_identity_warmups'] == 1
    assert worker['actual_nice'] == 10 and worker['actual_CPU_affinity'] == [0, 1] and worker['NCNN_threads'] == 1
    assert all(mask == [0, 1] for mask in worker['after_warmup_thread_affinities'].values())
    assert worker['PL_actions'] == 0 and not worker['torch_imported']
    assert worker['identity_model'] == 'old' and worker['encoder_bin_sha256'] == plan['models']['old']['encoder_bin_sha256']
    for index, (pub, job, frozen, prior) in enumerate(zip(publications['records'], jobs, plan['fixed_jobs'], prior_jobs)):
        assert pub['fixed_job_index'] == job['fixed_job_index'] == frozen['fixed_job_index'] == index
        assert pub['requested_monotonic_ns'] == epoch + frozen['requested_enqueue_offset_ns'] == job['release_monotonic_ns'] == job['requested_enqueue_monotonic_ns']
        assert pub['enqueue_started_monotonic_ns'] == job['enqueued_monotonic_ns'] >= pub['requested_monotonic_ns']
        assert pub['enqueue_returned_monotonic_ns'] >= pub['enqueue_started_monotonic_ns'] and pub['publisher_CPU_affinity'] == [0, 1]
        assert pub['publisher_lateness_ms'] == (pub['enqueue_started_monotonic_ns'] - pub['requested_monotonic_ns']) / 1e6
        assert all(mask == [0, 1] for mask in job['thread_affinities_after_job'].values())
        assert job['event'] == frozen['event'] and job['selection'] == frozen['selection']
        assert job['source_frame0'] == frozen['source_frame0'] == prior['source_frame0']
        assert not job['identity_reference_available'] and job['JPEG_source'] == 'same_frame_file_read'
        assert job['queue_wait_ms'] == (job['started_monotonic_ns'] - job['enqueued_monotonic_ns']) / 1e6
        assert job['enqueue_to_result_ms'] == (job['completed_monotonic_ns'] - job['enqueued_monotonic_ns']) / 1e6
        assert job['enqueued_monotonic_ns'] <= job['started_monotonic_ns'] <= job['inference_finished_monotonic_ns'] <= job['completed_monotonic_ns']
        jpeg = camera_root / 'highres' / ('f' + str(job['source_frame0']).zfill(5) + '.jpg')
        assert sha(jpeg) == job['source_JPEG_sha256'] == frozen['source_JPEG_sha256']
        left, top, right, bottom = frozen['box_native_xyxy']
        crop = [max(0, math.floor(left - 870)), max(0, math.floor(top)), min(1050, math.ceil(right - 870)), min(1440, math.ceil(bottom))]
        assert crop == job['native_source_crop_xyxy']
        with Image.open(jpeg) as image:
            photo = image.convert('RGB').crop(crop).transpose(Image.Transpose.ROTATE_270)
        saved = folder / 'background' / job['photo_file']
        assert sha(saved) == job['photo_sha256'] == prior['photo_sha256']
        with Image.open(saved) as image:
            assert image.convert('RGB').tobytes() == photo.tobytes()
        tensor = body.body_tensor(photo)
        vector = folder / 'background' / job['vector_file']
        assert sha(vector) == job['vector_sha256']
        with np.load(vector) as archive, np.load(prior_root / prior['vector_file']) as reference:
            for key in ['input', 'raw', 'normalized', 'scores']:
                assert archive[key].tobytes() == reference[key].tobytes()
            assert tensor.tobytes() == archive['input'].tobytes()
            assert hashlib.sha256(tensor.tobytes()).hexdigest() == job['input_tensor_sha256']
            assert hashlib.sha256(archive['raw'].tobytes()).hexdigest() == job['raw_feature_sha256']
            raw = archive['raw'].astype(float)
            assert np.max(np.abs(raw / np.linalg.norm(raw) - archive['normalized'])) < 1e-7
            dots = archive['normalized'].astype(float) @ gallery.T
            scores = [max(dots[i] for i, row in enumerate(gallery_rows) if row['identity'] == label) for label in labels]
            assert np.max(np.abs(np.array(scores) - archive['scores'])) < 1e-12
            winner = int(np.argmax(scores))
            assert job['predicted_id'] == labels[winner] and abs(job['similarity'] - scores[winner]) < 1e-12
            assert job['accepted'] == (scores[winner] >= plan['fixed_identity_threshold'])
            assert job['secondary_Cows_threshold_accepted'] == (scores[winner] >= plan['secondary_Cows_threshold'])
        assert all(job[key] == value for key, value in frozen['expected_prior_actual'].items())
        actual_jobs.append({'run': run, 'condition': spec['condition'], 'repeat': spec['repeat'],
                            **{key: job[key] for key in ['fixed_job_index', 'source_frame0', 'photo_sha256', 'input_tensor_sha256', 'raw_feature_sha256', 'predicted_id', 'similarity', 'accepted', 'queue_wait_ms', 'enqueue_to_result_ms', 'actual_identity_network_ms']}})
    boundaries = load(folder / 'system_boundaries.json')
    before, after = boundaries['before'], boundaries['after']
    assert before['sample_monotonic_ns'] <= epoch < case['period_end_monotonic_ns'] <= after['sample_monotonic_ns']
    vm_deltas = {key: after['vmstat'][key] - value for key, value in before['vmstat'].items()}
    assert all(value >= 0 for value in vm_deltas.values())
    cases.append({**{key: value for key, value in case.items() if key not in ['periodic_events', 'foreground_proc_status']},
                  'absolute_difference_from_human_total12': abs(case['source_down_count'] - 12),
                  'deadline_miss_fraction_of_processed': case['deadline_misses'] / len(rows),
                  'mean_model_ms': float(np.mean([row['model_ms'] for row in rows])),
                  'mean_JPEG_wait_ms': float(np.mean([row['JPEG_input_wait_ms'] for row in rows])),
                  'maximum_identity_queue_ms': max((job['queue_wait_ms'] for job in jobs), default=None),
                  'maximum_identity_result_ms': max((job['enqueue_to_result_ms'] for job in jobs), default=None),
                  'mean_identity_network_ms': float(np.mean([job['actual_identity_network_ms'] for job in jobs])) if jobs else None,
                  'accepted_predictions_without_identity_GT': sum(job['accepted'] for job in jobs),
                  'foreground_VmHWM_kB_cumulative': proc_kb(case['foreground_proc_status'], 'VmHWM'),
                  'foreground_VmRSS_kB_at_end': proc_kb(case['foreground_proc_status'], 'VmRSS'),
                  'foreground_VmSwap_kB_at_end': proc_kb(case['foreground_proc_status'], 'VmSwap'),
                  'process_major_faults_delta': after['ru_majflt'] - before['ru_majflt'],
                  'system_vmstat_deltas': vm_deltas, 'producer_model_IO_overlap_cases': io_overlaps})
assert total_raw == state['actual_O8_forwards'] == terminal['actual_O8_forwards']
assert len(actual_jobs) == 40 and len({row['photo_sha256'] for row in actual_jobs}) == 10
assert total_produced == 4 * 392 and total_ticks == 8 * 1783 + total_raw and total_paths == 16
actual_total = total_raw + 8 + 16 + 40 + 8
assert actual_total <= plan['maximum_total_board_image_forwards'] == 3208
assert total_raw <= plan['maximum_timed_O8_forwards'] == 3136

# Inherited fields from the four-run source protocol are retained unchanged.
# Their inconsistency is disclosed; the executable runs and new explicit caps
# above define this eight-run experiment. Do not silently edit a frozen plan.
protocol_notes = [
    {'field': 'expected_timed_O8_maximum', 'frozen_value': plan['expected_timed_O8_maximum'],
     'scope': 'Inherited source-four-run field; inconsistent as an eight-run cap. Executed maximum_timed_O8_forwards=3136 is audited.'},
    {'field': 'fixed_jobs_per_case', 'frozen_value': plan['fixed_jobs_per_case'],
     'scope': 'W-on amount only; executable runs explicitly set W-off to zero.'},
    {'field': 'no_every_frame_highres_ring', 'frozen_value': plan['no_every_frame_highres_ring'],
     'scope': 'No event-photo selection ring; B/D do have a bounded JPEG producer bank. Not a claim of zero per-frame JPEG input.'},
]
result = {'status': 'ALL8_SAVED_RAW_TIMING_EVENTS_PRODUCER_FIXED40_IDENTITY_AND_RESOURCE_COUNTERS_VERIFIED_WITH_DISCLOSED_PROTOCOL_METADATA_INCONSISTENCY',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'actual_timed_O8_forwards': total_raw,
          'actual_O8_qualification_forwards': 8, 'actual_O8_warmups': 16,
          'actual_ARM_timed_queries': 40, 'actual_ARM_warmups': 8,
          'all_new_actual_board_forwards': actual_total, 'counter_observation_ticks': total_ticks,
          'independently_recomputed_counter_paths': total_paths, 'producer_source_frames': total_produced,
          'frontend_received_packets': total_received, 'producer_model_IO_overlap_cases': total_overlap,
          'fixed_photo_tensor_raw_feature_score_jobs_verified': 40, 'unique_fixed_photos': 10,
          'new_CPU_model_reference_forwards': 0, 'identical_prior_verified_reference_reused': True,
          'full_tracker_association_replay_complete': False,
          'permanent_event_ID_accuracy_known': False, 'formal_counting_event_accuracy_known': False,
          'protocol_metadata_notes': protocol_notes, 'cases': cases,
          'new_independent_test': False, 'new_training_updates': 0, 'whole_goal_complete': False}
save(ROOT / 'results/independent_verification.json', result)
save(ROOT / 'results/actual_job_rows.json', actual_jobs)
print(json.dumps({key: value for key, value in result.items() if key not in ['cases', 'protocol_metadata_notes']}))
