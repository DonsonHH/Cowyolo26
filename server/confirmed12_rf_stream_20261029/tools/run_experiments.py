"""Causal synthetic RF ingress with real CPU fallback queries and bounded pressure controls."""
from pathlib import Path
from collections import Counter
from dataclasses import asdict
import copy,hashlib,json,multiprocessing,os,queue,socket,sys,time,tarfile
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/confirmed12_rf_stream_20261029');PROJECT=ROOT.parent
sys.path.insert(0,str(ROOT/'input'))
from association import Read
from stream_linker import OnlineLinker
from identity_worker import worker_main
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n')

class GatedQueue:
    def __init__(self,real_queue,gate):self.real=real_queue;self.gate=gate
    def get(self):self.gate.wait();return self.real.get()

def start_worker(ctx,p,label,gated=False):
    folder=ROOT/'results'/label;folder.mkdir(exist_ok=False)
    tasks=ctx.Queue(p['queue_capacity']);results=ctx.Queue(p['worker_result_capacity']);gate=ctx.Event()
    if not gated:gate.set()
    protocol={'identity':p['source_identity'],'identity_gallery_export_path':str(folder/'gallery_vectors.json')}
    process=ctx.Process(target=worker_main,args=(GatedQueue(tasks,gate),results,protocol,str(PROJECT)));process.start()
    ready=results.get(timeout=120);assert ready['kind']=='ready' and ready['device']=='cpu' and ready['conditions']==5
    save(folder/'ready.json',ready)
    return {'process':process,'tasks':tasks,'results':results,'gate':gate,'label':label,'folder':folder,'ready':ready}
def stop_worker(worker):
    worker['gate'].set();worker['tasks'].put(None,timeout=10);worker['process'].join(timeout=30)
    assert worker['process'].exitcode==0
    messages=[]
    while True:
        try:messages.append(worker['results'].get(timeout=.1))
        except queue.Empty:break
    assert any(m['kind']=='stopped' for m in messages);save(worker['folder']/'shutdown.json',messages)
def verdict(result):
    if result['status']!='COMPLETED':return 'UNRESOLVED_'+result['status']
    return 'VISUAL_THRESHOLD_CANDIDATE_UNVERIFIED' if any(c['passes_frozen_threshold'] for c in result['conditions']) else 'VISUAL_ALL_CONDITIONS_REJECTED'

