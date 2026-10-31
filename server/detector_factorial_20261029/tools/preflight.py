"""Exact rotation oracles and three real trainer two-update discarded runs."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import os,sys,socket,json,copy,gc,hashlib,inspect,random
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.models.yolo.detect.train import DetectionTrainer
from ultralytics.engine.trainer import BaseTrainer
from rotation_training import rotate_training_batch,FactorialTrainer,RightAngleTrainer
from common import ROOT,sha,save_new,state_digest
class SmokeStop(Exception):pass
def pixel_rotate(a,k):
    if k==0:return a.copy()
    if k==1:return a.transpose(0,2,1)[:,::-1,:].copy()
    if k==2:return a[:,::-1,::-1].copy()
    return a.transpose(0,2,1)[:,:,::-1].copy()
def oracles():
    rows=[]
    for side in [16,32]:
        arrays=np.arange(4*3*side*side,dtype=np.float32).reshape(4,3,side,side)
        rects=[(3,2,3,8,11),(1,1,2,9,12),(0,4,5,13,15),(3,8,1,15,6),(0,1,1,5,6)]
        masks=[];boxes=[];indices=[]
        for batch,x0,y0,x1,y1 in rects:
            mask=np.zeros((1,side,side),np.float32);mask[0,y0:y1,x0:x1]=1;masks.append(mask)
            boxes.append([(x0+x1)/(2*side),(y0+y1)/(2*side),(x1-x0)/side,(y1-y0)/side]);indices.append(batch)
        boxes=np.asarray(boxes,np.float32)
        schedules=[[k]*4 for k in range(4)]+[[0,1,2,3],[3,2,1,0]]
        for device in ['cpu','cuda']:
            for turns in schedules:
                images=torch.as_tensor(arrays,device=device);target=torch.as_tensor(boxes,device=device);batches=torch.tensor(indices,device=device)
                output,rotated=rotate_training_batch(images,target,batches,turns)
                expected_images=np.stack([pixel_rotate(a,k) for a,k in zip(arrays,turns)])
                assert np.array_equal(output.cpu().numpy(),expected_images)
                expected=[]
                for mask,batch in zip(masks,indices):
                    transformed=pixel_rotate(mask,turns[batch])[0];ys,xs=np.nonzero(transformed)
                    expected.append([(xs.min()+xs.max()+1)/(2*side),(ys.min()+ys.max()+1)/(2*side),(xs.max()-xs.min()+1)/side,(ys.max()-ys.min()+1)/side])
                assert np.array_equal(rotated.cpu().numpy(),np.asarray(expected,np.float32))
                assert torch.equal(target[:,2]*target[:,3],rotated[:,2]*rotated[:,3])
                restored_images,restored_boxes=rotate_training_batch(output,rotated,batches,[(4-k)%4 for k in turns])
                assert torch.equal(images,restored_images) and torch.equal(target,restored_boxes)
                empty_images,empty_boxes=rotate_training_batch(images,torch.empty((0,4),device=device),torch.empty((0,),device=device),turns)
                assert torch.equal(empty_images,output) and empty_boxes.shape==(0,4)
                rows.append({'side':side,'device':device,'turns':turns,'image_pixel_permutation_exact':True,'independent_mask_box_envelope_exact':True,
                 'inverse_and_area_exact':True,'empty_labels_exact':True,'object_batch_indices_not_sorted':True})
    return rows
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    p=json.loads((ROOT/'protocol/training_v3.json').read_text());assert torch.__version__==p['library']['torch'] and ultralytics.__version__==p['library']['ultralytics']
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    for name,digest in p['input_sha256'].items():assert sha(ROOT/'input'/name)==digest
    for name,digest in p['implementation_sha256'].items():assert sha(ROOT/'tools'/name)==digest
    assert sha(p['source_weights'])==p['source_weights_sha256']
    labels=json.loads((ROOT/'input/loader_summary.json').read_text());assert sha(p['source_data_yaml'])==labels['data_yaml_sha256']
    manifest=json.loads((ROOT/'input/prepared_manifest.json').read_text());assert len(manifest)==8380
    for r in manifest:
        assert sha(r['image_alias'])==r['sha256'] and sha(r['label_path'])==r['label_sha256']
    audit=oracles();assert len(audit)==48
    records=[]
    # Full real trainer path, stopped deliberately after the second optimizer
    # update in the first epoch. No saved weights are admitted or reused.
    for name,size,rotate in [('plain192',192,False),('rot192',192,True),('rot256',256,True)]:
        seed=26;model=YOLO(p['source_weights']);observed=[];start=None
        def on_start(t):
            nonlocal start
            assert t.initial_model_digest==p['expected_initial_state_digests'][str(seed)]
            assert len(t.train_loader.dataset)==6809 and len(t.test_loader.dataset)==1571 and len(t.train_loader)==213
            assert sum(len(r['cls']) for r in t.train_loader.dataset.labels)==8888 and sum(len(r['cls']) for r in t.test_loader.dataset.labels)==1864
            assert type(t.optimizer).__name__=='AdamW';start=state_digest(t.model)
        def before_batch(t):t.observed_batches+=1
        def after_batch(t):
            assert torch.isfinite(t.loss).all()
            observed.append({'batch':t.observed_batches,'optimizer_steps':t.observed_optimizer_steps,'loss':t.loss.detach().cpu().tolist()})
            if t.observed_optimizer_steps>=2:raise SmokeStop('Expectedtwo-updatepreflightstop;discardweights')
        model.add_callback('on_train_start',on_start);model.add_callback('on_train_batch_start',before_batch);model.add_callback('on_train_batch_end',after_batch)
        stopped=False
        try:
            kwargs={**p['train_kwargs_common'],'workers':0,'save':False,'val':False}
            model.train(trainer=RightAngleTrainer if rotate else FactorialTrainer,data=p['source_data_yaml'],imgsz=size,
             project=str(ROOT/'results/preflight_discarded'),name=name,exist_ok=False,seed=seed,epochs=10,device=0,**kwargs)
        except SmokeStop:stopped=True
        t=model.trainer;assert stopped and t.observed_optimizer_steps==2 and t.observed_batches==2 and len(observed)==2
        assert start and state_digest(t.model)!=start and t.preprocess_image_count==64
        assert sum(t.rotation_counts.values())==(64 if rotate else 0) and t.rotation_label_rows>0 if rotate else sum(t.rotation_counts.values())==0
        # Exercise the real unaugmented superclass seam and global RNG states.
        synthetic={'img':torch.arange(2*3*size*size,dtype=torch.uint8).reshape(2,3,size,size),
                   'bboxes':torch.tensor([[.3,.4,.2,.25],[.8,.7,.1,.2]]),'batch_idx':torch.tensor([1.,0.]),'cls':torch.zeros((2,1))}
        rng_before=torch.get_rng_state().clone();cuda_before=torch.cuda.get_rng_state().clone()
        standard=DetectionTrainer.preprocess_batch(t,copy.deepcopy(synthetic))
        actual=t.preprocess_batch(copy.deepcopy(synthetic));assert torch.equal(torch.get_rng_state(),rng_before) and torch.equal(torch.cuda.get_rng_state(),cuda_before)
        if not rotate:assert all(torch.equal(actual[k],standard[k]) for k in standard)
        record={'name':name,'size':size,'rotate':rotate,'seed':seed,'initial_state_digest':t.initial_model_digest,
                'training_batches':2,'actual_discarded_optimizer_steps':2,'train_images':6809,'validation_images':1571,
                'train_label_rows':8888,'validation_label_rows':1864,'real_loss_history':observed,
                'rotation_schedule_first2_batches':t.rotation_schedule[:2],'global_torch_CPU_CUDA_RNG_unchanged_by_extra_preprocess':True,
                'no_extra_branch_matches_standard_preprocess_exact':not rotate,'weights_saved_for_reuse':False,
                'workers_override_for_smoke':0,'formal_workers':p['train_kwargs_common']['workers'],'source_video_or_Toros_forward':False}
        records.append(record);del actual,standard,synthetic,t,model;gc.collect();torch.cuda.empty_cache()
    result={'status':'48_CPU_CUDA_ROTATION_ORACLES_AND3_REAL_TRAINER_TWO_UPDATE_SMOKES_PASS',
       'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/training_v3.json'),
       'geometry_oracles':audit,'real_trainer_runs':records,'discarded_optimizer_steps':6,'formal_training_updates':0,
       'all_source_image_and_label_hashes_verified':8380,'source_video_Toros_or_final_candidates_forward':False,
       'torch':torch.__version__,'ultralytics':ultralytics.__version__,'device':torch.cuda.get_device_name(0),
       'no_formal_checkpoint_reuse':True,'whole_goal_complete':False}
    target=ROOT/'results/preflight.json';save_new(target,result);print(json.dumps({k:v for k,v in result.items() if k not in ['geometry_oracles','real_trainer_runs']}),flush=True)
if __name__=='__main__':main()
