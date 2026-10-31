"""Convert fixed body encoder, then compare all132 existing image embeddings."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,sys,socket,time,subprocess
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import numpy as np,torch,ncnn,pnnx
from PIL import Image
from torchvision.models import mobilenet_v3_small
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'input'))
from training_primitives import BodyTransform
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
 torch.set_num_threads(4);p=load(ROOT/'protocol/encoder_v1.json');e=load(ROOT/'protocol/execution_v2.json')
 assert e['script_sha256']==sha(__file__) and e['protocol_sha256']==sha(ROOT/'protocol/encoder_v1.json')
 assert sha(ROOT/'input/images.json')==p['image_manifest_sha256'] and sha(ROOT/'input/training_primitives.py')==p['input_module_sha256']
 assert sha(ROOT/'input/prior_embeddings.npz')==p['prior_embedding_sha256']
 checkpoint=Path(p['encoder_condition']['checkpoint']);assert sha(checkpoint)==p['encoder_condition']['checkpoint_sha256']
 out=ROOT/'results/export_v2';out.mkdir(parents=True,exist_ok=False);base=mobilenet_v3_small(weights=None)
 encoder=torch.nn.Sequential(base.features,base.avgpool,torch.nn.Flatten()).eval();encoder.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
 for parameter in encoder.parameters():parameter.requires_grad_(False)
 images=load(ROOT/'input/images.json');transform=BodyTransform();first=next(iter(images.values()))[0]
 with Image.open(first['path']) as image:probe=transform(image).unsqueeze(0).contiguous()
 # NCNN files were produced before the wrapper tried to import invalid numeric Python attribute names.
 import shutil
 old=ROOT/'results/export';reuse=[]
 for name in ['encoder.pt','encoder.ncnn.param','encoder.ncnn.bin']:
  original=old/name;assert original.is_file();shutil.copyfile(original,out/name)
  reuse.append({'file':name,'sha256':sha(original),'bytes':original.stat().st_size})
 save(out/'converted_asset_reuse.json',{'failed_job':'130569','assets':reuse,'conversion_repeated':False,
  'old_failure':'GeneratedPNNXPythonhasnumericself.0_*attribute;NCNNparamandbinwerealreadywritten;do not execute generatedPython.',
  'measured_real_image_forwards_in_old_failed_job':0,'export_trace_probes_in_old_job_not_claimed_zero':True})
 assert (out/'encoder.ncnn.param').exists() and (out/'encoder.ncnn.bin').exists()
 lines=(out/'encoder.ncnn.param').read_text().splitlines();assert lines[0].strip()=='7767517'
 operators=sorted({line.split()[0] for line in lines[2:] if line.strip()})
 net=ncnn.Net();net.opt.num_threads=4
 net.opt.use_fp16_storage=False;net.opt.use_fp16_packed=False;net.opt.use_fp16_arithmetic=False;net.opt.use_bf16_storage=False
 assert net.load_param(str(out/'encoder.ncnn.param'))==0 and net.load_model(str(out/'encoder.ncnn.bin'))==0
 features={};comparisons=[];records=[];counts={'TorchCPU':0,'ncnnCPU':0};times=[];prior=np.load(ROOT/'input/prior_embeddings.npz')
 vectorfolder=out/'vectors';vectorfolder.mkdir()
 for group,rows in images.items():
  reference_vectors=[];native_vectors=[]
  for i,row in enumerate(rows):
   assert sha(row['path'])==row['sha256']
   with Image.open(row['path']) as image:x=transform(image).unsqueeze(0).contiguous()
   start=time.perf_counter_ns()
   with torch.inference_mode():reference=encoder(x).numpy().reshape(576).copy()
   torch_ms=(time.perf_counter_ns()-start)/1e6;counts['TorchCPU']+=1
   start=time.perf_counter_ns();extractor=net.create_extractor();assert extractor.input('in0',ncnn.Mat(x.numpy()[0]))==0
   code,output=extractor.extract('out0');assert code==0
   actual=np.asarray(output).reshape(576).copy();native_ms=(time.perf_counter_ns()-start)/1e6;counts['ncnnCPU']+=1
   assert np.isfinite(reference).all() and np.isfinite(actual).all()
   refnorm=reference/np.linalg.norm(reference);natnorm=actual/np.linalg.norm(actual)
   error=float(np.max(np.abs(refnorm-natnorm)));cosine=float(refnorm.astype(np.float64)@natnorm.astype(np.float64))
   assert error<=p['max_normalized_embedding_absolute_error'] and 1-cosine<=p['maximum_1_minus_cosine_error']
   previous=prior[group][i];prior_error=float(np.max(np.abs(refnorm-previous)));assert prior_error<=p['prior_Torch_normalized_embedding_tolerance']
   name=group+'_'+str(i).zfill(3);file=vectorfolder/(name+'.npz')
   np.savez_compressed(file,input=x.numpy(),Torch_raw=reference,ncnn_raw=actual,Torch_normalized=refnorm,ncnn_normalized=natnorm)
   records.append({'name':name,'group':group,'index':i,'file':file.relative_to(out).as_posix(),'sha256':sha(file),
    'input_tensor_sha256':hashlib.sha256(x.numpy().tobytes()).hexdigest(),'max_normalized_difference':error,'cosine':cosine,
    'maximum_reference_vs_prior_normalized_error':prior_error,'Torch_ms':torch_ms,'ncnn_ms':native_ms})
   reference_vectors.append(refnorm);native_vectors.append(natnorm);times.append(native_ms)
  features[group]={'Torch':np.stack(reference_vectors),'ncnn':np.stack(native_vectors)}
  print(json.dumps({'group':group,'completed_real_image_forwards':counts}),flush=True)
 prior.close();retrieval=[]
 for gallery in ['old_gallery','new_gallery']:
  labels=p['registered_IDs'];galleryrows=images[gallery]
  for queries in ['labelled_query','real_event_query']:
   scores={}
   for backend in ['Torch','ncnn']:
    dot=features[queries][backend].astype(np.float64)@features[gallery][backend].astype(np.float64).T
    score=np.stack([np.max(dot[:,[i for i,r in enumerate(galleryrows) if r['identity']==label]],axis=1) for label in labels],axis=1);scores[backend]=score
   a=scores['Torch'];b=scores['ncnn'];difference=float(np.max(np.abs(a-b)))
   assert np.array_equal(np.argmax(a,axis=1),np.argmax(b,axis=1))
   assert np.array_equal(a.max(1)>=p['fixed_threshold'],b.max(1)>=p['fixed_threshold'])
   retrieval.append({'gallery':gallery,'queries':queries,'query_images':len(images[queries]),'top1_and_threshold_decisions_exact':True,'maximum_cosine_score_difference':difference})
 assert counts==p['expected_measured_real_image_forwards']
 save(out/'vector_manifest.json',records);save(out/'retrieval_parity.json',retrieval)
 result={'status':'FIXED_BODY_ENCODER_EXPORTED_AND132_NCNN_EMBEDDINGS_PASS_REFERENCE_AND_RETRIEVAL_GATES',
  'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/encoder_v1.json'),
  'encoder_checkpoint_sha256':p['encoder_condition']['checkpoint_sha256'],'export_fp16':False,'ncnn_operators':operators,
  'real_image_forwards':counts,'export_trace_and_converter_probe_forwards_not_in_these_counts':True,
  'maximum_normalized_embedding_difference':max(r['max_normalized_difference'] for r in records),
  'maximum_prior_embedding_difference':max(r['maximum_reference_vs_prior_normalized_error'] for r in records),
  'mean_server_ncnn_embedding_ms':float(np.mean(times)),'all_retrieval_decisions_exact':True,
  'new_training_updates':0,'board_inference_executed':False,'identity_accuracy_newly_proven':False,'whole_goal_complete':False}
 save(out/'summary.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
