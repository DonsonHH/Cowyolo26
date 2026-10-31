"""One fixed10-epoch low-resolution factor/seed; no video inference."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import argparse,os,socket,json,math,csv,time,gc,hashlib
import torch,ultralytics
from ultralytics import YOLO
from common import ROOT,sha,state_digest,save,save_new
from rotation_training import FactorialTrainer,RightAngleTrainer
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    parser=argparse.ArgumentParser();parser.add_argument('--condition-index',type=int,required=True);a=parser.parse_args()
    p=json.loads((ROOT/'protocol/training_v4.json').read_text());execution=json.loads((ROOT/'protocol/formal_execution_v1.json').read_text())
    assert execution['base_protocol_sha256']==sha(ROOT/'protocol/training_v4.json') and execution['training_script_sha256']==sha(Path(__file__))
    assert execution['preflight_sha256']==sha(ROOT/'results/preflight_grad.json')
    smoke=json.loads((ROOT/'results/preflight_grad.json').read_text());assert smoke['status']=='48_ROTATION_ORACLES_AND3_REAL_TRAINERS6_FINITE_GRADIENT_UPDATES_PASS'
    assert smoke['formal_training_updates']==0 and smoke['discarded_optimizer_steps']==6 and len(smoke['geometry_oracles'])==48
    assert all(len(r['gradient_audits'])==2 for r in smoke['real_trainer_runs'])
    assert torch.__version__==p['library']['torch'] and ultralytics.__version__==p['library']['ultralytics']
    assert sha(p['source_weights'])==p['source_weights_sha256']
    for name,digest in p['implementation_sha256'].items():assert sha(ROOT/'tools'/name)==digest
    for name,digest in p['input_sha256'].items():assert sha(ROOT/'input'/name)==digest
    c=p['new_conditions'][a.condition_index];assert c['array_index']==a.condition_index
    assert c['imgsz'] in [192,256,320] and c['seed'] in [26,27,28] and not (c['imgsz']==320 and not c['right_angle'])
    output=ROOT/'results/training';output.mkdir(exist_ok=True);folder=output/c['condition_id'];assert not folder.exists(),folder
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    model=YOLO(p['source_weights']);history=[];gradient_counts=[];started=time.monotonic_ns()
    def on_start(t):
        assert t.initial_model_digest==p['expected_initial_state_digests'][str(c['seed'])]
        assert len(t.train_loader.dataset)==6809 and len(t.test_loader.dataset)==1571 and len(t.train_loader)==213
        assert sum(len(r['cls']) for r in t.train_loader.dataset.labels)==8888 and sum(len(r['cls']) for r in t.test_loader.dataset.labels)==1864
        assert type(t.optimizer).__name__=='AdamW' and t.args.workers==2
        save_new(folder/'initial_state.json',{'condition':c,'initial_state_digest':t.initial_model_digest,
         'train_images':6809,'validation_images':1571,'train_label_rows':8888,'validation_label_rows':1864,'batches_per_epoch':213,
         'preflight_sha256':sha(ROOT/'results/preflight_grad.json'),'protocol_sha256':sha(ROOT/'protocol/training_v4.json')})
        original=t.optimizer_step
        def checked_step():
            gradients=[q.grad for q in t.model.parameters() if q.grad is not None]
            assert gradients and all(torch.isfinite(q).all() for q in gradients)
            nonzero=sum(bool(torch.count_nonzero(q)) for q in gradients);assert nonzero>0
            gradient_counts.append({'update':len(gradient_counts)+1,'batch':t.observed_batches,'finite_tensors':len(gradients),'nonzero_tensors':nonzero})
            original()
        t.optimizer_step=checked_step
    def on_batch_start(t):t.observed_batches+=1
    def on_batch_end(t):assert torch.isfinite(t.loss).all()
    def on_fit(t):
        epoch=t.epoch+1
        if epoch>10 or epoch<=len(history):return
        history.append({'epoch':epoch,'training_batches':t.observed_batches,'optimizer_steps':t.observed_optimizer_steps,
          'validation':{k:float(v) for k,v in t.metrics.items()}})
        save(folder/'observed_history.json',history)
        save(folder/'progress.json',{'condition':c['condition_id'],'epoch':epoch,'batches':t.observed_batches,
          'optimizer_steps':t.observed_optimizer_steps,'elapsed_s':(time.monotonic_ns()-started)/1e9})
    model.add_callback('on_train_start',on_start);model.add_callback('on_train_batch_start',on_batch_start)
    model.add_callback('on_train_batch_end',on_batch_end);model.add_callback('on_fit_epoch_end',on_fit)
    returned=model.train(trainer=RightAngleTrainer if c['right_angle'] else FactorialTrainer,data=p['source_data_yaml'],
      project=str(output),name=c['condition_id'],exist_ok=False,device=0,seed=c['seed'],epochs=10,imgsz=c['imgsz'],**p['train_kwargs_common'])
    t=model.trainer;actual=list(csv.DictReader((folder/'results.csv').open()))
    assert len(actual)==len(history)==10 and t.observed_batches==2130 and t.observed_optimizer_steps==len(gradient_counts)==1225
    assert t.preprocess_image_count==68090
    expected=next(r for r in p['baseline_checkpoint_conditions'] if r['seed']==c['seed'])
    save_new(folder/'optimizer_step_batch_indices.json',t.optimizer_step_batch_indices)
    assert sha(folder/'optimizer_step_batch_indices.json')==expected['optimizer_step_schedule_sha256']
    save_new(folder/'gradient_checks.json',gradient_counts)
    save_new(folder/'rotation_schedule.json',t.rotation_schedule)
    if c['right_angle']:
        assert len(t.rotation_schedule)==2130 and sum(t.rotation_counts.values())==68090 and t.rotation_label_rows>0 and set(t.rotation_counts)=={0,1,2,3}
    else:assert not t.rotation_schedule and not t.rotation_counts and t.rotation_label_rows==0
    last=folder/'weights/last.pt';best=folder/'weights/best.pt';assert last.is_file() and best.is_file()
    final={'status':'ONE_FIXED10_EPOCH_LOWRES_FACTOR_SEED_COMPLETE','condition':c,'job_id':os.environ['SLURM_JOB_ID'],
      'array_task_id':os.environ.get('SLURM_ARRAY_TASK_ID'),'protocol_sha256':sha(ROOT/'protocol/training_v4.json'),
      'execution_protocol_sha256':sha(ROOT/'protocol/formal_execution_v1.json'),'initial_state_digest':t.initial_model_digest,
      'epochs':10,'training_batches':2130,'optimizer_steps':1225,'finite_gradient_updates':len(gradient_counts),
      'training_image_presentations':68090,'rotation_counts':dict(t.rotation_counts),'rotation_label_rows':t.rotation_label_rows,
      'rotation_schedule_sha256':sha(folder/'rotation_schedule.json'),'optimizer_step_schedule_sha256':sha(folder/'optimizer_step_batch_indices.json'),
      'last_checkpoint':str(last),'last_checkpoint_sha256':sha(last),'archived_best_sha256':sha(best),
      'last_epoch_validation':{k:float(v) for k,v in actual[-1].items() if k.startswith('metrics/')},
      'trainer_returned_archived_best_validation':returned.results_dict,'results_csv_sha256':sha(folder/'results.csv'),
      'effective_args_sha256':sha(folder/'args.yaml'),'elapsed_s':(time.monotonic_ns()-started)/1e9,
      'source_video_or_Toros_inference_before_all_weights_frozen':False,'new_independent_test':False,'whole_goal_complete':False}
    save_new(folder/'condition_complete.json',final);print(json.dumps(final),flush=True)
if __name__=='__main__':main()
