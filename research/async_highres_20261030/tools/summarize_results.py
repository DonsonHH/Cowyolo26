from pathlib import Path
from datetime import datetime,timezone
import json,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
v=load(ROOT/'results/independent_verification.json');producer=load(ROOT/'results/producer_independent_verification.json');bystate={r['run']:r for r in producer['records']};out=[]
for case in v['cases']:
 run=case['run'];folder=ROOT/'delivery/results'/run;rows=load(folder/'timing_rows.json');pauses=load(folder/'worker_pause_intervals.json');packetrows=bystate[run]['packet_timing_rows']
 background=next(r for r in v['backgrounds'] if r['run']==run);prod=load(folder/'producer_record.json')
 metrics={}
 for field in ['model_ms','after_model_to_count_ms','processing_ms','release_to_count_ms','JPEG_frontend_read_ms','selector_ms']:
  values=[r[field] for r in rows];metrics[field]={'mean':float(np.mean(values)),'P50':float(np.quantile(values,.5)),'P95':float(np.quantile(values,.95)),'P99':float(np.quantile(values,.99)),'max':max(values)}
 for field in ['read_ms','verify_ms','foreground_wait_ms','model_IO_overlap_ms','release_to_received_ms']:
  values=[r[field] for r in packetrows];metrics['packet_'+field]={'mean':float(np.mean(values)),'P50':float(np.quantile(values,.5)),'P95':float(np.quantile(values,.95)),'P99':float(np.quantile(values,.99)),'max':max(values)}
 ack=[(r['pause_acknowledged_monotonic_ns']-r['pause_requested_monotonic_ns'])/1e6 for r in pauses]
 metrics['worker_pause_ack_ms']={'mean':float(np.mean(ack)),'P95':float(np.quantile(ack,.95)),'max':max(ack)}
 record=next(r for r in load(ROOT/'delivery/results/record.json')['cases'] if r['run']==run)['cumulative_parent_proc_status']
 memory={k:int(re.search(r'^'+k+r':\s+(\d+) kB',record,re.M)[1]) for k in ['VmHWM','VmRSS','VmSwap']}
 out.append({'run':run,'policy':case['case'],'repeat':case['repeat'],'processed':case['processed_frames'],'skipped':case['skipped_slots'],'late':case['deadline_misses'],'FPS':case['processed_per_second_over_offered_duration'],'source_down_count':case['source_down_count'],
  'metrics':metrics,'background':background,'producer_peak':{k:prod.get(k,0) for k in ['peak_retained_frames','peak_retained_payload_bytes','peak_transient_payload_bytes']},'cumulative_parent_memory_kB':memory,
  'received_packets_with_positive_model_IO_overlap':sum(r['model_IO_overlap_ms']>0 for r in packetrows)})
comparisons=[]
for repeat in [1,2]:
 a=next(r for r in out if r['repeat']==repeat and r['policy']=='serial_input');b=next(r for r in out if r['repeat']==repeat and r['policy']=='async_input')
 comparisons.append({'repeat':repeat,'serial_run':a['run'],'async_run':b['run'],'processed_difference_async_minus_serial':b['processed']-a['processed'],'FPS_difference':b['FPS']-a['FPS'],'deadline_misses_difference':b['late']-a['late'],
  'P95_release_to_count_ms_difference':b['metrics']['release_to_count_ms']['P95']-a['metrics']['release_to_count_ms']['P95'],'max_backend_completion_ms_difference':b['background']['max_enqueue_to_result_ms']-a['background']['max_enqueue_to_result_ms'],
  'same_count_does_not_establish_independent_accuracy':True})
summary={'status':'ALL4_RUN_COMPONENTS_PAIRED_ORDER_COMPARISONS_AND_MEMORY_SCOPE_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),'runs':out,'comparisons':comparisons,
 'repeats_are_independent_farm_sessions':False,'new_forwards':0,'global_default_replaced':False,'whole_goal_complete':False}
f=ROOT/'results/summary.json';assert not f.exists();f.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'run':r['run'],'FPS':r['FPS'],'count':r['source_down_count'],'late':r['late'],'mean_model_ms':r['metrics']['model_ms']['mean'],'mean_input_wait_ms':r['metrics']['JPEG_frontend_read_ms']['mean'],'mean_IO_model_overlap_ms':r['metrics']['packet_model_IO_overlap_ms']['mean'],'max_backend_s':r['background']['max_enqueue_to_result_ms']/1000} for r in out]))