def run_case(case,p,stream,captures,registry,worker):
    folder=ROOT/'results/cases'/case['case_id'];folder.mkdir(exist_ok=False)
    lookup={c['event_id']:c for c in captures};at_close={c['frame0']:[] for c in captures}
    for c in captures:at_close[c['frame0']].append(c)
    rows={};messages=[];receipts=list(case['reads']);cursor=0;pending_peak=0;new_queries=0
    linker=OnlineLinker(registry,reader=p['RF_reader'],wait_frames=p['RF_decision_wait_frames'],
                        orphan_gap_frames=p['orphan_gap_frames'],horizon_frame0=p['source_frame0_scope'][1])
    def receive(message):
        nonlocal new_queries
        messages.append(message)
        if message['kind']=='fatal':raise RuntimeError(str(message))
        if message['kind']!='result':return
        task=message['event_id'];row=next(r for r in rows.values() if r['task_id']==task)
        assert row['status']=='QUEUED';message['parent_received_wall_ns']=time.monotonic_ns()
        row['worker_result']=message;row['status']=verdict(message);row['verified_identity']=False
        new_queries+=len(message['conditions'])
    def poll():
        while True:
            try:message=worker['results'].get_nowait()
            except queue.Empty:break
            receive(message)
    def enqueue(row,expired=False):
        nonlocal pending_peak
        capture=lookup[row['event_id']];now=time.monotonic_ns();row['enqueue_wall_ns']=now
        row['deadline_wall_ns']=now-1 if expired else now+round(p['worker_deadline_wall_seconds']*1e9)
        job={'event_id':row['task_id'],'oriented_crop_path':capture['snapshot_path'],
             'oriented_crop_sha256':capture['snapshot_sha256'],'deadline_wall_ns':row['deadline_wall_ns']}
        try:worker['tasks'].put_nowait(job);row['status']='QUEUED'
        except queue.Full:row['status']='UNRESOLVED_QUEUE_CAPACITY'
        pending_peak=max(pending_peak,sum(r['status']=='QUEUED' for r in rows.values()))
    def decision_row(capture,rf=None):
        return {'event_id':capture['event_id'],'task_id':case['case_id']+'__'+capture['event_id'],
                'snapshot_id':capture['snapshot_id'],'snapshot_sha256':capture['snapshot_sha256'],'source_passage_frame0':capture['frame0'],
                'rf_decision':copy.deepcopy(rf),'status':'CREATED','worker_result':None,'verified_identity':False,
                'source_cow_identity_reference':None,'RF_input_is_synthetic':True}
    began=time.monotonic_ns();is_pressure=case['mode'] in ['burst_capacity','expired']
    if is_pressure:
        assert not worker['gate'].is_set()
        for capture in captures:
            row=decision_row(capture);rows[row['event_id']]=row;enqueue(row,expired=case['mode']=='expired')
        admissions_finished=time.monotonic_ns();before_release=Counter(r['status'] for r in rows.values())
        assert before_release=={'QUEUED':4,'UNRESOLVED_QUEUE_CAPACITY':8}
        worker['gate'].set();gate_released=time.monotonic_ns()
        pressure={'admission_gate_blocked_worker_before_dequeue':True,'statuses_before_release':dict(before_release),
                  'admissions_finished_wall_ns':admissions_finished,'gate_released_wall_ns':gate_released,
                  'expired_deadlines_deliberately_injected':case['mode']=='expired'}
    else:
        pressure=None
        for sample in stream:
            due=began+sample['recorded_relative_available_wall_ns']
            while time.monotonic_ns()<due:
                poll();time.sleep(min(.005,max(0,(due-time.monotonic_ns())/1e9)))
            frame=sample['frame0'];incoming=[]
            while cursor<len(receipts) and receipts[cursor]['received']<=frame:
                incoming.append(Read(**receipts[cursor]));cursor+=1
            closing=[]
            for capture in at_close.get(frame,[]):
                closing.append({'event_id':capture['event_id'],'track_id':capture['track_id'],'direction':capture['direction'],
                    'snapshot_id':None if capture['event_id'] in case['missing_snapshot_event_ids'] else capture['snapshot_id']})
            fresh=linker.step(frame,{int(k):v for k,v in sample['visual_positions'].items()},closing,incoming)
            for rf in fresh:
                capture=lookup[rf['event_id']];row=decision_row(capture,rf);rows[row['event_id']]=row
                row['decision_seen_wall_ns']=time.monotonic_ns()
                if rf['identity_candidate'] is not None:
                    row['status']='RF_UNIQUE_CANDIDATE_UNVERIFIED'
                elif rf['snapshot_id'] is None:
                    row['status']='UNRESOLVED_NO_SNAPSHOT'
                else:enqueue(row)
            poll()
        linker.finish(p['source_frame0_scope'][1]);assert cursor==len(receipts)
        for identity,row in rows.items():
            final_rf=linker.outputs[identity]
            assert row['rf_decision']['identity_candidate']==final_rf['identity_candidate'] and row['rf_decision']['rf_status']==final_rf['rf_status']
            row['rf_decision']=copy.deepcopy(final_rf)
        save(folder/'stream_linker_trace.json',linker.export())
    source_replay_done=time.monotonic_ns();deadline=time.monotonic()+p['worker_drain_wall_seconds']
    while any(r['status']=='QUEUED' for r in rows.values()) and time.monotonic()<deadline:
        try:receive(worker['results'].get(timeout=.1))
        except queue.Empty:pass
    assert not any(r['status']=='QUEUED' for r in rows.values())
    assert len(rows)==12 and all(row['verified_identity'] is False for row in rows.values())
    event_rows=[rows[c['event_id']] for c in captures]
    for row in event_rows:save(folder/(row['event_id']+'.json'),row)
    save(folder/'events.json',event_rows);save(folder/'worker_messages.json',messages)
    flags=Counter(r['status'] for r in event_rows);rf_flags=Counter(r['rf_decision']['rf_status'] for r in event_rows if r['rf_decision'])
    summary={'case_id':case['case_id'],'mode':case['mode'],'event_ledgers':12,'terminal_status_counts':dict(flags),
             'RF_status_counts':dict(rf_flags),'real_query_forward_calls':new_queries,
             'completed_query_jobs':sum(r['worker_result'] is not None and r['worker_result']['status']=='COMPLETED' for r in event_rows),
             'worker_results_after_source_replay_end':sum(r['worker_result'] is not None and r['worker_result']['finished_wall_ns']>source_replay_done for r in event_rows),
             'max_observed_inflight_including_service':pending_peak,'source_replay_done_wall_ns':source_replay_done,
             'late_observation_links':sum(len(r['rf_decision']['late_observation_ids']) for r in event_rows if r['rf_decision']),
             'pressure_control':pressure,'worker_group':worker['label'],'RF_hardware_connected':False,
             'source_cow_identity_accuracy':None,'FPGA_execution_verified':False,'whole_goal_complete':False}
    if case['mode']=='burst_capacity':assert flags=={'VISUAL_ALL_CONDITIONS_REJECTED':4,'UNRESOLVED_QUEUE_CAPACITY':8} and new_queries==20
    if case['mode']=='expired':assert flags=={'UNRESOLVED_EXPIRED_WAITING':4,'UNRESOLVED_QUEUE_CAPACITY':8} and new_queries==0
    save(folder/'summary.json',summary);print(json.dumps(summary),flush=True);return summary

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    p=load(ROOT/'protocol/stream_v1.json');assert sha(ROOT/'tools/stream_linker.py')==p['stream_adapter_sha256']
    assert sha(ROOT/'tools/identity_worker.py')==p['worker_sha256']
    assert sha(PROJECT/'identity_training/tools/training_primitives.py')==p['body_transform_sha256']
    for name,digest in p['input_sha256'].items():
        if name.startswith('private_'):continue
        assert sha(ROOT/'input'/name)==digest
    captures=load(ROOT/'input/runtime_captures.json');stream=load(ROOT/'input/runtime_visual_stream.json')
    registry=load(ROOT/'input/runtime_registry.json');cases=load(ROOT/'input/runtime_cases.json')
    allowed={'event_id','frame0','track_id','direction','snapshot_id','snapshot_path','snapshot_sha256','local_snapshot_path','snapshot_source_frame0'}
    assert all(set(c)==allowed for c in captures)
    for c in captures:assert sha(c['snapshot_path'])==c['snapshot_sha256'] and c['snapshot_source_frame0']<=c['frame0']
    assert len(captures)==12 and len(cases)==12 and len(stream)==392
    (ROOT/'results').mkdir(exist_ok=False);(ROOT/'results/cases').mkdir()
    ctx=multiprocessing.get_context('spawn');workers=[];summaries=[]
    try:
        worker=start_worker(ctx,p,'functional_worker');workers.append(worker)
        for case in cases[:10]:summaries.append(run_case(case,p,stream,captures,registry,worker))
        stop_worker(worker)
        for case in cases[10:]:
            worker=start_worker(ctx,p,case['case_id']+'_worker',gated=True);workers.append(worker)
            summaries.append(run_case(case,p,stream,captures,registry,worker));stop_worker(worker)
    finally:
        for worker in workers:
            if worker['process'].is_alive():worker['gate'].set();worker['process'].terminate();worker['process'].join(timeout=5)
    result={'status':'12_EVENT_CAUSAL_RF_STREAM_TEN_FUNCTIONAL_CASES_AND_TWO_REAL_WORKER_PRESSURE_CONTROLS_COMPLETE',
            'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/stream_v1.json'),
            'cases':summaries,'event_ledgers':sum(s['event_ledgers'] for s in summaries),
            'true_query_forward_calls':sum(s['real_query_forward_calls'] for s in summaries),'worker_groups':3,
            'original_source_photos_changed':False,'identity_models_or_thresholds_changed':False,
            'source_cow_identity_accuracy':None,'RF_hardware_connected':False,'new_detector_forwards':0,'new_training_updates':0,
            'FPGA_execution_verified':False,'whole_goal_complete':False}
    assert result['event_ledgers']==144;save(ROOT/'results/summary.json',result)
    files=[]
    for folder in ['input','protocol','tools','tests','results']:
        for file in sorted((ROOT/folder).rglob('*')):
            if file.is_file():files.append({'file':file.relative_to(ROOT).as_posix(),'bytes':file.stat().st_size,'sha256':sha(file)})
    save(ROOT/'delivery_manifest.json',{'files':files});archive=ROOT/'RF_stream_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for row in files:tf.add(ROOT/row['file'],arcname=row['file'])
        tf.add(ROOT/'delivery_manifest.json',arcname='delivery_manifest.json')
    print(json.dumps({'status':result['status'],'files':len(files)+1,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive)}),flush=True)
if __name__=='__main__':main()
