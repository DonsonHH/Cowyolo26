from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def save(p,v):assert not p.exists();p.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]))
v=load(ROOT/'results/independent_verification.json');p=load(ROOT/'protocol/run_v1.json');jobs=load(ROOT/'results/actual_job_rows.json');pairs=[];unmatched=[]
for repeat in[1,2]:
 a=[r for r in jobs if r['repeat']==repeat and r['identity_model']=='old'];b=[r for r in jobs if r['repeat']==repeat and r['identity_model']=='new'];amap={json.dumps(r['event'],sort_keys=True):r for r in a};bmap={json.dumps(r['event'],sort_keys=True):r for r in b}
 for key in sorted(set(amap)|set(bmap)):
  if key not in amap or key not in bmap:unmatched.append({'repeat':repeat,'event':(amap.get(key)or bmap[key])['event'],'model':'old'if key in amap else'new'});continue
  old,new=amap[key],bmap[key];pairs.append({'repeat':repeat,'event':old['event'],'same_source_frame':old['source_frame0']==new['source_frame0'],'same_photo_sha256':old['photo_sha256']==new['photo_sha256'],'same_input_tensor_sha256':old['input_tensor_sha256']==new['input_tensor_sha256'],'old_source_frame0':old['source_frame0'],'new_source_frame0':new['source_frame0'],'old_candidate':old['predicted_id'],'new_candidate':new['predicted_id'],'old_accepted':old['accepted'],'new_accepted':new['accepted'],'new_minus_old_completion_ms':new['enqueue_to_result_ms']-old['enqueue_to_result_ms']})
components=[]
for spec,case in zip(p['runs'],v['cases']):
 folder=ROOT/'delivery/results'/spec['run'];rows=load(folder/'timing_rows.json');worker=load(folder/'background/record.json');rr=worker['jobs'];status=case['cumulative_parent_proc_status']if'cumulative_parent_proc_status'in case else load(ROOT/'delivery/results/record.json')['cases'][len(components)]['cumulative_parent_proc_status']
 memory={line.split(':',1)[0]:line.split(':',1)[1].strip()for line in status.splitlines()if line.startswith(('VmRSS:','VmHWM:','VmSwap:'))}
 one={'run':spec['run'],'identity_model':spec['identity_model'],'foreground_component_means_ms':{k:float(np.mean([r[k]for r in rows]))for k in['model_ms','after_model_to_count_ms','JPEG_frontend_read_ms','selector_ms']},'foreground_proc_memory':memory,
 'background_component_means_ms':{k:float(np.mean([r[k]for r in rr]))if rr else None for k in['queue_wait_ms','highres_JPEG_read_decode_and_hash_ms','runtime_native_crop_and_photo_save_ms','Pillow_preprocess_ms','actual_identity_network_ms','worker_process_CPU_ms','enqueue_to_result_ms']},
 'actual_jobs':len(rr),'accepted_predictions':sum(r['accepted']for r in rr),'secondary_threshold_accepted':sum(r['secondary_Cows_threshold_accepted']for r in rr)}
 components.append(one)
save(ROOT/'results/job_pairing.json',{'status':'LITERAL_EVENT_MATCHED_AND_UNMATCHED_ROWS_PRESERVED_NO_PHYSICAL_ID_MAPPING_ASSUMED','created_UTC':datetime.now(timezone.utc).isoformat(),'pairs':pairs,'unmatched':unmatched,'whole_goal_complete':False})
save(ROOT/'results/component_timings.json',{'status':'TIMING_COMPONENTS_AND_PROCESS_MEMORY_DERIVED_WITHOUT_RETROACTIVE_OVERHEAD_SUBTRACTION','runs':components,'new_model_forwards':0})
print(json.dumps({'literal_event_pairs':len(pairs),'unmatched_job_rows':len(unmatched),'same_photo_pairs':sum(r['same_photo_sha256']for r in pairs)}))
