"""Score a completed fixed case against an explicit external service protocol.

This does not mutate runtime summaries or manufacture timed event ground truth.
"""
import argparse
import hashlib
import json
from pathlib import Path


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def candidate_matches(config, protocol, profile_name=None):
    def contains(actual, required):
        return isinstance(actual, dict) and all(k in actual and (contains(actual[k], v) if isinstance(v, dict) else actual[k] == v)
                                                for k, v in required.items())
    if 'profiles' in protocol:
        required=protocol['profiles'].get(profile_name)
        return required is not None and contains(config,required)
    if 'candidate_invariants' in protocol:
        return contains(config, protocol['candidate_invariants'])
    if protocol.get('version') != 'bounded-count-publication-1s-v1':
        return False
    # Fixed legacy v1 was frozen with human-readable model/capture labels.
    required = {k: protocol['candidate'][k] for k in ('preprocess_mode','detector_input','warmup_model_forwards','confidence')}
    normalized = {**config,'tracker':{'motion_box':'kalman',**config.get('tracker',{})}}
    required.update(sample_hz=protocol['candidate']['target_model_hz'],detector={'size':256},
                    capture={'width':1280,'height':720,'fps':5,'fourcc':'MJPG'},
                    counter={'stable_samples':protocol['candidate']['stable_samples'],'lower':.4,'upper':.6,'maximum_gap_s':2},
                    tracker={'motion_box':'kalman',**{k:protocol['candidate'][k] for k in ('track_high_thresh','track_low_thresh','new_track_thresh','fuse_score')}},
                    endpoint_recovery={'enabled':True,'roi_scale':1.5,'maximum_age_s':1.5,'maximum_per_frame':1,
                                       'maximum_extra_forwards':None,'reacquire_missing_tracks':True,'maximum_reacquisitions_per_origin':8})
    return contains(normalized,required)


