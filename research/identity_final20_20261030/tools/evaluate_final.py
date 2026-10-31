"""One fixed feature evaluation of the sealed20 ID component; no training or search."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,socket,sys,traceback,time
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
import numpy as np
from PIL import Image
import PIL,torch,torchvision
from torchvision.models import mobilenet_v3_small
from frozen_body_tensor import body_tensor

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')

assert os.environ.get('SLURM_JOB_ID')and socket.gethostname()!='mu01'
torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(26);torch.use_deterministic_algorithms(True)
p=load(ROOT/'protocol/run_v1.json');e=load(ROOT/'protocol/execution_v1.json')
assert sha(ROOT/'protocol/run_v1.json')==e['protocol_sha256']
for name,digest in e['files_sha256'].items():assert sha(ROOT/name)==digest
admission=load(ROOT/'results/pixel_admission.json');assert admission['status']=='ALL90_FIXED_FINAL_ID_CROPS_CRC_RGB_AND_NO_EXACT_PRIOR_PIXEL_OVERLAP_PASS'
assert torch.__version__==e['Torch_version']and PIL.__version__==e['Pillow_version']
out=ROOT/'results/evaluation';out.mkdir(exist_ok=False);anchors=out/'input_anchors';anchors.mkdir()
state={'status':'RUNNING','created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),
 'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'execution_sha256':sha(ROOT/'protocol/execution_v1.json'),'actual_model_image_forwards':0,'actual_network_calls':0,
 'new_training_updates':0,'new_board_forwards':0,'warmups':0,'whole_goal_complete':False,'versions':{'Torch':torch.__version__,'Pillow':PIL.__version__,'NumPy':np.__version__,'Torchvision':torchvision.__version__}}
counts={};active=None;timeline=[];input_hashes=[]
def hook(module,args):
 value=args[0];assert value.shape[1:]==(3,224,224)and value.device.type=='cpu'and value.dtype==torch.float32 and len(value)<=e['batch']
 state['actual_model_image_forwards']+=len(value);state['actual_network_calls']+=1;counts[active]+=len(value)

try:
 images=[];inputs=[]
 for index,(row,audit)in enumerate(zip(p['images'],admission['rows'])):
  path=ROOT/row['local_relative_file'];assert sha(path)==audit['sha256']
  with Image.open(path)as image:image.load();x=body_tensor(image)
  digest=hashlib.sha256(x.tobytes()).hexdigest();input_hashes.append({'index':index,'input_tensor_sha256':digest});inputs.append(x[0]);images.append(row)
  if index in e['tensor_anchor_indices']:np.savez_compressed(anchors/('index'+str(index)+'.npz'),input=x)
 assert len(inputs)==90;inputs=np.stack(inputs)
 save(out/'input_hashes.json',input_hashes);features={}
 for spec in e['models']:
  assert sha(spec['checkpoint'])==spec['checkpoint_sha256']
  full=mobilenet_v3_small(weights=None);encoder=torch.nn.Sequential(full.features,full.avgpool,torch.nn.Flatten()).eval()
  encoder.load_state_dict(torch.load(spec['checkpoint'],map_location='cpu',weights_only=True))
  for parameter in encoder.parameters():parameter.requires_grad_(False)
  active=spec['name'];counts[active]=0;handle=encoder.register_forward_pre_hook(hook);raw=[]
  for start in range(0,90,e['batch']):
   with torch.inference_mode():v=encoder(torch.from_numpy(inputs[start:start+e['batch']])).cpu().contiguous().numpy()
   assert v.shape==(min(e['batch'],90-start),576)and np.isfinite(v).all();raw.extend(v.copy())
  handle.remove();raw=np.stack(raw);normalized=raw/np.linalg.norm(raw,axis=1,keepdims=True);features[active]=normalized
  folder=out/active;folder.mkdir();np.savez_compressed(folder/'all_features.npz',raw=raw,normalized=normalized)
  timeline.append({'model':active,'images':counts[active],'cumulative_images':state['actual_model_image_forwards'],'completed_UTC':datetime.now(timezone.utc).isoformat(),'features_sha256':sha(folder/'all_features.npz')})
  print(json.dumps(timeline[-1]),flush=True);del encoder,full
 assert state['actual_model_image_forwards']==180 and state['actual_network_calls']==16 and all(v==90 for v in counts.values())
 gi=[i for i,r in enumerate(images)if r['purpose']=='gallery'];qi=[i for i,r in enumerate(images)if r['purpose']!='gallery'];labels=sorted(p['roles']['registered']);assert len(gi)==30 and len(qi)==60
 rng=np.random.default_rng(e['bootstrap_seed']);known_draws=rng.integers(0,10,size=(e['bootstrap_draws'],10));unknown_draws=rng.integers(0,10,size=(e['bootstrap_draws'],10))
 np.savez_compressed(out/'bootstrap_ID_indices.npz',known=known_draws,unknown=unknown_draws)
 outcomes=[];decisions=[];perid={};unthresholded={}
 for name,values in features.items():
  pair=values[qi].astype(float)@values[gi].astype(float).T
  scores=np.stack([pair[:,[j for j,i in enumerate(gi)if images[i]['publisher_identity']==label]].max(axis=1)for label in labels],axis=1)
  retrieval=[]
  for k,index in enumerate(qi):
   order=sorted(range(len(labels)),key=lambda j:(-scores[k,j],labels[j]));r=images[index]
   retrieval.append({'source_index':index,'identity':r['publisher_identity'],'is_known':r['is_known'],'predicted_id':labels[order[0]],'score':float(scores[k,order[0]]),'top5_IDs':[labels[j]for j in order[:5]],'all_ID_scores':{label:float(v)for label,v in zip(labels,scores[k])}})
  save(out/name/'retrieval_unthresholded.json',retrieval);unthresholded[name]=retrieval
  for policy,tau in e['threshold_policies'][name].items():
   selected=[{**r,'model':name,'policy':policy,'threshold':tau,'accepted':r['score']>=tau}for r in retrieval];known=[r for r in selected if r['is_known']];unknown=[r for r in selected if not r['is_known']]
   c=sum(r['accepted']and r['predicted_id']==r['identity']for r in known);w=sum(r['accepted']and r['predicted_id']!=r['identity']for r in known);u=sum(not r['accepted']for r in known);fa=sum(r['accepted']for r in unknown);assert c+w+u==len(known)==30 and len(unknown)==30
   summary={'model':name,'policy':policy,'threshold':tau,'known_queries':30,'unknown_queries':30,'C':c,'W':w,'U':u,'M':0,'unknown_FA':fa,'known_Top1':sum(r['predicted_id']==r['identity']for r in known),'known_Top5':sum(r['identity']in r['top5_IDs']for r in known),'accepted_wrong_fraction':(w+fa)/(c+w+fa)if c+w+fa else None}
   idvalues={}
   for metric,registered in[('Top1',True),('C',True),('W',True),('U',True),('FA',False)]:
    IDs=sorted(p['roles']['registered']if registered else p['roles']['unknown']);vv=[]
    for ID in IDs:
     rr=[r for r in selected if r['identity']==ID];assert len(rr)==3
     vv.append(sum((r['predicted_id']==ID)if metric=='Top1'else(r['accepted']and r['predicted_id']==ID)if metric=='C'else(r['accepted']and r['predicted_id']!=ID)if metric=='W'else(not r['accepted'])if metric=='U'else r['accepted']for r in rr)/3)
    a=np.array(vv);draws=known_draws if registered else unknown_draws;sample=a[draws].mean(axis=1);idvalues[metric]={'IDs':IDs,'rates':vv,'macro_mean':float(a.mean()),'percentile95':np.quantile(sample,[.025,.975]).tolist()}
   perid[name+':'+policy]=idvalues;outcomes.append(summary);decisions.extend(selected)
 paired=[]
 for policy in e['threshold_policies']['old_C']:
  for metric in['Top1','C','W','U','FA']:
   a=perid['old_C:'+policy][metric];b=perid['new_C_domain_seed26:'+policy][metric];assert a['IDs']==b['IDs'];delta=np.array(b['rates'])-np.array(a['rates']);draws=unknown_draws if metric=='FA'else known_draws
   paired.append({'policy':policy,'metric':metric,'IDs':a['IDs'],'new_minus_old_per_ID':delta.tolist(),'mean_difference':float(delta.mean()),'percentile95':np.quantile(delta[draws].mean(axis=1),[.025,.975]).tolist()})
 save(out/'all_outcomes.json',outcomes);save(out/'all_decisions.json',decisions);save(out/'per_ID_intervals.json',perid);save(out/'paired_ID_differences.json',paired)
 assert len(outcomes)==8 and len(decisions)==480 and len(paired)==20
 state.update({'status':'BOTH_FROZEN_ENCODERS90_FINAL_ID_IMAGES180_FORWARDS8_FIXED_POLICIES_AND20_PAIRED_ID_CONTRASTS_COMPLETE','model_image_counts':counts,'timeline':timeline,'outcomes':outcomes,'per_identity_interval_sets':8,'paired_ID_contrasts':20,'final20_ID_pixels_opened':True,'reservedMar05toMar11_pixels_opened':False,'new_default_model_or_threshold_adopted':False})
except BaseException as error:state.update({'status':'FAILED','error':repr(error),'traceback':traceback.format_exc()});raise
finally:save(out/'summary.json',state);print(json.dumps({k:v for k,v in state.items()if k!='outcomes'}),flush=True)
