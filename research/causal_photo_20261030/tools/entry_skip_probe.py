"""Read-only counter-only deletion probes selected after observed periodic failures."""
from pathlib import Path
from datetime import datetime,timezone
import json,gzip,importlib.util,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
spec=importlib.util.spec_from_file_location('causal_skip_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py');scanner=importlib.util.module_from_spec(spec);sys.modules[spec.name]=scanner;spec.loader.exec_module(scanner)
source=PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/stride5_counter_trace.json.gz';baseline=gz(source);records=[]
for label,deleted in [('no_delete',[]),('delete9515_only',[9515]),('delete10440_only',[10440]),('actual_foreground_repeat2_skips',[9515,10440]),('actual_current_repeat2_skips',[r['source_frame0'] for r in load(ROOT/'delivery/results/r2_current_frame/skipped_slots.json')])]:
 observations=[o for o in baseline['observations'] if o['frame0'] not in deleted];events,accepted=scanner.batch_events(observations,True);events=[e for e in events if 8912<=e['frame0']<=10873]
 records.append({'diagnostic':label,'deleted_observation_frames':deleted,'counter_only_count':len(events),'events':events,'accepted_history':accepted})
assert [r['counter_only_count'] for r in records]==[10,9,10,9,9]
details=[]
for name,tid in [('r2_foreground_only',21),('r2_current_frame',5)]:
 trace=gz(ROOT/'delivery/results'/name/'counter_trace.json.gz');first=next((i for i,o in enumerate(trace['observations']) if tid in o['confirmed_IDs']),None);assert first is not None
 previous=trace['observations'][first-1];admitted=previous['tentative_positions'].get(str(tid));samples={i:o['confirmed_positions'][str(tid)] for i,o in enumerate(trace['observations']) if str(tid) in o['confirmed_positions']}
 if admitted is not None:samples[first-1]=admitted
 runs=[];current=[];prior=None
 for i,pos in sorted(samples.items()):
  if pos>=.4:
   if current:runs.append(current);current=[]
   prior=i;continue
  if prior is not None and i!=prior+1:
   if current:runs.append(current);current=[]
  current.append({'frame0':trace['observations'][i]['frame0'],'position':pos,'admitted_tentative':i==first-1});prior=i
 if current:runs.append(current)
 details.append({'run':name,'temporary_track_id':tid,'first_confirmed_frame0':trace['observations'][first]['frame0'],'all_A_region_runs_including_legal_prior':runs,'longest_A_run':max(map(len,runs),default=0),'accepted_prior_source_frame0':previous['frame0'] if admitted is not None else None,'event_present':any(e['track_id']==tid for e in trace['handoff_events'])})
assert [r['longest_A_run'] for r in details]==[2,1]
result={'status':'OBSERVED9_COUNT_ENTRY_LOSS_AND_COUNTER_ONLY_DELETION_DIAGNOSIS_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'source_trace_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'counter_only_probes':records,'actual_periodic_cases':details,
 'posthoc_development_diagnostic_not_independent_test':True,'counter_only_deletion_does_not_rerun_tracker':True,'new_model_or_board_forwards':0,'threshold_or_count_rules_changed':False,'whole_goal_complete':False}
f=ROOT/'results/entry_skip_probe.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'counter_only_counts':[r['counter_only_count'] for r in records],'actual_longest_A_runs':[r['longest_A_run'] for r in details],'production_changed':False}))
