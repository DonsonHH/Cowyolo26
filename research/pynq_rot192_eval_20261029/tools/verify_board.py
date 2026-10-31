from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,hashlib,tarfile,gzip,importlib.util,sys,ast
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;Q=ROOT/'delivery/results/quality_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
meta=load(ROOT/'evidence/board_transfer.json');archive=ROOT/'board_results_delivery.tar.gz'
assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
OUT=ROOT/'board_delivery';OUT.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==meta['members']
 for m in members:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  target=(OUT/m.name).resolve();assert target.is_relative_to(OUT.resolve()) and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
manifest=load(OUT/'board_result_manifest.json');assert len(manifest)==meta['manifest_files']
for row in manifest:
 file=OUT/row['file'];assert file.stat().st_size==row['bytes'] and sha(file)==row['sha256']
for a,b in [('board_protocol_v2.json','protocol/board_video_v2.json'),('board_video_v2.py','tools/board_video_v2.py'),('frozen_input.py','tools/frozen_input.py')]:assert sha(OUT/a)==sha(ROOT/b)
p=load(OUT/'board_protocol_v2.json');s=load(OUT/'results_v2/record.json');terminal=load(OUT/'results_v2/terminal.json');final=load(OUT/'final_state.json')
assert s['status']==terminal['status']=='ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE'
assert terminal['record_sha256']==sha(OUT/'results_v2/record.json') and s['protocol_sha256']==sha(ROOT/'protocol/board_video_v2.json')
assert s['actual_video_model_forwards']==terminal['actual_video_model_forwards']==len(s['rows'])==2654 and len(s['warmups'])==2
assert final['proc_exists'] is False and terminal['close_error'] is None and final['PID']==terminal['PID']==s['PID']==26302
assert s['PL_after_sha256']==final['PL_bit_sha256']==p['O8_bit_sha256'] and s['hardware_status']['error']=='0x0'
assert s['model_checkpoint_sha256']==p['checkpoint_sha256']=='7b01cead4841f17d561f2a6bd768f9b229f1b3bd142818d8302135d3c69ffd45'
spec=importlib.util.spec_from_file_location('independent_board_temporal_runs',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
scanner=importlib.util.module_from_spec(spec);sys.modules[spec.name]=scanner;spec.loader.exec_module(scanner)
tree=ast.parse((ROOT/'tools/verify_quality.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='event_optimum')
context={};exec(compile(ast.Module(body=[node],type_ignores=[]),'<independent_event_matching>','exec'),context)
counts=[];raw_ticks=boxes=ticks=paths=anchors=0;inverse_error=0.;formal=[];qdq_different_raw_rows=0
inputs=load(Q/'board_input_manifest.json')
for video in p['videos']:
 folder=OUT/'results_v2'/video['name'];records=gz(folder/'raw_predictions.json.gz');raw=np.load(folder/'all_raw.npy')
 expected_frames=list(range(0,video['decode_end_exclusive'],video['inference_stride']))
 assert [r['frame0'] for r in records]==expected_frames and raw.shape==(len(records),300,6) and raw.dtype==np.float32 and np.isfinite(raw).all() and np.all(raw[:,:,5]==0)
 with np.load(Q/(video['name']+'_all_raw.npz')) as arrays:
  for a,b in zip(raw,arrays['QDQ']):qdq_different_raw_rows+=a.tobytes()!=b.tobytes()
 raw_ticks+=len(records);x0,y0,x1,y1=video['detection_crop_xyxy']
 inverse=np.array([[0,1,x0],[-1,0,y1],[0,0,1]],float) if video['orientation']=='clockwise90' else np.array([[1,0,x0],[0,1,y0],[0,0,1]],float)
 byframe={r['frame0']:i for i,r in enumerate(records)}
 for row,array in zip(records,raw):
  assert row['time_s']==row['frame0']/video['fps']
  selected=array[array[:,4]>=.2];assert len(selected)==len(row['predictions'])
  for prediction,value in zip(row['predictions'],selected):
   assert prediction['confidence']==float(value[4]) and prediction['class']==0
   a,b,c,d=prediction['crop_oriented_xyxy'];corners=np.array([[a,b,1],[c,b,1],[c,d,1],[a,d,1]])@inverse.T
   expected=[*corners[:,:2].min(0),*corners[:,:2].max(0)]
   error=max(abs(a-b) for a,b in zip(expected,prediction['xyxy']));inverse_error=max(inverse_error,error);assert error<1e-8;boxes+=1
 for row in [r for r in inputs if r['scene']==video['name'] and r['anchor']]:
  with np.load(Q/'native_integer_anchors'/(video['name']+'_f'+str(row['frame0'])+'.npz')) as expected:
   observed=raw[byframe[row['frame0']]][None]
   assert observed.tobytes()==expected['native_integer_raw'].tobytes()
   assert hashlib.sha256(expected['input'].tobytes()).hexdigest()==row['input_tensor_sha256'];anchors+=1
 for stride in video['counter_replay_strides']:
  trace=gz(folder/('stride'+str(stride)+'_counter_trace.json.gz'));obs=trace['observations']
  assert [r['frame0'] for r in obs]==list(range(0,video['decode_end_exclusive'],stride));ticks+=len(obs)
  bypost=defaultdict(list)
  for r in trace['post_tracker']:bypost[r['frame0']].append(r)
  for row in obs:
   positions={};active=set()
   for post in bypost[row['frame0']]:
    if post['track_id'] is None:continue
    tid=post['track_id'];active.add(tid);a,b,c,d=post['xyxy'];cx=(a+c)/(2*video['width']);cy=(b+d)/(2*video['height'])
    if video['perpendicular_ROI'][0]<(cx if video['axis']=='y' else cy)<video['perpendicular_ROI'][1]:positions[str(tid)]=cy if video['axis']=='y' else cx
   assert positions==row['confirmed_positions'] and sorted(active)==row['confirmed_IDs']
  for kind,admit in [('confirmed_only_events',False),('handoff_events',True)]:
   events,accepted=scanner.batch_events(obs,admit);assert events==trace[kind];paths+=1
   events=[e for e in events if video['scope_start_frame0']<=e['frame0']<video['scope_end_exclusive']]
   metric=next(x for scene in s['scenes'] if scene['scene']==video['name'] for x in scene['metrics'] if x['stride']==stride and x['counter']==kind)
   assert metric['events']==events and metric['down']==sum(e['direction']=='A->B' for e in events) and metric['up']==sum(e['direction']=='B->A' for e in events)
   counts.append({'scene':video['name'],**metric})
   if video['name']=='toros':
    best,winners=context['event_optimum'](video['reference_events'],events)
    matched=winners[0];tp=sum(video['reference_events'][a]['direction']==events[b]['direction'] for a,b in matched)
    formal.append({'stride':stride,'counter':kind,'TP':tp,'FP':len(events)-tp,'FN':6-tp,'assignment_optima':len(winners)})
assert raw_ticks==2654 and ticks==2734 and paths==6 and anchors==8
stage_names=['PNG_read_ms','preprocess_ms','input_hash_check_ms','tensor_to_raw_ms','decode_restore_ms','tracker_counter_ms','raw_memorymap_and_row_save_ms']
for row in s['rows']:assert abs(sum(row[k] for k in stage_names)-row['PNG_to_counter_with_raw_save_ms'])<1e-8
timings={}
for key in stage_names+['PNG_to_counter_with_raw_save_ms']:
 values=np.asarray([r[key] for r in s['rows']]);timings[key]={'mean':float(values.mean()),'p95':float(np.quantile(values,.95)),'max':float(values.max())}
for scene in s['scenes']:assert scene['unpaced_replay_FPS']==scene['input_images']/scene['PNG_to_counter_replay_wall_s_including_raw_flush']
forensic=load(OUT/'failed_v1_forensic.json');assert forensic['first_failed_script_forwards']==0 and forensic['old_PID_absent']
record={'status':'ALL2654_ACTUAL_FPGA_ARM_RAW_OUTPUTS6_COUNTER_PATHS_AND8_HELDOUT_INPUT_VECTORS_INDEPENDENTLY_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_video_model_forwards':2654,'actual_warmups':2,'raw_boxes_inverse_verified':boxes,
 'maximum_inverse_error':inverse_error,'counter_observation_ticks':ticks,'independent_counter_paths':paths,
 'actual8_video_anchor_CPU_integer_raw_bytes_exact':True,'QDQ_ORT_vs_actual_O8_different_raw_frame_rows':qdq_different_raw_rows,
 'source_counts':counts,'publisher_event_scores':formal,'timing_ms':timings,
 'frame_times_over200ms':sum(r['PNG_to_counter_with_raw_save_ms']>200 for r in s['rows']),
 'scene_wall_replay':[{'scene':r['scene'],'images':r['input_images'],'wall_s':r['PNG_to_counter_replay_wall_s_including_raw_flush'],'unpaced_FPS':r['unpaced_replay_FPS']} for r in s['scenes']],
 'raw_source_and_trace_files_archived':True,'old_failed_board_process_actual_forwards':0,'failed_evidence_preserved':True,
 'live_camera_or_periodic_scheduler_tested':False,'simultaneous_identity_tested':False,'stable_joint5FPS_proven':False,'whole_goal_complete':False,
 'archive_sha256':sha(archive),'archive_members':len(members),'manifest_hashes':len(manifest)}
file=ROOT/'results/independent_board_verification.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='source_counts'}))
