"""One independent process per arm/seed; actual paired step schedule gate follows."""
from pathlib import Path
import csv,json,os,time
import torch,ultralytics
from ultralytics import YOLO
from common import *
from observed_trainer import ObservedTrainer


def main():
    torch.set_num_threads(4);assert torch.cuda.is_available() and ultralytics.__version__=='8.4.63'
    pp=ROOT/'protocol/composition_v1.json';p=json.loads(pp.read_text())
    condition=p['conditions'][int(os.environ['SLURM_ARRAY_TASK_ID'])]
    name=condition['name'];arm=condition['arm'];seed=condition['seed']
    preflight=json.loads((ROOT/'results/preflight.json').read_text())
    assert preflight['status']=='PASS_REAL_LOADER_AND_TWO_DISCARDED_UPDATES_PER_ARM' and preflight['protocol_sha256']==sha(pp)
    prepared=json.loads((ROOT/'results/data_prepared.json').read_text());assert prepared['protocol_sha256']==sha(pp)
    diagnosis=json.loads((ROOT/'results/loader_label_diagnosis.json').read_text())
    effective_labels=next(r['actual_loader_rows'] for r in diagnosis['conditions'] if r['arm']==arm)
    assert sha(ROOT/'data'/arm/'slot_manifest.json')==prepared['arms'][arm]['slot_manifest_sha256']
    weights=PROJECT/'models/yolo26n.pt';assert sha(weights)==p['source_weights_sha256']
    out=ROOT/'results/training'/name;assert not out.exists()
    started=time.perf_counter();history=[]
    model=YOLO(str(weights))
    def on_start(trainer):
        assert len(trainer.train_loader.dataset)==5913 and len(trainer.test_loader.dataset)==370
        assert sum(len(r['cls']) for r in trainer.train_loader.dataset.labels)==effective_labels
        assert len(trainer.train_loader)==185 and type(trainer.optimizer).__name__=='AdamW'
        save(out/'initial_state.json',{'model_digest':trainer.initial_model_digest,'train_slots':len(trainer.train_loader.dataset),
                                      'validation_slots':len(trainer.test_loader.dataset),'batches_per_epoch':len(trainer.train_loader),
                                      'optimizer_class':type(trainer.optimizer).__name__,'seed':seed,'arm':arm})
    def on_batch_start(trainer):trainer.observed_batches+=1
    def on_batch_end(trainer):assert torch.isfinite(trainer.loss).all()
    def on_fit(trainer):
        # Callback is also used for final best validation with stripped state;
        # only one record per actual training epoch is added.
        epoch=trainer.epoch+1
        if epoch>p['epochs'] or epoch<=len(history):return
        record={'epoch':epoch,'training_batches':trainer.observed_batches,'optimizer_steps':trainer.observed_optimizer_steps,
                'validation':{k:float(v) for k,v in trainer.metrics.items()}}
        history.append(record);save(out/'observed_history.json',history)
        save(out/'optimizer_step_batch_indices.json',trainer.optimizer_step_batch_indices)
        save(out/'progress.json',{'condition':name,'epoch':epoch,'epochs':p['epochs'],'batches':trainer.observed_batches,'optimizer_steps':trainer.observed_optimizer_steps})
    model.add_callback('on_train_start',on_start);model.add_callback('on_train_batch_start',on_batch_start)
    model.add_callback('on_train_batch_end',on_batch_end);model.add_callback('on_fit_epoch_end',on_fit)
    returned=model.train(trainer=ObservedTrainer,data=str(ROOT/'data'/arm/'data.yaml'),project=str(ROOT/'results/training'),
                         name=name,exist_ok=False,device=0,seed=seed,epochs=p['epochs'],**p['train_kwargs'])
    trainer=model.trainer
    rows=list(csv.DictReader((out/'results.csv').open()));assert len(rows)==10
    assert trainer.observed_batches==1850 and len(history)==10 and trainer.observed_optimizer_steps>0
    checkpoint=out/'weights/last.pt';assert checkpoint.is_file()
    save(out/'optimizer_step_batch_indices.json',trainer.optimizer_step_batch_indices)
    result={'status':'ONE_COMPOSITION_CONDITION_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
            'array_task_id':int(os.environ['SLURM_ARRAY_TASK_ID']),'condition':condition,'protocol_sha256':sha(pp),
            'source_weights_sha256':sha(weights),'data_slot_manifest_sha256':prepared['arms'][arm]['slot_manifest_sha256'],
            'initial_model_digest':trainer.initial_model_digest,'epochs':len(rows),'training_batches':trainer.observed_batches,
            'optimizer_steps':trainer.observed_optimizer_steps,'optimizer_step_schedule_sha256':sha(out/'optimizer_step_batch_indices.json'),
            'checkpoint':str(checkpoint),'checkpoint_sha256':sha(checkpoint),'last_epoch_validation':{k:float(v) for k,v in rows[-1].items() if k.startswith('metrics/')},
            'trainer_return_metrics_for_archived_best':returned.results_dict,'args_sha256':sha(out/'args.yaml'),
            'training_csv_sha256':sha(out/'results.csv'),'history':history,'torch':torch.__version__,'ultralytics':ultralytics.__version__,
            'device':torch.cuda.get_device_name(0),'elapsed_s':time.perf_counter()-started,
            'scope':p['scope'],'source_video_or_Toros_forward_this_job':False,'dev_test_forward':False}
    save(out/'condition_complete.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['history','trainer_return_metrics_for_archived_best']}),flush=True)


if __name__=='__main__':main()