def assess(summary, events, frames, supervisor, freeze, protocol, protocol_sha256, output_sha256):
    """Keep count-reference agreement, integrity and realtime service separate."""
    config = summary['config']
    event_counts = {kind: sum(row['kind'] == kind for row in events) for kind in ('IN', 'OUT')}
    expected_hashes = freeze['expected_file_sha256']
    input_hashes = [v for p, v in expected_hashes.items() if p.endswith('/input.avi')]
    integrity = {
        'terminal_success': supervisor.get('status') == 'EXITED' and supervisor.get('exit_code') == 0,
        'terminal_bound_to_run': supervisor.get('run_id') == summary['run_id'] and supervisor.get('output_sha256') == output_sha256
            and supervisor.get('launch_identity') == freeze.get('launch_identity') and freeze.get('launch_identity') is not None
            and supervisor.get('output_dir') == freeze.get('expected_output_dir'),
        'runtime_completed': summary.get('status') == 'COMPLETED_UNSCORED',
        'config_matches_freeze': config == freeze['config'],
        'config_matches_protocol_candidate': candidate_matches(config,protocol,freeze.get('service_profile')),
        'service_protocol_matches_freeze': protocol_sha256 == freeze.get('service_protocol_sha256'),
        'source_matches_freeze': input_hashes == [summary.get('video_sha256')],
        'model_matches_freeze': expected_hashes.get(config['detector']['program'] + '/graph.bin') == summary.get('model_sha256'),
        'plan_matches_freeze': expected_hashes.get(config['detector']['plan']) == summary.get('resident_plan_sha256'),
        'runtime_assets_match_freeze': set(summary.get('runtime_asset_sha256',{})) == {
            'native_sources/native_queue.so','hardware/accepted/firmware_manifest.json','hardware/accepted/optimization_8_resident.bit'} and all(
            expected_hashes.get(config['detector']['root'] + '/' + path) == value
            for path,value in summary.get('runtime_asset_sha256',{}).items()),
        'captured_all_declared_frames': summary['capture']['captured_frames'] == config['expected_capture_frames'],
        'processed_frame_rows_match': len(frames) == summary['processed_frames'],
        'global_latency_covers_all_observations': summary['latency_entire_stream']['count'] == summary['processed_frames'],
        'row_run_ids_match': all(r.get('run_id') == summary['run_id'] for r in events + frames),
        'unique_event_ids': len({r['event_id'] for r in events}) == len(events),
        'event_counts_match_summary': all(event_counts[k] == summary['counts'][k] for k in event_counts),
        'publication_count_matches': summary['timings']['event_publication']['count'] == len(events),
        'capture_clean_eof': summary['capture']['capture_done'] and summary['capture']['capture_error'] is None,
        'all_forward_calls_accounted': summary['model_forwards'] == summary['base_model_forwards'] + summary['warmup_model_forwards'] + summary['endpoint_recovery_forwards'] + summary.get('birth_refinement_forwards', 0)
    }
    latency = summary['latency_entire_stream']
    publication = summary['timings']['event_publication']
    clock = {
        'no_future_frames': summary['future_frame_violations'] == protocol['future_frame_violations'],
        'bounded_application_queue': summary['capture']['maximum_application_queue_frames'] <= protocol['maximum_application_queue_frames'],
        'capture_deadline': summary['capture']['capture_lateness_ms']['maximum_ms'] <= protocol['maximum_capture_lateness_ms'],
        'observation_p95_deadline': latency['p95_upper_bound_ms'] is not None and latency['p95_upper_bound_ms'] <= protocol['maximum_observation_p95_upper_bound_ms'],
        'observation_max_deadline': latency['maximum_ms'] <= protocol['maximum_observation_age_ms'],
        'event_publication_deadline': publication['maximum_ms'] is None or publication['maximum_ms'] <= protocol['maximum_event_publication_age_ms'],
        'drain_deadline': summary['drain_after_last_source_frame_s'] <= protocol['maximum_end_of_stream_drain_s']
    }
    reference = freeze.get('external_reference') or {}
    direction_for_kind = {'IN': config['in_direction'], 'OUT': 'A->B' if config['in_direction'] == 'B->A' else 'B->A'}
    # UP/DOWN are valid only for the explicitly configured vertical camera.
    directional = {}
    if config['axis'] == 'y':
        for kind, direction in direction_for_kind.items():
            directional['UP' if direction == 'B->A' else 'DOWN'] = event_counts[kind]
    compared = {k: directional[k] == value for k, value in reference.items() if value is not None and k in directional}
    count_reference_pass = bool(compared) and all(compared.values())
    return {'status': 'COMPLETED_EXTERNAL_PROTOCOL_ASSESSMENT', 'run_id': summary['run_id'],
            'protocol_version': protocol['version'], 'integrity_checks': integrity, 'clock_checks': clock,
            'integrity_pass': all(integrity.values()), 'service_clock_pass': all(integrity.values()) and all(clock.values()),
            'user_directional_reference': reference, 'actual_directional_counts': directional,
            'count_reference_checks': compared, 'count_reference_pass': count_reference_pass,
            'counts_and_service_pass': all(integrity.values()) and all(clock.values()) and count_reference_pass,
            'historical_runtime_500ms_clock_pass': summary['realtime_clock_pass'],
            'event_precision_recall_verified': False, 'physical_camera_transport_verified': False,
            'event_visual_review': 'pending separate recorded-source inspection',
            'stream_wall_elapsed_s': summary['stream_wall_elapsed_s'],
            'observation_latency': latency, 'event_publication_age': publication}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'freeze', 'protocol', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    load = lambda p: json.loads(p.read_text())
    result = assess(load(args.run / 'summary.json'), read_rows(args.run / 'events.jsonl'), read_rows(args.run / 'frames.jsonl'),
                    load(args.run / 'status.json'), load(args.freeze), load(args.protocol), hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
                    {n:hashlib.sha256((args.run/n).read_bytes()).hexdigest() for n in ('summary.json','events.jsonl','frames.jsonl','transform.json')})
    result['evidence_file_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [args.run / n for n in ('summary.json', 'events.jsonl', 'frames.jsonl', 'status.json')] + [args.freeze, args.protocol]}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in ('integrity_pass', 'service_clock_pass', 'count_reference_pass', 'counts_and_service_pass')}))


if __name__ == '__main__':
    main()
