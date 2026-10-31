"""Independent read/window incidence, lifecycle, pressure and model-score checks."""
from pathlib import Path
from collections import Counter
import hashlib,json,numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=load(ROOT/'protocol/stream_v1.json');folder=ROOT/'delivery';summary=load(folder/'results/summary.json')
    assert sha(ROOT/'protocol/stream_v1.json')==sha(folder/'protocol/stream_v1.json')==summary['protocol_sha256']
    for r in load(folder/'delivery_manifest.json')['files']:
        path=folder/r['file'];assert path.stat().st_size==r['bytes'] and sha(path)==r['sha256']
    for name,digest in p['input_sha256'].items():assert sha(ROOT/'input'/name)==sha(folder/'input'/name)==digest
    for name in ['stream_linker.py','run_experiments.py','identity_worker.py']:assert sha(ROOT/'tools'/name)==sha(folder/'tools'/name)
    assert sha(ROOT/'input/association.py')==sha(PROJECT/'rf_queue_20261026/tools/association.py')==p['association_component_sha256']
    assert sha(ROOT/'tools/identity_worker.py')==sha(PROJECT/'confirmed12_capture_identity_20261029/tools/identity_worker.py')
    runtime_source=(ROOT/'tools/run_experiments.py').read_text(encoding='utf-8')
    assert 'source_first_query_reference_path' not in runtime_source and 'private_mock_read_ownership' not in runtime_source
    captures=load(ROOT/'input/runtime_captures.json');source_events=load(PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/events.json')
    reference={r['event_id']:r for r in source_events};registry=load(ROOT/'input/runtime_registry.json')
    cases=load(ROOT/'input/runtime_cases.json');private={r['case_id']:r['read_ownership_for_software_audit_only'] for r in load(ROOT/'input/private_mock_read_ownership.json')}
    stream=load(ROOT/'input/runtime_visual_stream.json');stream_by={r['frame0']:r for r in stream};captures_by={r['event_id']:r for r in captures}
    for c in captures:
        assert sha(Path(c['local_snapshot_path']))==c['snapshot_sha256'] and c['snapshot_source_frame0']<=c['frame0']
        assert c['frame0']==reference[c['event_id']]['frame0'] and c['track_id']==reference[c['event_id']]['track_id']
    ready_galleries={};model_scores=0;image_dots=0;max_feature_error=0.;max_score_error=0.;rf_matrices=0;rf_pairs=0
    all_terminal=Counter();checked_cases=[];all_ledgers=0;unique_read_assignments=0
    for case in cases:
        dest=folder/'results/cases'/case['case_id'];events=load(dest/'events.json');s=load(dest/'summary.json')
        assert len(events)==s['event_ledgers']==12 and [r['event_id'] for r in events]==[r['event_id'] for r in captures]
        assert s in summary['cases'];group=s['worker_group']
        if group not in ready_galleries:
            ready_galleries[group]=load(folder/'results'/group/'gallery_vectors.json')
            assert ready_galleries[group]['models_and_thresholds']==p['source_identity']['conditions']
            stopped=load(folder/'results'/group/'shutdown.json');assert len(stopped)==1 and stopped[0]['kind']=='stopped'
        gallery=ready_galleries[group];labels=gallery['labels'];entries=gallery['entries']
        expected_rf={};simulation_links=[];late_unique=set()
        if case['mode'] not in ['burst_capacity','expired']:
            trace=load(dest/'stream_linker_trace.json');slot_map={r['reservation_id']:r for r in trace['slots']}
            contexts=sorted([r for r in trace['audit'] if r['kind']=='RF_CAUSAL_CONTEXT'],key=lambda r:r['frame0'])
            assert len(contexts)==12 and all(r['rf_decision'] is not None for r in events)
            known_reads={r['read_id']:r for r in case['reads']};consumed=set()
            births={r['reservation_id']:r for r in trace['audit'] if r['kind']=='RESERVATION_OPENED'}
            for sid,slot in slot_map.items():
                birth=births[sid];assert birth['frame0']==slot['opened_frame0'] and birth['track_id']==slot['track_id']
                if not slot['birth_was_late_count']:
                    assert str(slot['track_id']) in stream_by[birth['frame0']]['visual_positions']
                    assert .25<=stream_by[birth['frame0']]['visual_positions'][str(slot['track_id'])]<=.75
                if slot['event_id'] is not None:
                    assert slot['closed_frame0']==captures_by[slot['event_id']]['frame0'] and slot['track_id']==captures_by[slot['event_id']]['track_id']
                else:
                    assert slot['orphan_closed'] is True and slot['closed_frame0']==slot['last_seen_frame0']
            for context in contexts:
                now=context['frame0'];identity=context['event_id'];capture=captures_by[identity];cutoff=capture['frame0']+p['RF_decision_wait_frames']
                assert now==cutoff and set(context['already_consumed_read_ids'])==consumed
                passages=context['passages'];target=next(r for r in passages if r['event_id']==context['target_reservation_id'])
                assert target['closed']==capture['frame0'] and target['snapshot_id']==(None if identity in case['missing_snapshot_event_ids'] else identity)
                received=context['received_reads'];assert {r['read_id'] for r in received}=={r['read_id'] for r in case['reads'] if r['received']<=now}
                assert all(r==known_reads[r['read_id']] and r['received']<=now for r in received)
                # Explicit incidence matrix over every received read and every
                # causally visible reservation, including not-yet-counted ones.
                matrix=[]
                for w in passages:
                    assert w['opened']<=now and w['event_id'] in slot_map
                    slot=slot_map[w['event_id']];assert w['opened']==slot['opened_frame0']
                    assert w['closed']<=now or w['closed']==p['source_frame0_scope'][1]+p['RF_decision_wait_frames']+1
                    matrix.append([r['valid'] and r['received']>=r['captured'] and r['received']<=cutoff and
                        r['reader']==w['reader'] and w['opened']<=cutoff and w['opened']<=r['captured']<=w['closed'] for r in received])
                rf_matrices+=1;rf_pairs+=sum(len(r) for r in matrix)
                t_index=next(i for i,w in enumerate(passages) if w['event_id']==target['event_id'])
                indices=[j for j,r in enumerate(received) if matrix[t_index][j] and r['read_id'] not in consumed]
                timely=[received[j] for j in indices];codes=sorted({r['code'] for r in timely})
                shared=any(sum(row[j] for row in matrix)>1 for j in indices)
                if len(codes)==1 and not shared and codes[0] in registry:
                    status='RF_UNIQUE_CANDIDATE';candidate=registry[codes[0]];consumed.update(r['read_id'] for r in timely)
                    unique_read_assignments+=len(timely)
                else:
                    candidate=None;status='RF_SHARED_WINDOW' if shared else 'RF_MULTI_CODE' if len(codes)>1 else 'RF_UNREGISTERED_CODE' if codes else 'RF_NO_TIMELY_READ'
                expected_rf[identity]={'rf_status':status,'identity_candidate':candidate,'timely_observation_ids':[r['read_id'] for r in timely],
                                       'candidate_code_count':len(codes),'decision_frame0':cutoff}
                actual=next(r['rf_decision'] for r in events if r['event_id']==identity)
                assert all(actual[key]==value for key,value in expected_rf[identity].items())
                assert actual['verified_identity'] is False and actual['emitted_frame0']==now
                late=[r['read_id'] for r in case['reads'] if r['valid'] and r['received']>=r['captured'] and
                    cutoff<r['received']<=p['source_frame0_scope'][1] and r['reader']==target['reader'] and target['opened']<=r['captured']<=target['closed']]
                assert actual['late_observation_ids']==late;late_unique.update(late)
                if candidate is not None:
                    owned={r['read_id']:r for r in private[case['case_id']]}
                    intended={owned[r['read_id']]['intended_mock_registry_record'] for r in timely}
                    simulation_links.append({'event_id':identity,'RF_candidate':candidate,'simulated_read_owner_records':sorted(intended),
                        'mock_owner_matches_event':candidate==f'SIM-REGISTRY-{[c["event_id"] for c in captures].index(identity)+1:03d}'})
            assert consumed==set(trace['consumed_read_ids']) and len(consumed)==len(set(consumed))
        else:
            pressure=s['pressure_control'];assert pressure['admission_gate_blocked_worker_before_dequeue'] is True
            assert pressure['statuses_before_release']=={'QUEUED':4,'UNRESOLVED_QUEUE_CAPACITY':8}
            assert pressure['admissions_finished_wall_ns']<=pressure['gate_released_wall_ns']
        statuses=Counter();case_queries=0
        for row in events:
            identity=row['event_id'];assert row['verified_identity'] is False and row['source_cow_identity_reference'] is None and row['RF_input_is_synthetic'] is True
            assert row['snapshot_sha256']==captures_by[identity]['snapshot_sha256'] and load(dest/(identity+'.json'))==row
            result=row['worker_result'];status=row['status']
            if case['mode'] not in ['burst_capacity','expired']:
                rf=row['rf_decision']
                if rf['identity_candidate'] is not None:
                    assert status=='RF_UNIQUE_CANDIDATE_UNVERIFIED' and result is None and 'enqueue_wall_ns' not in row
                elif identity in case['missing_snapshot_event_ids']:
                    assert status=='UNRESOLVED_NO_SNAPSHOT' and result is None
                else:assert result is not None and result['status']=='COMPLETED'
            if result is not None:
                assert result['event_id']==row['task_id'] and result['started_wall_ns']<=result['finished_wall_ns']<=result['parent_received_wall_ns']
                if case['mode'] in ['burst_capacity','expired']:
                    assert result['started_wall_ns']>=s['pressure_control']['gate_released_wall_ns']
                else:assert result['started_wall_ns']>=row['enqueue_wall_ns']
                if result['status']=='EXPIRED_WAITING':
                    assert result['conditions']==[] and result['started_wall_ns']>row['deadline_wall_ns'] and status=='UNRESOLVED_EXPIRED_WAITING'
                else:
                    assert result['status']=='COMPLETED' and len(result['conditions'])==5 and result['finished_wall_ns']<=row['deadline_wall_ns']
                    old={r['condition']:r for r in reference[identity]['worker_result']['conditions']}
                    passing=False
                    for c,definition in zip(result['conditions'],p['source_identity']['conditions']):
                        assert c['condition']==definition['name'] and c['model_sha256']==definition['checkpoint_sha256'] and c['frozen_threshold']==definition['threshold']
                        original=old[c['condition']];assert c['query_tensor_sha256']==original['query_tensor_sha256']
                        vector=np.asarray(c['feature_vector'],float);g=np.asarray(gallery['conditions'][c['condition']]['features'],float)
                        difference=float(np.max(np.abs(vector-np.asarray(original['feature_vector']))));max_feature_error=max(max_feature_error,difference);assert difference<=1e-5
                        scores=np.asarray([sum(a*b for a,b in zip(row,vector)) for row in g]);error=float(np.max(np.abs(scores-np.asarray(c['gallery_image_cosines']))))
                        max_score_error=max(max_score_error,error);assert error<1e-12
                        aggregated=[max(float(scores[i]) for i,r in enumerate(entries) if r['identity']==label) for label in labels]
                        best=max(range(len(labels)),key=lambda j:aggregated[j]);assert labels[best]==c['candidate_anonymous_id']
                        assert abs(aggregated[best]-c['cosine_similarity'])<1e-12 and c['passes_frozen_threshold']==(aggregated[best]>=definition['threshold'])
                        assert c['verified_identity'] is False and c['passes_frozen_threshold']==original['passes_frozen_threshold']
                        passing|=c['passes_frozen_threshold'];case_queries+=1;model_scores+=1;image_dots+=len(scores)
                    assert status==('VISUAL_THRESHOLD_CANDIDATE_UNVERIFIED' if passing else 'VISUAL_ALL_CONDITIONS_REJECTED')
            statuses[status]+=1
        assert dict(statuses)==s['terminal_status_counts'] and case_queries==s['real_query_forward_calls']
        assert all(status not in ['CREATED','QUEUED'] for status in statuses)
        assert sum(len(e['rf_decision']['late_observation_ids']) for e in events if e['rf_decision'])==s['late_observation_links']
        if case['mode']=='burst_capacity':assert statuses=={'VISUAL_ALL_CONDITIONS_REJECTED':4,'UNRESOLVED_QUEUE_CAPACITY':8} and case_queries==20
        if case['mode']=='expired':assert statuses=={'UNRESOLVED_EXPIRED_WAITING':4,'UNRESOLVED_QUEUE_CAPACITY':8} and case_queries==0
        if case['mode']=='wrong':assert len(simulation_links)==5 and all(not x['mock_owner_matches_event'] for x in simulation_links)
        if case['mode'] in ['single','duplicates','inside']:assert len(simulation_links)==5 and all(x['mock_owner_matches_event'] for x in simulation_links)
        checked_cases.append({'case_id':case['case_id'],'RF_status_counts':s['RF_status_counts'],'terminal_status_counts':dict(statuses),
            'real_query_forwards':case_queries,'late_observation_links':s['late_observation_links'],'unique_late_read_ids':len(late_unique),
            'mock_RF_ownership_audit':simulation_links,'notes':'Mock owner correspondence is a software control, not real cow identity correctness.'})
        all_terminal.update(statuses);all_ledgers+=len(events)
    assert all_ledgers==summary['event_ledgers']==144 and model_scores==summary['true_query_forward_calls']==515 and image_dots==15450
    assert all_terminal=={'VISUAL_ALL_CONDITIONS_REJECTED':84,'VISUAL_THRESHOLD_CANDIDATE_UNVERIFIED':19,
                         'RF_UNIQUE_CANDIDATE_UNVERIFIED':20,'UNRESOLVED_NO_SNAPSHOT':1,'UNRESOLVED_QUEUE_CAPACITY':16,'UNRESOLVED_EXPIRED_WAITING':4}
    assert rf_matrices==120
    for case_id in ['S02_duplicates','S03_delay_inside']:
        a=next(c for c in checked_cases if c['case_id']=='S01_single');b=next(c for c in checked_cases if c['case_id']==case_id)
        assert a['RF_status_counts']==b['RF_status_counts'] and a['terminal_status_counts']==b['terminal_status_counts'] and a['real_query_forwards']==b['real_query_forwards']
    record={'status':'144_STREAM_EVENT_LEDGERS_120_CAUSAL_RF_CONTEXTS_AND515_REAL_QUERY_DECISIONS_INDEPENDENTLY_VERIFIED',
        'cases_checked':12,'event_ledgers':144,'causal_RF_contexts':rf_matrices,'read_window_incidence_entries':rf_pairs,
        'real_model_query_results':model_scores,'image_dotproducts_verified':image_dots,'identity_scores_verified':model_scores*6,
        'maximum_query_feature_difference_from_prior_actual_source_run':max_feature_error,'maximum_independent_score_error':max_score_error,
        'unique_RF_consumed_observation_links':unique_read_assignments,'all_terminal_status_counts':dict(all_terminal),
        'case_checks':checked_cases,'source_events_are_reused_not144_independent_cows':True,
        'source_cow_identity_accuracy':None,'RF_hardware_connected':False,'new_detector_forwards':0,'new_training_updates':0,
        'FPGA_execution_verified':False,'whole_goal_complete':False}
    target=ROOT/'results/independent_verification.json';assert not target.exists();target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='case_checks'}))
if __name__=='__main__':main()
