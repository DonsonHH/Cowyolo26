from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
folder=ROOT/'delivery/results/foreground_idle_identity';rows=load(folder/'timing_rows.json');intervals=load(folder/'worker_pause_intervals.json');background=load(folder/'background/record.json')
assert len(rows)==len(intervals)==392 and len(background['jobs'])==11
for interval,row in zip(intervals,rows):
 assert interval['slot']==row['slot']
 a,b,c,d,e=[interval[k] for k in ['pause_requested_monotonic_ns','pause_acknowledged_monotonic_ns','foreground_started_monotonic_ns','foreground_completed_monotonic_ns','resume_sent_monotonic_ns']]
 assert a<=b<=c<=d<=e and c==row['started_monotonic_ns'] and d==row['completed_monotonic_ns']
 assert interval['child_PID']==background['PID']
for previous,current in zip(intervals,intervals[1:]):assert previous['resume_sent_monotonic_ns']<=current['pause_requested_monotonic_ns']
def stopped_overlap(start,end):
 # SIGCONT may execute the child before the parent timestamps its return.
 # Only acknowledgement -> foreground completion is certainly stopped.
 return sum(max(0,min(end,i['foreground_completed_monotonic_ns'])-max(start,i['pause_acknowledged_monotonic_ns'])) for i in intervals)
jobs=[]
for job in background['jobs']:
 start=job['started_monotonic_ns'];end=job['completed_monotonic_ns'];network_end=job['inference_finished_monotonic_ns']
 network_begin=round(network_end-job['actual_identity_network_ms']*1e6)
 stopped=stopped_overlap(start,end)/1e6;network_stopped=stopped_overlap(network_begin,network_end)/1e6
 elapsed=(end-start)/1e6;network_wall=job['actual_identity_network_ms'];network_CPU=job['identity_network_process_CPU_ms'];process_CPU=job['worker_process_CPU_ms']
 assert 0<network_CPU<=process_CPU and network_CPU<=network_wall+1e-3 and process_CPU<=elapsed+1e-3
 assert network_CPU<=network_wall-network_stopped+2 and process_CPU<=elapsed-stopped+2
 jobs.append({'frame0':job['source_frame0'],'queue_ms':job['queue_wait_ms'],'job_wall_ms':elapsed,'job_CPU_ms':process_CPU,
  'job_stopped_during_foreground_ms':stopped,'network_elapsed_ms':network_wall,'network_CPU_ms':network_CPU,
  'network_stopped_during_foreground_ms':network_stopped,'photo_crop_and_save_elapsed_ms':job['runtime_native_crop_and_photo_save_ms'],
  'enqueue_to_result_ms':job['enqueue_to_result_ms']})
assert any(j['network_stopped_during_foreground_ms']>0 for j in jobs)
previous=load(ROOT.parent/'pynq_periodic_joint_20261030/results/independent_verification.json');current=load(ROOT/'results/independent_verification.json')
result={'status':'ALL392_OS_ACKNOWLEDGED_WORKER_PAUSE_WINDOWS_AND11_REAL_JOB_CPU_TIME_RECORDS_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_stop_resume_pairs':392,'unique_actual_worker_PID':background['PID'],
 'all_foreground_critical_sections_inside_worker_stopped_intervals':True,'actual_network_calls_advanced_across_idle_windows':True,
 'network_elapsed_includes_pauses_and_is_not_pure_inference_latency':True,'jobs':jobs,
 'mean_network_CPU_ms':float(np.mean([r['network_CPU_ms'] for r in jobs])),
 'mean_photo_crop_and_save_elapsed_ms':float(np.mean([r['photo_crop_and_save_elapsed_ms'] for r in jobs])),
 'mean_network_elapsed_ms':float(np.mean([r['network_elapsed_ms'] for r in jobs])),
 'max_queue_ms':max(j['queue_ms'] for j in jobs),'max_enqueue_to_result_ms':max(j['enqueue_to_result_ms'] for j in jobs),
 'prior_direct_concurrency_deadline_misses':previous['cases'][1]['deadline_misses'],
 'current_idle_deadline_misses':current['cases'][1]['deadline_misses'],'each_condition_single_run_not_statistical_replicates':True,
 'source_counts_unchanged':[r['source_down_count'] for r in current['cases']],
 'whole_goal_complete':False,'evidence_hashes':{r:sha(ROOT/r) for r in ['protocol/run_v1.json','tools/board_idle.py','tools/background_idle_worker.py',
 'delivery/results/foreground_idle_identity/worker_pause_intervals.json','delivery/results/foreground_idle_identity/background/record.json']}}
file=ROOT/'results/idle_gate_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['jobs','evidence_hashes']}))
