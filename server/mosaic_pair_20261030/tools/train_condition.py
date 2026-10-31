"""One fresh mosaic arm/seed; append observed batch/gradient records as it runs."""
from pathlib import Path
from datetime import datetime,timezone
import os,socket,json,csv,time,hashlib,argparse,math
import torch,ultralytics
from ultralytics import YOLO
from common import ROOT,sha,state_digest,save,save_new,numpy_json
from rotation_training import RightAngleTrainer

class RecordedTrainer(RightAngleTrainer):
    def preprocess_batch(self,batch):
        batch=super().preprocess_batch(batch)
        x=batch['img'].detach().cpu().contiguous().numpy()
        boxes=batch['bboxes'].detach().cpu().contiguous().numpy()
        self.current_input_audit={'NN_input_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'NN_input_shape':list(x.shape),
            'bbox_tensor_sha256':hashlib.sha256(boxes.tobytes()).hexdigest(),'label_rows':len(boxes),
            'anchor_names':[Path(p).name for p in batch['im_file']]}
        return batch

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    parser=argparse.ArgumentParser();parser.add_argument('--condition-index',type=int,required=True);a=parser.parse_args()
    p=json.loads((ROOT/'protocol/training_v1.json').read_text());e=json.loads((ROOT/'protocol/formal_execution_v1.json').read_text())
    assert e['protocol_sha256']==sha(ROOT/'protocol/training_v1.json')
    for name,digest in e['files_sha256'].items():assert sha(ROOT/name)==digest,name
    assert e['preflight_sha256']==sha(ROOT/'results/preflight.json')
    smoke=json.loads((ROOT/'results/preflight.json').read_text());assert smoke['discarded_optimizer_updates']==4 and smoke['formal_training_updates']==0
    assert smoke['status']=='BOTH_MOSAIC_ARMS_REAL_CUDA_LOSS_GRADIENT_AND_TWO_OPTIMIZER_UPDATES_PASS'
    assert torch.__version__==p['library']['torch'] and ultralytics.__version__==p['library']['ultralytics']
    assert sha(p['source_weights'])==p['source_weights_sha256']
    c=p['conditions'][a.condition_index];assert c['array_index']==a.condition_index
    output=ROOT/'results/training';output.mkdir(exist_ok=True);folder=output/c['name'];assert not folder.exists()
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    model=YOLO(p['source_weights']);history=[];batch_rows=grad_rows=0;started=time.monotonic_ns();streams={}
    def on_start(t):
        assert t.initial_model_digest==p['expected_initial_state_digests'][str(c['seed'])]
        assert len(t.train_loader.dataset)==6809 and len(t.test_loader.dataset)==1571 and len(t.train_loader)==213
        assert sum(len(r['cls']) for r in t.train_loader.dataset.labels)==8888 and sum(len(r['cls']) for r in t.test_loader.dataset.labels)==1864
        assert type(t.optimizer).__name__=='AdamW' and t.args.workers==2 and float(t.args.mosaic)==c['mosaic']
        save_new(folder/'initial_state.json',{'condition':c,'initial_state_digest':t.initial_model_digest,'protocol_sha256':sha(ROOT/'protocol/training_v1.json'),
            'train_images':6809,'validation_images':1571,'train_labels':8888,'validation_labels':1864})
        streams['batch']=(folder/'actual_batches.jsonl').open('x',encoding='utf-8');streams['gradient']=(folder/'actual_gradient_updates.jsonl').open('x',encoding='utf-8')
        original=t.optimizer_step
        def checked_step():
            nonlocal grad_rows
            gradients=[v.grad for v in t.model.parameters() if v.grad is not None]
            assert gradients and all(torch.isfinite(v).all() for v in gradients)
            nonzero=sum(bool(torch.count_nonzero(v)) for v in gradients);assert nonzero>0
            original();grad_rows+=1
            record={'optimizer_update':grad_rows,'training_batch':t.observed_batches,'finite_tensors':len(gradients),'nonzero_tensors':nonzero}
            streams['gradient'].write(json.dumps(record,default=numpy_json)+'\n');streams['gradient'].flush()
        t.optimizer_step=checked_step
    def before(t):t.observed_batches+=1
    def after(t):
        nonlocal batch_rows
        assert torch.isfinite(t.loss).all();batch_rows+=1
        record={'training_batch':t.observed_batches,'optimizer_updates':t.observed_optimizer_steps,'loss':t.loss.detach().cpu().tolist(),
            'rotation_turns':t.rotation_schedule[-1]['turns'],**t.current_input_audit}
        assert record['NN_input_shape'][0]==len(record['rotation_turns'])
        streams['batch'].write(json.dumps(record,default=numpy_json)+'\n');streams['batch'].flush()
    def fit(t):
        epoch=t.epoch+1
        if epoch>10 or epoch<=len(history):return
        history.append({'epoch':epoch,'training_batches':t.observed_batches,'optimizer_updates':t.observed_optimizer_steps,
            'validation':{k:float(v) for k,v in t.metrics.items()}})
        save(folder/'observed_history.json',history)
        save(folder/'progress.json',{'epoch':epoch,'training_batches':t.observed_batches,'optimizer_updates':t.observed_optimizer_steps,
            'persisted_batch_rows':batch_rows,'persisted_gradient_rows':grad_rows,'elapsed_s':(time.monotonic_ns()-started)/1e9})
    model.add_callback('on_train_start',on_start);model.add_callback('on_train_batch_start',before)
    model.add_callback('on_train_batch_end',after);model.add_callback('on_fit_epoch_end',fit)
    try:
        returned=model.train(trainer=RecordedTrainer,data=p['source_data_yaml'],project=str(output),name=c['name'],exist_ok=False,
            seed=c['seed'],epochs=10,imgsz=192,device=0,**{**p['train_kwargs_common'],'mosaic':c['mosaic']})
    finally:
        for f in streams.values():f.close()
    t=model.trainer
    assert t.observed_batches==batch_rows==2130 and t.observed_optimizer_steps==grad_rows==1225 and t.preprocess_image_count==68090
    assert len(t.rotation_schedule)==2130 and sum(t.rotation_counts.values())==68090
    actual=list(csv.DictReader((folder/'results.csv').open()));assert len(actual)==len(history)==10
    for row in actual:
        for key,value in row.items():assert math.isfinite(float(value)),(key,value)
    save_new(folder/'optimizer_step_batch_indices.json',t.optimizer_step_batch_indices)
    last=folder/'weights/last.pt';best=folder/'weights/best.pt';assert last.is_file() and best.is_file()
    result={'status':'ONE_FRESH10_EPOCH_MOSAIC_ARM_SEED_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
        'job_id':os.environ['SLURM_JOB_ID'],'array_task_id':os.environ.get('SLURM_ARRAY_TASK_ID'),'condition':c,
        'protocol_sha256':sha(ROOT/'protocol/training_v1.json'),'preflight_sha256':sha(ROOT/'results/preflight.json'),
        'initial_state_digest':t.initial_model_digest,'epochs':10,'training_batches':2130,'optimizer_updates':1225,'training_image_presentations':68090,
        'actual_persisted_batch_rows':batch_rows,'actual_persisted_gradient_rows':grad_rows,'actual_rotation_counts':dict(t.rotation_counts),
        'actual_rotation_label_rows':t.rotation_label_rows,'optimizer_step_indices_sha256':sha(folder/'optimizer_step_batch_indices.json'),
        'batch_audit_sha256':sha(folder/'actual_batches.jsonl'),'gradient_audit_sha256':sha(folder/'actual_gradient_updates.jsonl'),
        'last_checkpoint':str(last),'last_checkpoint_sha256':sha(last),'archived_best_sha256':sha(best),'results_csv_sha256':sha(folder/'results.csv'),
        'effective_args_sha256':sha(folder/'args.yaml'),'last_epoch_validation':{k:float(v) for k,v in actual[-1].items() if k.startswith('metrics/')},
        'source_or_Toros_inference_before_all_weights_frozen':False,'new_independent_test':False,'whole_goal_complete':False,
        'elapsed_s':(time.monotonic_ns()-started)/1e9}
    save_new(folder/'condition_complete.json',result);print(json.dumps(result,default=numpy_json),flush=True)
if __name__=='__main__':main()
