from pathlib import Path
from datetime import datetime,timezone
import json,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
v=load(ROOT/'results/UART_metadata_audit.json');recovery=load(ROOT/'results/recovery_independent_verification.json');state=load(ROOT/'metadata_recovery/results/record.json');cases=[]
for case in v['cases']:
 folder=ROOT/'metadata_recovery/results'/case['run'];rows=load(folder/'timing_rows.json');worker=load(folder/'background/record.json');producer=load(folder/'producer_record.json')
 metrics={}
 for key in ['model_ms','processing_ms','after_model_to_count_ms','release_to_count_ms','JPEG_frontend_read_ms','selector_ms']:
  values=[r[key] for r in rows];metrics[key]={'mean':float(np.mean(values)),'P50':float(np.quantile(values,.5)),'P95':float(np.quantile(values,.95)),'P99':float(np.quantile(values,.99)),'max':max(values)}
 memory=next(r for r in state['cases'] if r['run']==case['run'])['cumulative_parent_proc_status']
 cases.append({**case,'metrics':metrics,'backend_mean_network_elapsed_ms':float(np.mean([j['actual_identity_network_ms'] for j in worker['jobs']])),
  'backend_mean_network_CPU_ms':float(np.mean([j['identity_network_process_CPU_ms'] for j in worker['jobs']])),
  'backend_actual_CPU_ms':sum(j['worker_process_CPU_ms'] for j in worker['jobs']),
  'producer_peak':{k:producer[k] for k in ['peak_retained_frames','peak_retained_payload_bytes','peak_transient_payload_bytes']},
  'cumulative_parent_memory_kB':{k:int(re.search(r'^'+k+r':\s+(\d+) kB',memory,re.M)[1]) for k in ['VmHWM','VmRSS','VmSwap']}})
pairs=[]
for repeat in [1,2]:
 idle=next(r for r in cases if r['repeat']==repeat and r['policy']=='idle_gate');parallel=next(r for r in cases if r['repeat']==repeat and r['policy']=='low_priority_parallel')
 pairs.append({'repeat':repeat,'processed_delta_parallel_minus_idle':parallel['processed']-idle['processed'],'count_delta':parallel['count_down']-idle['count_down'],
  'late_delta':parallel['late']-idle['late'],'FPS_delta':parallel['FPS']-idle['FPS'],'P95_release_to_frontend_ms_delta':parallel['P95_release_to_frontend_ms']-idle['P95_release_to_frontend_ms'],
  'max_backend_enqueue_to_result_ms_delta':parallel['max_enqueue_to_result_ms']-idle['max_enqueue_to_result_ms']})
record={'status':'SERIAL_RECOVERED_POLICY_TRADEOFF_COMPONENTS39_ACTUAL_JOBS_AND_PAIRED_ORDER_DIFFERENCES_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'cases':cases,'paired_order_comparisons':pairs,'original_full_archive_downloaded':False,'raw_photo_input_numeric_verification':recovery['status'],
 'new_forwards':0,'global_default_changed':False,'whole_goal_complete':False}
f=ROOT/'results/summary_recovered.json';assert not f.exists();f.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'run':r['run'],'FPS':r['FPS'],'count':r['count_down'],'max_backend_s':r['max_enqueue_to_result_ms']/1000,'positive_CPU_tick_windows':r['CPU_windows_positive_ticks']} for r in cases]))
