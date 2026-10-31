"""Identity-disjoint A/B/C study; all checkpoints freeze before final inference."""
from pathlib import Path
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
from collections import defaultdict
from datetime import datetime,timezone
import csv,hashlib,json,random,time,sys
import numpy as np
from PIL import Image
import torch,torchvision
import torch.nn.functional as F
from torchvision.models import mobilenet_v3_small,MobileNet_V3_Small_Weights
from training_primitives import BodyTransform,identity_batch,batch_hard_triplet
from identity_metrics import calibrate_threshold,summarise,cluster_intervals

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_training');OUT=ROOT/'results/study'
OUT.mkdir(parents=True,exist_ok=False)
protocol_path=ROOT/'protocol/identity_training_v1.json';protocol=json.loads(protocol_path.read_text());opt=protocol['optimisation']
audit=json.loads((ROOT/'results/input_audit/summary.json').read_text());assert audit['status']=='PASS'
assert hashlib.sha256(protocol_path.read_bytes()).hexdigest()==audit['protocol_sha256']
manifest=json.loads((ROOT/'results/input_audit/manifest.json').read_text())
checkpoint=ROOT/'models/mobilenet_v3_small-047dcff4.pth'
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==protocol['checkpoint_sha256']
assert torch.cuda.is_available();torch.set_num_threads(4)
torch.backends.cudnn.deterministic=True;torch.backends.cudnn.benchmark=False
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
torch.use_deterministic_algorithms(True)
by_split={split:[r for r in manifest if r['split']==split] for split in ['train','validation_gallery','validation_query','evaluation_gallery','evaluation_query']}
train_ids=sorted({r['identity'] for r in by_split['train']})
assert not(set(train_ids)&{r['identity'] for r in manifest if r['split']!='train'})
class_index={identity:i for i,identity in enumerate(train_ids)}
cache={};evaluation_enabled=False;access_log=[]
def image(row):
    if row['split'].startswith('evaluation') and not evaluation_enabled:raise RuntimeError('Final image access before frozen checkpoint gate')
    path=row['relative_path']
    if path not in cache:
        with Image.open(ROOT/path) as im:im.load();cache[path]=im.convert('RGB')
        access_log.append({'relative_path':path,'split':row['split'],'evaluation_gate_open':evaluation_enabled})
    return cache[path].copy()
