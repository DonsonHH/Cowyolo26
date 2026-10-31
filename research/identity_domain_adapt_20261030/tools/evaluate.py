from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,socket,sys
import numpy as np
from PIL import Image
import torch
from torchvision.models import mobilenet_v3_small
from frozen_body_tensor import body_tensor
from frozen_identity_metrics import calibrate_threshold,summarise,cluster_intervals

ROOT=Path(__file__).resolve().parents[1]


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
 assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def retrieve(features,rows,gallery_IDs=None,query_IDs=None):
 gallery=[i for i,row in enumerate(rows) if row['purpose']=='gallery'and(gallery_IDs is None or row['identity']in gallery_IDs)]
 queries=[i for i,row in enumerate(rows) if row['purpose']!='gallery'and(not row['is_known']or query_IDs is None or row['identity']in query_IDs)]
 labels=sorted({rows[i]['identity']for i in gallery});similarity=features[queries].astype(float)@features[gallery].astype(float).T
 scores=np.stack([similarity[:,[j for j,index in enumerate(gallery)if rows[index]['identity']==label]].max(axis=1)for label in labels],axis=1)
 result=[]
 for position,index in enumerate(queries):
  order=sorted(range(len(labels)),key=lambda j:(-scores[position,j],labels[j]));source=rows[index]
  result.append({'source_index':source['source_index'],'identity':source['identity'],'is_known':source['is_known'],'day':source['day'],
                 'predicted_id':labels[order[0]],'similarity':float(scores[position,order[0]]),'top5_IDs':[labels[j]for j in order[:5]],
                 'scores_by_ID':{label:float(score)for label,score in zip(labels,scores[position])}})
 return result


assert os.environ.get('SLURM_JOB_ID')and socket.gethostname()!='mu01'
torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
plan=load(ROOT/'protocol/run_v1.json');execution=load(ROOT/'protocol/execution_v1.json')
assert execution['protocol_sha256']==sha(ROOT/'protocol/run_v1.json')
for relative,digest in execution['code_hashes'].items():assert sha(ROOT/relative)==digest
source_root=Path(plan['Cows_evaluation_source_directory']);source_plan=load(source_root/'protocol/run_v1.json')
assert sha(source_root/'protocol/run_v1.json')==plan['Cows_evaluation_source_protocol_sha256']
source_acquisition=load(source_root/'results/acquisition_v2.json')
for row in source_acquisition['records']:assert sha(source_root/row['local_relative_file'])==row['sha256']
selected=[]
for index,row in enumerate(source_plan['selected_images']):
 selected.append({**row,'identity':row['identity_namespace'],'day':row['date'],'source_index':index,'path':str(source_root/row['local_relative_file'])})
retention=[]
for index,row in enumerate(plan['MultiCam_retention_images']):
 retention.append({**row,'source_index':index,'path':row['remote_path'],'purpose':'gallery'if row['split']=='evaluation_gallery'else'known_query',
                   'is_known':row['role']=='evaluation_registered_ids'})
for row in retention:
 assert sha(row['path'])==row['sha256']
 if row['purpose']!='gallery'and not row['is_known']:row['purpose']='unknown_query'
out=ROOT/'results/evaluation';out.mkdir(exist_ok=False)
frozen=[]
for condition in plan['conditions']:
 folder=ROOT/'results/training'/condition['name'];terminal=load(folder/'terminal.json')
 assert terminal['status']=='ONE_DOMAIN_TRAINING_CONDITION_COMPLETE'and terminal['optimizer_updates']==300
 assert terminal['training_image_forwards']==9600 and terminal['new_calibration_or_development_image_forwards']==0
 checkpoint=folder/'last_encoder.pt';assert sha(checkpoint)==terminal['last_encoder_sha256']
 frozen.append({'condition':condition,'checkpoint':str(checkpoint),'sha256':sha(checkpoint),'terminal_sha256':sha(folder/'terminal.json')})
assert len({load(ROOT/'results/training'/condition['name']/'terminal.json')['initial_encoder_state_digest']for condition in plan['conditions']})==1
save(out/'all6_last_checkpoints_frozen.json',{'status':'ALL6_LAST300_WEIGHTS_FROZEN_BEFORE_ANY_CALIBRATION_OR_DEVELOPMENT_FEATURES',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'models':frozen,'new_evaluation_model_image_forwards_at_freeze':0})
weight_freeze_SHA=sha(out/'all6_last_checkpoints_frozen.json')
total_images=total_calls=0;active={};forward_counts={};input_hashes={};timeline=[]


def count_forward(model,args):
 global total_images,total_calls
 assert not model.training and args[0].shape[1:]==(3,224,224)and len(args[0])<=12
 total_images+=len(args[0]);total_calls+=1;key=active['name']+':'+active['phase'];forward_counts[key]=forward_counts.get(key,0)+len(args[0])


models={}
for row in frozen:
 full=mobilenet_v3_small(weights=None);encoder=torch.nn.Sequential(full.features,full.avgpool,torch.nn.Flatten()).eval()
 encoder.load_state_dict(torch.load(row['checkpoint'],map_location='cpu',weights_only=True))
 for parameter in encoder.parameters():parameter.requires_grad_(False)
 encoder.register_forward_pre_hook(count_forward);models[row['condition']['name']]=encoder


