from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,gzip,hashlib,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
p=load(ROOT/'protocol/run_v1.json');v=load(ROOT/'results/independent_verification.json')
reference=gz(PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/stride5_counter_trace.json.gz')
revents=[e for e in reference['handoff_events'] if e['frame0']>=8912];out=[]
for run in p['runs']:
 folder=ROOT/'delivery/results'/run['run'];trace=gz(folder/'counter_trace.json.gz');rows=load(folder/'timing_rows.json');skips=load(folder/'skipped_slots.json');summary=next(r for r in v['cases'] if r['run']==run['run'])
 events=[e for e in trace['handoff_events'] if e['frame0']>=8912]
 # Diagnostic same-raw history keys, not individual-animal ground truth.
 missing=[e for e in revents if not any(a['track_id']==e['track_id'] and a['direction']==e['direction'] for a in events)]
 extra=[e for e in events if not any(a['track_id']==e['track_id'] and a['direction']==e['direction'] for a in revents)]
 metrics={}
 for key in ['model_ms','after_model_to_count_ms','JPEG_frontend_read_ms','selector_ms','processing_ms','release_to_count_ms']:
  data=np.asarray([r[key] for r in rows]);metrics[key]={'mean':float(data.mean()),'P50':float(np.quantile(data,.5)),'P95':float(np.quantile(data,.95)),'P99':float(np.quantile(data,.99)),'max':float(data.max())}
 status=next(r for r in load(ROOT/'delivery/results/record.json')['cases'] if r['run']==run['run'])['cumulative_parent_proc_status']
 memory={key:int(re.search(r'^'+key+r':\s+(\d+) kB',status,re.M)[1]) for key in ['VmHWM','VmRSS','VmSwap']}
 camera={r['frame0']:r for r in load(PROJECT/'pynq_periodic_joint_20261030/camera_delivery/manifest.json')}
 ring=[];transient_peak=0
 if run['policy']=='causal_ring':
  for row in rows:
   transient_peak=max(transient_peak,sum(camera[f]['bytes'] for f in [*ring,row['frame0']]))
   ring.append(row['frame0']);ring=[f for f in ring if row['frame0']-f<=25]
   assert len(ring)<=6
 neighborhoods=[]
 for event in missing:
  frame=event['frame0'];native=[r for r in reference['observations'] if frame-75<=r['frame0']<=frame+25]
  actual=[r for r in trace['observations'] if frame-75<=r['frame0']<=frame+25]
  neighborhoods.append({'cached_default_event':event,'prior_full_video_observations':native,'actual_periodic_observations':actual,'skipped_nearby_slots':[s for s in skips if frame-75<=s['source_frame0']<=frame+25]})
 out.append({'run':run['run'],'policy':run['policy'],'frames':len(rows),'skips':len(skips),'deadline_misses':summary['deadline_misses'],'actual_down_count':len(events),
  'metrics_ms':metrics,'cumulative_parent_status_kB':memory,'ring_compressed_payload_bytes':summary['ring_peak_compressed_bytes'],
  'transient_read_before_expire_JPEG_payload_peak_bytes':transient_peak,
  'missing_cached_temporary_track_events':missing,'extra_cached_temporary_track_events':extra,'missing_event_neighborhoods':neighborhoods,
  'skips_by_hundred_source_frame':dict(Counter((s['source_frame0']//100)*100 for s in skips)),
  'timing_components_are_observational_not_isolated_causal_IO_proof':True,'RSS_is_cumulative_parent_only_not_whole_system':True})
f=ROOT/'results/timing_and_event_diagnosis.json';assert not f.exists();f.write_text(json.dumps({'status':'ALL_SIX_RUN_COMPONENTS_AND_DEVELOPMENT_EVENT_DIFFERENCES_RECONSTRUCTED','created_UTC':datetime.now(timezone.utc).isoformat(),'runs':out,'permanent_ID_or_independent_GT_used':False,'new_forwards':0,'whole_goal_complete':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'run':r['run'],'count':r['actual_down_count'],'missing_cached_temp_tracks':[e['track_id'] for e in r['missing_cached_temporary_track_events']],'mean_JPEG_read_ms':r['metrics_ms']['JPEG_frontend_read_ms']['mean'],'mean_selector_ms':r['metrics_ms']['selector_ms']['mean']} for r in out]))
