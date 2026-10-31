from pathlib import Path
from datetime import datetime,timezone
import json,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
v=load(ROOT/'results/independent_verification.json');prod=load(ROOT/'results/producer_independent_verification.json');cpu=load(ROOT/'results/CPU_independent_verification.json');runs=[]
for case in v['cases']:
 folder=ROOT/'delivery/results'/case['run'];rows=load(folder/'timing_rows.json');packets=next(r['packet_timing_rows'] for r in prod['records'] if r['run']==case['run']);pauses=load(folder/'worker_pause_intervals.json');p=load(folder/'producer_record.json')
 metrics={}
 for key in ['model_ms','processing_ms','release_to_count_ms','after_model_to_count_ms','JPEG_frontend_read_ms','selector_ms']:
  values=[r[key] for r in rows];metrics[key]={'mean':float(np.mean(values)),'P50':float(np.quantile(values,.5)),'P95':float(np.quantile(values,.95)),'P99':float(np.quantile(values,.99)),'max':max(values)}
 for key in ['read_ms','verify_ms','model_IO_overlap_ms','foreground_wait_ms']:
  values=[r[key] for r in packets];metrics['packet_'+key]={'mean':float(np.mean(values)),'P95':float(np.quantile(values,.95)),'max':max(values)}
 ack=[(r['pause_acknowledged_monotonic_ns']-r['pause_requested_monotonic_ns'])/1e6 for r in pauses]
 metrics['pause_ack_ms']={'mean':float(np.mean(ack)),'P95':float(np.quantile(ack,.95)),'max':max(ack)} if ack else None
 memory=next(r for r in load(ROOT/'delivery/results/record.json')['cases'] if r['run']==case['run'])['cumulative_parent_proc_status']
 runs.append({'run':case['run'],'policy':case['case'],'repeat':case['repeat'],'processed':case['processed_frames'],'skipped':case['skipped_slots'],'late':case['deadline_misses'],'FPS':case['processed_per_second_over_offered_duration'],'count_down':case['source_down_count'],
  'background':next(r for r in v['backgrounds'] if r['run']==case['run']),'CPU_progress':next(r for r in cpu['runs'] if r['run']==case['run']),
  'metrics':metrics,'producer_peak':{k:p[k] for k in ['peak_retained_frames','peak_retained_payload_bytes','peak_transient_payload_bytes']},
  'cumulative_parent_memory_kB':{k:int(re.search(r'^'+k+r':\s+(\d+) kB',memory,re.M)[1]) for k in ['VmHWM','VmRSS','VmSwap']}})
pairs=[]
for repeat in [1,2]:
 a=next(r for r in runs if r['repeat']==repeat and r['policy']=='idle_gate');b=next(r for r in runs if r['repeat']==repeat and r['policy']=='low_priority_parallel')
 pairs.append({'repeat':repeat,'processed_delta_parallel_minus_idle':b['processed']-a['processed'],'FPS_delta':b['FPS']-a['FPS'],'late_delta':b['late']-a['late'],
  'count_delta':b['count_down']-a['count_down'],'max_backend_completion_ms_delta':b['background']['max_enqueue_to_result_ms']-a['background']['max_enqueue_to_result_ms']})
result={'status':'ALL_BACKEND_POLICY_RUNS_COMPONENTS_CPU_WINDOWS_AND_PAIRED_ORDER_DIFFERENCES_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),'runs':runs,'paired_order_comparisons':pairs,
 'same_source_repeats_not_independent_sessions':True,'same_actual_triggered_count_not_guaranteed_fixed_photo_workload':True,'new_forwards':0,'whole_goal_complete':False}
f=ROOT/'results/summary.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'run':r['run'],'FPS':r['FPS'],'count':r['count_down'],'late':r['late'],'max_backend_s':r['background']['max_enqueue_to_result_ms']/1000,'child_CPU_progress_tick_windows':r['CPU_progress']['windows_with_positive_child_CPU_ticks']} for r in runs]))