def extract(name,phase,rows):
 active.update(name=name,phase=phase);raws=[];hashes=[]
 for start in range(0,len(rows),12):
  batch=rows[start:start+12];inputs=[]
  for row in batch:
   path=Path(row['path'])
   with Image.open(path)as image:image.load();value=body_tensor(image)
   digest=hashlib.sha256(value.tobytes()).hexdigest();key=(phase,row['source_index'])
   if key in input_hashes:assert input_hashes[key]==digest
   else:input_hashes[key]=digest
   hashes.append({'source_index':row['source_index'],'input_tensor_sha256':digest});inputs.append(value[0])
  with torch.inference_mode():raw=models[name](torch.from_numpy(np.stack(inputs))).detach().cpu().contiguous().numpy()
  assert raw.shape==(len(batch),576)and np.isfinite(raw).all();raws.extend(raw.copy())
 raw=np.stack(raws);normalized=raw/np.linalg.norm(raw,axis=1,keepdims=True);assert np.isfinite(normalized).all()
 folder=out/phase/name;folder.mkdir(parents=True);np.savez_compressed(folder/'features.npz',raw=raw,normalized=normalized)
 save(folder/'input_hashes.json',hashes);timeline.append({'condition':name,'phase':phase,'images':len(rows),'finished_UTC':datetime.now(timezone.utc).isoformat(),'cumulative_images':total_images})
 return normalized


calibration=[]
calrows=[row for row in selected if row['phase']=='calibration'];devrows=[row for row in selected if row['phase']=='evaluation']
for frozen_row in frozen:
 name=frozen_row['condition']['name'];features=extract(name,'calibration',calrows);predictions=retrieve(features,calrows)
 threshold=calibrate_threshold([row['similarity']for row in predictions],[row['predicted_id']for row in predictions],
                               [row['identity']for row in predictions],[row['is_known']for row in predictions],.05)
 save(out/'calibration'/name/'retrieval.json',predictions)
 calibration.append({'condition':name,'threshold':threshold,'feature_SHA256':sha(out/'calibration'/name/'features.npz')})
assert total_images==1080 and total_calls==90
save(out/'all6_thresholds_frozen.json',{'status':'ALL6_COWS_THRESHOLDS_FROZEN_BEFORE_ANY_DEVELOPMENT_OR_RETENTION_FEATURE',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'weight_freeze_SHA256':weight_freeze_SHA,'calibration':calibration,
 'calibration_image_forwards':total_images,'development_feature_forwards':0})
threshold_freeze_SHA=sha(out/'all6_thresholds_frozen.json');outcomes=[]
evaluation_IDs=['Cows2021_IdentificationTest:'+identity for identity in source_plan['roles']['evaluation_registered']]
folds=[evaluation_IDs[:20],evaluation_IDs[20:]]
for row in frozen:
 name=row['condition']['name'];assert sha(out/'all6_thresholds_frozen.json')==threshold_freeze_SHA
 feature=extract(name,'development',devrows);tau=next(value['threshold']['threshold']for value in calibration if value['condition']==name)
 for scope,IDs in [('fold0',folds[0]),('fold1',folds[1]),('full40',evaluation_IDs)]:
  predictions=retrieve(feature,devrows,IDs,IDs)
  save(out/'development'/name/(scope+'_unthresholded.json'),predictions)
  for policy,threshold in [('original_MultiCam',plan['original_threshold']),('Cows_calibrated',tau)]:
   decisions=[{**value,'accepted':value['similarity']>=threshold}for value in predictions];metrics=summarise(decisions)
   metrics['known_closed_Top5_correct']=sum(value['identity']in value['top5_IDs']for value in decisions if value['is_known'])
   outcomes.append({'condition':name,'arm':row['condition']['arm'],'seed':row['condition']['seed'],'dataset':'Cows2021',
                    'scope':scope,'threshold_policy':policy,'threshold':threshold,'metrics':metrics,'ID_cluster_intervals':cluster_intervals(metrics['per_identity'])})
   save(out/'development'/name/(scope+'_'+policy+'_decisions.json'),decisions)
 retained=extract(name,'retention',retention);predictions=retrieve(retained,retention)
 decisions=[{**value,'accepted':value['similarity']>=plan['original_threshold']}for value in predictions];metrics=summarise(decisions)
 save(out/'retention'/name/'original_threshold_decisions.json',decisions)
 outcomes.append({'condition':name,'arm':row['condition']['arm'],'seed':row['condition']['seed'],'dataset':'MultiCam2023',
                  'scope':'seen_retention30gallery60query','threshold_policy':'original_MultiCam','threshold':plan['original_threshold'],
                  'metrics':metrics,'ID_cluster_intervals':cluster_intervals(metrics['per_identity'])})
assert total_images==3780 and total_calls==318 and len(outcomes)==42
summary={'status':'ALL6_LAST300_WEIGHTS_JOINT_THRESHOLDS_MATCHED20_ID_DEVELOPMENT_AND_RETENTION_COMPLETE',
         'created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),
         'actual_evaluation_model_image_forwards':total_images,'actual_network_calls':total_calls,'warmup_forwards':0,
         'by_condition_phase_forwards':forward_counts,'weight_freeze_SHA256':weight_freeze_SHA,'threshold_freeze_SHA256':threshold_freeze_SHA,
         'timeline':timeline,'calibration':calibration,'outcomes':outcomes,'models':frozen,
         'development_material_previously_seen':True,'future20_ID_pixels_opened':False,'new_board_forwards':0,'whole_goal_complete':False}
save(out/'summary.json',summary)
print(json.dumps({key:value for key,value in summary.items()if key not in['timeline','calibration','outcomes','models','by_condition_phase_forwards']}),flush=True)
