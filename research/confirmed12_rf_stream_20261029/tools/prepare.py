from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    source=PROJECT/'confirmed12_capture_identity_20261029';p=load(source/'protocol/chain_v1.json');s=load(source/'delivery/results/replay/summary.json')
    assert s['event_count']==s['worker_completed_jobs']==12 and s['true_query_forwards']==60
    input_dir=ROOT/'input';input_dir.mkdir(exist_ok=True);protocol_dir=ROOT/'protocol';protocol_dir.mkdir(exist_ok=False)
    assert sha(input_dir/'association.py')==sha(PROJECT/'rf_queue_20261026/tools/association.py')
    (ROOT/'tools/identity_worker.py').write_bytes((source/'tools/identity_worker.py').read_bytes())
    events=load(source/'delivery/results/replay/events.json');captures=[]
    for e in events:
        shot=e['selected_snapshot'];relative='results/replay/'+shot['oriented_path']
        file=source/'delivery'/relative;assert sha(file)==shot['oriented_sha256']
        captures.append({'event_id':e['event_id'],'frame0':e['frame0'],'track_id':e['track_id'],'direction':e['direction'],
            'snapshot_id':e['event_id'],'snapshot_path':REMOTE+'/confirmed12_capture_identity_20261029/'+relative,
            'snapshot_sha256':sha(file),'local_snapshot_path':str(file.resolve()),'snapshot_source_frame0':shot['frame0']})
    save(input_dir/'runtime_captures.json',captures)
    observations=load(PROJECT/'firststage_iou_regression_20261029/delivery/results/original_seed26__original_fused/observations.json')
    import csv
    with (source/'delivery/results/replay/frontend_ticks.csv').open(newline='') as f:ticks={int(r['frame0']):int(r['loop_end_wall_ns']) for r in csv.DictReader(f)}
    start=8915;origin=ticks[start];runtime=[]
    for r in observations:
        frame=r['frame0']
        if not start<=frame<10874:continue
        positions={**r['confirmed_positions'],**r['tentative_positions']}
        assert not set(r['confirmed_positions'])&set(r['tentative_positions'])
        runtime.append({'frame0':frame,'visual_positions':positions,'recorded_relative_available_wall_ns':ticks[frame]-origin})
    assert len(runtime)==392;save(input_dir/'runtime_visual_stream.json',runtime)
    registry={f'SIM-TAG-{i+1:03d}':f'SIM-REGISTRY-{i+1:03d}' for i in range(12)}
    save(input_dir/'runtime_registry.json',registry);cases=[];private=[]
    definitions=[('S00_missing','missing'),('S01_single','single'),('S02_duplicates','duplicates'),('S03_delay_inside','inside'),
                 ('S04_late','late'),('S05_conflict','conflict'),('S06_invalid','invalid'),('S07_wrong_single','wrong'),
                 ('S08_unregistered','unregistered'),('S09_missing_snapshot','missing_snapshot')]
    for name,mode in definitions:
        reads=[];owners=[]
        for i,e in enumerate(captures):
            if mode in ['missing','missing_snapshot']:continue
            captured=e['frame0']-5;received=captured;code=f'SIM-TAG-{i+1:03d}'
            if mode=='inside':received=e['frame0']+10
            if mode=='late':received=e['frame0']+20
            if mode=='wrong':code=f'SIM-TAG-{(i+1)%12+1:03d}'
            if mode=='unregistered':code=f'SIM-UNREGISTERED-{i+1:03d}'
            def add(suffix,code_value=code,received_value=received,reader='lane1',valid=True):
                uid=f'{name}_read{i+1:03d}_{suffix}';reads.append({'read_id':uid,'code':code_value,'captured':captured,'received':received_value,'reader':reader,'valid':valid})
                owners.append({'read_id':uid,'simulated_for_event_id':e['event_id'],'intended_mock_registry_record':f'SIM-REGISTRY-{i+1:03d}'})
            if mode=='invalid':
                add('wrong_lane',reader='lane2');add('invalid',valid=False);add('bad_clock',received_value=captured-1)
            else:
                add('primary')
                if mode=='duplicates':add('repeat1',received_value=received+1);add('repeat2',received_value=received+2)
                if mode=='conflict':add('conflict',code_value=f'SIM-TAG-{(i+1)%12+1:03d}')
        reads.sort(key=lambda r:(r['received'],r['read_id']))
        case={'case_id':name,'mode':mode,'reads':reads,'missing_snapshot_event_ids':[captures[4]['event_id']] if mode=='missing_snapshot' else [],
              'pacing':'recorded_cached_frontend_1x','is_actual_RF_stream':False}
        cases.append(case);private.append({'case_id':name,'read_ownership_for_software_audit_only':owners})
    cases += [{'case_id':'P00_burst_capacity','mode':'burst_capacity','reads':[],'missing_snapshot_event_ids':[],
               'pacing':'controlled_simultaneous_admission_gate','is_actual_RF_stream':False},
              {'case_id':'P01_expired','mode':'expired','reads':[],'missing_snapshot_event_ids':[],
               'pacing':'controlled_simultaneous_admission_gate_with_expired_deadlines','is_actual_RF_stream':False}]
    save(input_dir/'runtime_cases.json',cases);save(input_dir/'private_mock_read_ownership.json',private)
    protocol={'name':'Causal visual reservation / synthetic RF stream / real frozen ReID queries on12 captured source events',
       'created_UTC':datetime.now(timezone.utc).isoformat(),'source_capture_final_review_sha256':sha(source/'results/final_review_v3.json'),
       'source_capture_protocol_sha256':sha(source/'protocol/chain_v1.json'),'source_identity':p['identity'],
       'body_transform_sha256':p['body_transform_sha256'],'worker_sha256':sha(ROOT/'tools/identity_worker.py'),
       'source_first_query_reference_path':REMOTE+'/confirmed12_capture_identity_20261029/results/replay/events.json',
       'source_first_query_reference_sha256':sha(source/'delivery/results/replay/events.json'),
       'source_frozen_count_candidate_sha256':p['frozen_development_candidate_sha256'],
       'source_fps':25,'source_step_frames':5,'source_frame0_scope':[8915,10873],'RF_reader':'lane1',
       'visual_reservation_birth_center_y_inclusive':[.25,.75],'include_tentative_visual_observations_as_blockers':True,
       'RF_decision_wait_frames':15,'orphan_gap_frames':50,'RF_capture_guard_frames':0,
       'association_component_sha256':sha(input_dir/'association.py'),'stream_adapter_sha256':sha(ROOT/'tools/stream_linker.py'),
       'queue_capacity':4,'worker_result_capacity':16,'worker_deadline_wall_seconds':30,'worker_drain_wall_seconds':30,
       'functional_case_pacing':'Use saved previous cached-frontend relative monotonic availability at1x; no new foreground decoding or inference.',
       'stress_case_scope':'Deterministic admission barrier holds worker before dequeue:4accepted8capacity rejects; expired case executes no query for4expired accepted tasks.',
       'cases':[c['case_id'] for c in cases],'functional_cases':10,'pressure_controls':2,'expected_event_ledgers':144,
       'runtime_truth_separation':'Private mock read ownership not passed to OnlineLinker or worker. RF IDs useSIM namespace, not real or public cow identity ground truth.',
       'input_sha256':{f.name:sha(f) for f in input_dir.iterdir() if f.is_file()},
       'real_RF_hardware_connected':False,'source_cow_identity_reference_available':False,
       'new_detector_forwards':0,'new_training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(protocol_dir/'stream_v1.json',protocol)
    print(json.dumps({'protocol_sha256':sha(protocol_dir/'stream_v1.json'),'functional_cases':10,'pressure_controls':2,'event_ledgers_expected':144,
                       'source_trace_duration_host_s':runtime[-1]['recorded_relative_available_wall_ns']/1e9}))
if __name__=='__main__':main()
