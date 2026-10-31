from pathlib import Path
import os,sys,time,json,hashlib,traceback,fcntl
os.environ['XILINX_XRT']='/usr';os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
import numpy as np
from PIL import Image
from pynq import PL
LEGACY=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029');sys.path.insert(0,str(LEGACY))
from ncnn_encoder_v3 import Encoder,body_tensor
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
 q=p.with_suffix(p.suffix+'.partial');q.write_text(json.dumps(v,indent=2)+'\n');q.replace(p)

def main():
 p=load(ROOT/'run_protocol.json');out=ROOT/'results';out.mkdir(exist_ok=False)
 state={'status':'RUNNING','PID':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'protocol_sha256':sha(ROOT/'run_protocol.json'),
  'measured_forwards':0,'warmup_forwards':0,'attempted_network_calls':0,'models':{},'new_training_updates':0,'new_PL_forwards':0,'PL_programming':False,'whole_goal_complete':False}
 encoder=lock=None;failure=None
 try:
  for row in p['payload_files']:assert sha(ROOT/row['file'])==row['sha256']
  for row in p['runtime_files']:assert sha(row['file'])==row['sha256']
  assert sha(PL.bitfile_name)==p['O8_bit_sha256']
  lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with np.load(ROOT/'CPU_reference_features.npz')as archive:reference={k:archive[k].copy()for k in archive.files}
  CPUrows=load(ROOT/'CPU_fixed_decisions.json');assert len(CPUrows)==480
  inputs=[];prep=[];anchors=out/'input_anchors';anchors.mkdir()
  for row in p['images']:
   path=ROOT/row['payload_image'];assert sha(path)==row['image_SHA256'];start=time.monotonic_ns()
   with Image.open(path)as im:im.load();x=body_tensor(im)
   elapsed=(time.monotonic_ns()-start)/1e6;digest=hashlib.sha256(x.tobytes()).hexdigest();assert digest==row['input_tensor_SHA256']
   inputs.append(x);prep.append({'index':row['index'],'input_tensor_sha256':digest,'JPEG_read_decode_preprocess_ms':elapsed})
   if row['index']in p['input_anchor_indices']:np.savez_compressed(anchors/('index'+str(row['index'])+'.npz'),input=x)
  write(out/'preprocessing_gate.json',{'status':'ALL90_JPEG_AND_TENSOR_HASHES_MATCH_BEFORE_ENCODER_CREATE_OR_FORWARD','rows':prep,'model_forwards':0,'JPEG_integrity_read_precedes_and_is_outside_timing':True})
  features={}
  for spec in p['models']:
   name=spec['name'];folder=out/name;folder.mkdir();model={'name':name,'encoder_directory':spec['encoder_directory'],'measured_forwards':0,'warmups':[],'rows':[]}
   state['models'][name]=model;encoder=Encoder(Path(spec['encoder_directory']),threads=1)
   for index in range(2):
    state['attempted_network_calls']+=1;start=time.monotonic_ns();encoder.run(inputs[0]);state['warmup_forwards']+=1;model['warmups'].append({'index':index,'network_ms':(time.monotonic_ns()-start)/1e6})
   model['thread_affinities_after_warmups']={q.name:sorted(os.sched_getaffinity(int(q.name)))for q in Path('/proc/self/task').iterdir()}
   raws=[];norms=[]
   for index,x in enumerate(inputs):
    state['attempted_network_calls']+=1;start=time.monotonic_ns();raw=encoder.run(x);ms=(time.monotonic_ns()-start)/1e6;state['measured_forwards']+=1;model['measured_forwards']+=1
    f=raw/np.linalg.norm(raw);ref=reference[name+'_normalized'][index];error=float(np.max(np.abs(f-ref)));dot=1-float(f.astype(float)@ref.astype(float))
    record={'index':index,'input_tensor_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'raw_feature_sha256':hashlib.sha256(raw.tobytes()).hexdigest(),'network_ms':ms,'normalized_Torch_error':error,'one_minus_dot':dot,'numeric_pass':error<=1e-4 and dot<=1e-5}
    model['rows'].append(record);raws.append(raw);norms.append(f)
    if(index+1)%15==0:write(out/'progress.json',{'status':'RUNNING','PID':os.getpid(),'model':name,'images_in_model':index+1,'measured_forwards':state['measured_forwards'],'warmup_forwards':state['warmup_forwards']});print(json.dumps(record),flush=True)
   raws=np.stack(raws);norms=np.stack(norms);np.savez_compressed(folder/'actual_features.npz',raw=raws,normalized=norms);features[name]=norms
   times=[r['network_ms']for r in model['rows']];model.update({'network_mean_ms':float(np.mean(times)),'network_P95_ms':float(np.quantile(times,.95)),'numeric_failed_images':sum(not r['numeric_pass']for r in model['rows']),'maximum_normalized_feature_error':max(r['normalized_Torch_error']for r in model['rows'])})
   write(folder/'record.json',model);encoder.close();encoder=None
  gi=[r['index']for r in p['images']if r['purpose']=='gallery'];qi=[r['index']for r in p['images']if r['purpose']!='gallery'];labels=sorted(p['registered_IDs']);retrieval=[];all_decisions=[];outcomes=[]
  for name,values in features.items():
   pair=values[qi].astype(float)@values[gi].astype(float).T;scores=np.stack([pair[:,[j for j,i in enumerate(gi)if p['images'][i]['publisher_identity']==ID]].max(axis=1)for ID in labels],axis=1)
   for position,index in enumerate(qi):
    cpu=next(r for r in CPUrows if r['model']==name and r['policy']=='primary_cal10_fold0'and r['source_index']==index)
    order=sorted(range(10),key=lambda j:(-scores[position,j],labels[j]));rank=[labels[j]for j in order];cpu_rank=sorted(labels,key=lambda ID:(-cpu['all_ID_scores'][ID],ID))
    delta=max(abs(float(scores[position,j])-cpu['all_ID_scores'][ID])for j,ID in enumerate(labels))
    retrieval.append({'model':name,'source_index':index,'predicted_id':rank[0],'top5_IDs':rank[:5],'all_ID_scores':{ID:float(value)for ID,value in zip(labels,scores[position])},'CPU_predicted_id':cpu['predicted_id'],'CPU_top5_IDs':cpu['top5_IDs'],'same_Top1':rank[0]==cpu['predicted_id'],'same_Top5_order':rank[:5]==cpu['top5_IDs'],'same_full_ranking':rank==cpu_rank,'maximum_registered_score_difference':delta})
   for policy,tau in p['threshold_policies'][name].items():
    cases=[]
    for r in[r for r in retrieval if r['model']==name]:
     index=r['source_index'];meta=p['images'][index];cpu=next(x for x in CPUrows if x['model']==name and x['policy']==policy and x['source_index']==index);score=r['all_ID_scores'][r['predicted_id']];accept=score>=tau
     actual={'model':name,'policy':policy,'source_index':index,'identity':meta['publisher_identity'],'is_known':meta['is_known'],'predicted_id':r['predicted_id'],'score':score,'top5_IDs':r['top5_IDs'],'accepted':accept,'threshold':tau,'CPU_predicted_id':cpu['predicted_id'],'CPU_accepted':cpu['accepted'],'same_CPU_Top1_and_accept':r['predicted_id']==cpu['predicted_id']and accept==cpu['accepted']};cases.append(actual)
    known=[r for r in cases if r['is_known']];unknown=[r for r in cases if not r['is_known']]
    outcomes.append({'model':name,'policy':policy,'known_queries':30,'unknown_queries':30,'known_Top1':sum(r['identity']==r['predicted_id']for r in known),'known_Top5':sum(r['identity']in r['top5_IDs']for r in known),'C':sum(r['accepted']and r['identity']==r['predicted_id']for r in known),'W':sum(r['accepted']and r['identity']!=r['predicted_id']for r in known),'U':sum(not r['accepted']for r in known),'unknown_FA':sum(r['accepted']for r in unknown)});all_decisions.extend(cases)
  write(out/'all_retrieval.json',retrieval);write(out/'all_decisions.json',all_decisions);write(out/'all_outcomes.json',outcomes)
  numeric_errors=sum(model['numeric_failed_images']for model in state['models'].values());top1_changes=sum(not r['same_Top1']for r in retrieval);top5_changes=sum(not r['same_Top5_order']for r in retrieval);decision_changes=sum(not r['same_CPU_Top1_and_accept']for r in all_decisions)
  assert state['measured_forwards']==180 and state['warmup_forwards']==4 and state['attempted_network_calls']==184 and len(retrieval)==120 and len(all_decisions)==480 and'torch'not in sys.modules
  state.update({'status':'BOTH90_ENCODERS180_ARM_FEATURES_AND480_FIXED_DECISIONS_PASS'if not(numeric_errors or top1_changes or top5_changes or decision_changes)else'ALL180_FEATURES_SAVED_BUT_NUMERIC_OR_RANK_OR_DECISION_GATE_FAILED',
   'numeric_failed_images':numeric_errors,'Top1_changes':top1_changes,'Top5_order_changes':top5_changes,'full_ranking_changes':sum(not r['same_full_ranking']for r in retrieval),'fixed_decision_changes':decision_changes,'primary_outcomes':[r for r in outcomes if r['policy']=='primary_cal10_fold0'],'Torch_imported':False,'PL_after':PL.bitfile_name,'PL_after_SHA256':sha(PL.bitfile_name)})
 except BaseException as error:failure=error;state.update({'status':'FAILED_EXCEPTION','error':repr(error),'traceback':traceback.format_exc()})
 finally:
  if encoder:
   try:encoder.close()
   except BaseException as error:state['encoder_close_error']=repr(error);state['status']='ENCODER_CLOSE_FAILED'
  if lock:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
  write(out/'record.json',state);os.sync();write(out/'terminal.json',{'status':state['status'],'PID':os.getpid(),'measured_forwards':state['measured_forwards'],'warmup_forwards':state['warmup_forwards'],'record_sha256':sha(out/'record.json')})
  print(json.dumps({k:v for k,v in state.items()if k!='models'}),flush=True)
 if failure or state['status']!='BOTH90_ENCODERS180_ARM_FEATURES_AND480_FIXED_DECISIONS_PASS':raise SystemExit(1)

if __name__=='__main__':main()