def seed_everything(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
def make_encoder(path=None):
    model=mobilenet_v3_small(weights=None)
    if path is None:model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
    encoder=torch.nn.Sequential(model.features,model.avgpool,torch.nn.Flatten())
    if path is not None:encoder.load_state_dict(torch.load(path,map_location='cpu',weights_only=True))
    return encoder.cuda().eval()
def extract(model,rows,transform):
    model.eval();vectors=[]
    with torch.inference_mode():
        for i in range(0,len(rows),32):
            batch=torch.stack([transform(image(r)) for r in rows[i:i+32]]).cuda()
            vectors.append(F.normalize(model(batch),dim=1).cpu().numpy())
    return np.concatenate(vectors)
def retrieve(gallery,query,gallery_rows,query_rows):
    ids=sorted({r['identity'] for r in gallery_rows})
    similarity=query.astype(float)@gallery.astype(float).T
    scores=np.stack([similarity[:,[i for i,r in enumerate(gallery_rows) if r['identity']==identity]].max(1) for identity in ids],axis=1)
    result=[]
    for row,values in zip(query_rows,scores):
        j=int(np.argmax(values));result.append({'relative_path':row['relative_path'],'identity':row['identity'],'role':row['role'],
             'split':row['split'],'day':row['day'],'is_known':row['identity'] in ids,'predicted_id':ids[j],'similarity':float(values[j])})
    return result
def assess(rows):
    threshold=calibrate_threshold([r['similarity'] for r in rows],[r['predicted_id'] for r in rows],[r['identity'] for r in rows],[r['is_known'] for r in rows])
    for row in rows:row['accepted']=row['similarity']>=threshold['threshold']
    return threshold,summarise(rows)
def save_json(path,value):path.write_text(json.dumps(value,indent=2))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

started=time.perf_counter();conditions=[]
for name,transform in [('A_official_frozen',MobileNet_V3_Small_Weights.IMAGENET1K_V1.transforms()),('B_letterbox_frozen',BodyTransform())]:
    seed_everything(26);model=make_encoder()
    gallery=extract(model,by_split['validation_gallery'],transform);query=extract(model,by_split['validation_query'],transform)
    predictions=retrieve(gallery,query,by_split['validation_gallery'],by_split['validation_query']);threshold,metrics=assess(predictions)
    dest=OUT/name;dest.mkdir();np.savez_compressed(dest/'validation_embeddings.npz',gallery=gallery,query=query)
    save_json(dest/'validation_predictions.json',predictions);save_json(dest/'threshold.json',threshold)
    conditions.append({'name':name,'seed':None,'checkpoint':str(checkpoint),'checkpoint_sha256':sha(checkpoint),
                       'threshold':threshold,'validation':metrics,'preprocess':'official' if name.startswith('A_') else 'letterbox',
                       'training_updates':0})
    del model;torch.cuda.empty_cache()

for seed in opt['seeds']:
    seed_everything(seed);rng=random.Random(seed);model=make_encoder();model.train()
    classifier=torch.nn.Parameter(torch.empty(len(train_ids),576,device='cuda'));torch.nn.init.normal_(classifier,std=.01)
    optimiser=torch.optim.AdamW(list(model.parameters())+[classifier],lr=opt['learning_rate'],weight_decay=opt['weight_decay'])
    augment=BodyTransform(augment=True);deterministic=BodyTransform();dest=OUT/f'C_letterbox_trained_seed{seed}';dest.mkdir()
    best_key=None;best=None;history=[];updates=0
    for epoch in range(1,opt['epochs']+1):
        model.train();losses=[];ce_values=[];triplet_values=[]
        for step in range(opt['batches_per_epoch']):
            selected=identity_batch(by_split['train'],rng,opt['identities_per_batch'],opt['images_per_identity'])
            rows=[by_split['train'][i] for i in selected]
            assert all(r['split']=='train' and r['identity'] in class_index for r in rows)
            batch=torch.stack([augment(image(r)) for r in rows]).cuda();labels=torch.tensor([class_index[r['identity']] for r in rows],device='cuda')
            optimiser.zero_grad(set_to_none=True);z=F.normalize(model(batch),dim=1)
            ce=F.cross_entropy(16*F.linear(z,F.normalize(classifier,dim=1)),labels)
            triplet=batch_hard_triplet(z,labels,.3);loss=ce+triplet
            assert torch.isfinite(loss);loss.backward()
            assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
            optimiser.step();updates+=1;losses.append(loss.item());ce_values.append(ce.item());triplet_values.append(triplet.item())
        vg=extract(model,by_split['validation_gallery'],deterministic);vq=extract(model,by_split['validation_query'],deterministic)
        predictions=retrieve(vg,vq,by_split['validation_gallery'],by_split['validation_query']);threshold,metrics=assess(predictions)
        key=(metrics['known_correct_accepted_C'],-metrics['known_wrong_accepted_W'],metrics['known_closed_top1_correct'],-epoch)
        record={'seed':seed,'epoch':epoch,'updates':updates,'mean_training_loss':float(np.mean(losses)),
                'mean_ce':float(np.mean(ce_values)),'mean_triplet':float(np.mean(triplet_values)),
                'validation_C':metrics['known_correct_accepted_C'],'validation_W':metrics['known_wrong_accepted_W'],
                'validation_U':metrics['known_rejected_U'],'validation_top1':metrics['known_closed_top1_correct'],
                'validation_unknown_accepts':metrics['unknown_false_accepts'],'threshold':threshold['threshold']}
        history.append(record);save_json(dest/'training_history.json',history)
        if best_key is None or key>best_key:
            best_key=key
            state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            torch.save(state,dest/'best_encoder.pt')
            np.savez_compressed(dest/'validation_embeddings.npz',gallery=vg,query=vq)
            save_json(dest/'validation_predictions.json',predictions);save_json(dest/'threshold.json',threshold)
            best={'name':dest.name,'seed':seed,'selected_epoch':epoch,'checkpoint':str(dest/'best_encoder.pt'),
                  'checkpoint_sha256':sha(dest/'best_encoder.pt'),'threshold':threshold,'validation':metrics,'preprocess':'letterbox',
                  'selected_training_updates':updates}
        print(json.dumps(record),flush=True)
    assert updates==opt['epochs']*opt['batches_per_epoch']
    best.update(training_updates=updates,training_identity_count=len(train_ids),encoder_parameters=sum(p.numel() for p in model.parameters()))
    save_json(dest/'selected_model.json',best);conditions.append(best)
    del model,classifier,optimiser;torch.cuda.empty_cache()

freeze={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'evaluation_features_computed':False,
        'protocol_sha256':audit['protocol_sha256'],'conditions':conditions,
        'image_accesses_before_gate':len(access_log),'forbidden_evaluation_accesses_before_gate':sum(r['split'].startswith('evaluation') for r in access_log)}
assert freeze['forbidden_evaluation_accesses_before_gate']==0
save_json(OUT/'all_models_and_thresholds_frozen.json',freeze);freeze_hash=sha(OUT/'all_models_and_thresholds_frozen.json')
evaluation_enabled=True;results=[]
for condition in conditions:
    assert sha(Path(condition['checkpoint']))==condition['checkpoint_sha256']
    seed_everything(condition['seed'] or 26)
    model=make_encoder(None if condition['seed'] is None else Path(condition['checkpoint']))
    transform=MobileNet_V3_Small_Weights.IMAGENET1K_V1.transforms() if condition['preprocess']=='official' else BodyTransform()
    gallery=extract(model,by_split['evaluation_gallery'],transform);query=extract(model,by_split['evaluation_query'],transform)
    predictions=retrieve(gallery,query,by_split['evaluation_gallery'],by_split['evaluation_query'])
    for row in predictions:row['accepted']=row['similarity']>=condition['threshold']['threshold']
    metrics=summarise(predictions);dest=OUT/condition['name']
    np.savez_compressed(dest/'evaluation_embeddings.npz',gallery=gallery,query=query)
    save_json(dest/'evaluation_predictions.json',predictions)
    with (dest/'evaluation_predictions.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(predictions[0]));w.writeheader();w.writerows(predictions)
    result={**condition,'evaluation':metrics,'evaluation_cluster_intervals':cluster_intervals(metrics['per_identity'])}
    save_json(dest/'summary.json',result);results.append(result)
    print(json.dumps({'condition':condition['name'],'evaluation':{k:v for k,v in metrics.items() if k!='per_identity'}}),flush=True)
    del model;torch.cuda.empty_cache()
assert sha(OUT/'all_models_and_thresholds_frozen.json')==freeze_hash
save_json(OUT/'feature_index.json',{split:rows for split,rows in by_split.items() if split!='train'})
save_json(OUT/'image_access_log.json',access_log)
summary={'job_id':os.environ['SLURM_JOB_ID'],'status':'COMPLETED_IDENTITY_DISJOINT_PILOT','protocol_sha256':audit['protocol_sha256'],
         'audit':audit,'conditions':results,'final_freeze_sha256':freeze_hash,'elapsed_s':time.perf_counter()-started,
         'torch':torch.__version__,'torchvision':torchvision.__version__,'device':torch.cuda.get_device_name(0),
         'scope':protocol['scope'],'evaluation_unit':'Curated body-crop query; all queries provided, so M0 is by construction',
         'seed_selection':'All three declared seeds reported, no best-seed selection'}
save_json(OUT/'summary.json',summary)
