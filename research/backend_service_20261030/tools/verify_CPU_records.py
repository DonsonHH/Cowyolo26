from pathlib import Path
from datetime import datetime,timezone
import json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
p=load(ROOT/'protocol/run_v1.json');v=load(ROOT/'results/independent_verification.json');records=[];all_rows=0
for run in p['runs']:
 folder=ROOT/'delivery/results'/run['run'];rows=load(folder/'timing_rows.json');worker=load(folder/'background/record.json');pid=worker['PID'];total=positive=0;hz_set=set();starts=set()
 assert worker['actual_nice']==10 and worker['actual_CPU_affinity']==[0,1] and worker['execution_policy']==run['policy']
 for row in rows:
  a=row['worker_CPU_before'];b=row['worker_CPU_after'];assert a['PID']==b['PID']==pid and a['nice']==b['nice']==10
  assert a['starttime_ticks']==b['starttime_ticks'];starts.add(a['starttime_ticks'])
  assert a['clock_ticks_per_second']==b['clock_ticks_per_second']>0;hz_set.add(a['clock_ticks_per_second'])
  assert a['snapshot_started_monotonic_ns']<=a['snapshot_finished_monotonic_ns']<=row['started_monotonic_ns']<=b['snapshot_started_monotonic_ns']<=b['snapshot_finished_monotonic_ns']<=row['completed_monotonic_ns']
  assert a['total_CPU_ticks']==a['utime_ticks']+a['stime_ticks'] and b['total_CPU_ticks']==b['utime_ticks']+b['stime_ticks']
  delta=b['total_CPU_ticks']-a['total_CPU_ticks'];assert delta==row['worker_CPU_tick_delta']>=0
  if run['policy']=='idle_gate':assert a['state']==b['state']=='T'
  total+=delta;positive+=delta>0;all_rows+=1
 assert len(hz_set)==len(starts)==1;hz=next(iter(hz_set))
 records.append({'run':run['run'],'policy':run['policy'],'frame_windows':len(rows),'windows_with_positive_child_CPU_ticks':positive,
  'sum_child_CPU_ticks_inside_boundary_windows':total,'clock_ticks_per_second':hz,'approximate_CPU_ms_inside_boundary_windows':total*1000/hz,
  'actual_worker_nice':worker['actual_nice'],'actual_worker_CPU_affinity':worker['actual_CPU_affinity'],
  'CPU_tick_quantization_and_boundary_overhead_preclude_layer_level_overlap':True})
assert all_rows==v['actual_O8_timed_forwards']
result={'status':'ALL_FRAME_CHILD_CPU_TICK_WINDOWS_POLICY_NICE_AND_SNAPSHOT_BOUNDARIES_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),'frame_windows':all_rows,'runs':records,
 'source':'Linux child process utime+stime, clock ticks; not per-layer scheduler trace','new_forwards':0,'whole_goal_complete':False}
f=ROOT/'results/CPU_independent_verification.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
