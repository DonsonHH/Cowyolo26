"""All three fixed10-epoch source-date development runs, then freeze together."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import csv,json,math,os,socket,time
import torch,ultralytics
from ultralytics import YOLO
from common import ROOT,PROJECT,sha,save,verify_similarity_review
from observed_trainer import ObservedTrainer


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    assert torch.cuda.is_available() and ultralytics.__version__=='8.4.63'
    torch.set_num_threads(4)
    pp=ROOT/'protocol/detector_v1.json';p=json.loads(pp.read_text())
    assert torch.__version__==p['library']['torch']
    smoke_path=ROOT/'results/preflight.json';smoke=json.loads(smoke_path.read_text())
    assert smoke['status']=='PASS_ACTUAL_TRAIN_LOADER_AND_TWO_DISCARDED_CUDA_UPDATES'
    assert smoke['protocol_sha256']==sha(pp) and smoke['formal_training_updates']==0
    label_path=ROOT/'results/labels_v1/summary.json';labels=json.loads(label_path.read_text())
    assert sha(label_path)==smoke['label_loader_summary_sha256']
    similarity=verify_similarity_review(labels)
    assert similarity==smoke['similarity_review']
    manifest_path=ROOT/'results/labels_v1/prepared_image_label_manifest.json'
    assert sha(manifest_path)==labels['prepared_manifest_sha256']==smoke['prepared_manifest_sha256']
    manifest=json.loads(manifest_path.read_text())
    counts=Counter(row['actual_split'] for row in manifest)
    actual_labels={row['split']:row['actual_loaded_annotation_rows'] for row in labels['loader_results']}
    assert set(counts)=={'train','val'} and counts['train']>=64 and counts['val']>0
    data=ROOT/'data_v1/data.yaml';assert sha(data)==labels['data_yaml_sha256']
    source=PROJECT/'models/yolo26n.pt';assert sha(source)==p['source_weights_sha256']
    for row in manifest:
        assert Path(row['image_alias']).is_file() and sha(row['image_alias'])==row['sha256']
        assert sha(row['label_path'])==row['label_sha256']
    output=ROOT/'results/training';output.mkdir(exist_ok=False)
    save(output/'input_audit.json',{'protocol_sha256':sha(pp),'prepared_manifest_sha256':sha(manifest_path),
         'label_loader_summary_sha256':sha(label_path),'preflight_sha256':sha(smoke_path),
         'source_weights_sha256':sha(source),'roles':dict(counts),'loaded_labels':actual_labels,
         'similarity_review':similarity,'source_video_or_candidate_final_pixels_used':False})
    started=time.perf_counter();conditions=[]
    for seed in p['seeds']:
        name=f'seed{seed}';out=output/name
        assert not out.exists()
        model=YOLO(str(source));history=[]
        expected_batches=math.ceil(counts['train']/p['train_kwargs']['batch'])
        def on_start(trainer):
            assert len(trainer.train_loader.dataset)==counts['train']
            assert len(trainer.test_loader.dataset)==counts['val']
            assert len(trainer.train_loader)==expected_batches
            assert sum(len(r['cls']) for r in trainer.train_loader.dataset.labels)==actual_labels['train']
            assert sum(len(r['cls']) for r in trainer.test_loader.dataset.labels)==actual_labels['val']
            assert type(trainer.optimizer).__name__=='AdamW'
            save(out/'initial_state.json',{'seed':seed,'state_digest':trainer.initial_model_digest,
                 'batches_per_epoch':expected_batches,'train_images':counts['train'],'validation_images':counts['val'],
                 'optimizer':type(trainer.optimizer).__name__})
        def on_batch_start(trainer):trainer.observed_batches+=1
        def on_batch_end(trainer):assert torch.isfinite(trainer.loss).all()
        def on_fit(trainer):
            epoch=trainer.epoch+1
            # The trainer invokes this callback again after final best validation.
            if epoch>p['epochs'] or epoch<=len(history):return
            record={'epoch':epoch,'training_batches':trainer.observed_batches,
                    'optimizer_steps':trainer.observed_optimizer_steps,
                    'validation':{k:float(v) for k,v in trainer.metrics.items()}}
            history.append(record);save(out/'observed_history.json',history)
            save(out/'optimizer_step_batch_indices.json',trainer.optimizer_step_batch_indices)
            save(output/'progress.json',{'seed':seed,'epoch':epoch,'epochs':p['epochs'],
                 'completed_seeds':[r['seed'] for r in conditions],
                 'actual_batches':trainer.observed_batches,'actual_optimizer_steps':trainer.observed_optimizer_steps})
        model.add_callback('on_train_start',on_start)
        model.add_callback('on_train_batch_start',on_batch_start)
        model.add_callback('on_train_batch_end',on_batch_end)
        model.add_callback('on_fit_epoch_end',on_fit)
        current=time.perf_counter()
        returned=model.train(trainer=ObservedTrainer,data=str(data),project=str(output),name=name,
                             exist_ok=False,device=0,seed=seed,epochs=p['epochs'],**p['train_kwargs'])
        trainer=model.trainer
        csv_path=out/'results.csv';rows=list(csv.DictReader(csv_path.open()))
        assert len(rows)==len(history)==p['epochs']
        assert [int(r['epoch']) for r in rows]==list(range(1,p['epochs']+1))
        assert trainer.observed_batches==expected_batches*p['epochs'] and trainer.observed_optimizer_steps>0
        last=out/'weights/last.pt';best=out/'weights/best.pt'
        assert last.is_file() and best.is_file()
        save(out/'optimizer_step_batch_indices.json',trainer.optimizer_step_batch_indices)
        record={'seed':seed,'epochs':len(rows),'checkpoint_rule':p['checkpoint_selection'],
                'checkpoint':str(last),'checkpoint_sha256':sha(last),'archived_best_sha256':sha(best),
                'initial_state_digest':trainer.initial_model_digest,'actual_training_batches':trainer.observed_batches,
                'actual_optimizer_steps':trainer.observed_optimizer_steps,
                'optimizer_step_schedule_sha256':sha(out/'optimizer_step_batch_indices.json'),
                'last_epoch_validation':{k:float(v) for k,v in rows[-1].items() if k.startswith('metrics/')},
                'trainer_returned_archived_best_metrics':returned.results_dict,
                'training_csv_sha256':sha(csv_path),'effective_args_sha256':sha(out/'args.yaml'),
                'elapsed_s':time.perf_counter()-current}
        conditions.append(record);save(out/'condition_complete.json',record)
        print(json.dumps({k:v for k,v in record.items() if k!='trainer_returned_archived_best_metrics'}),flush=True)
        del model,trainer;torch.cuda.empty_cache()
    assert [r['seed'] for r in conditions]==p['seeds']
    freeze={'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(pp),
            'prepared_manifest_sha256':sha(manifest_path),'conditions':conditions,
            'all_seeds_retained':True,'source_Toros_or_candidate_final_forward_before_freeze':False}
    save(output/'all_checkpoints_frozen_before_video.json',freeze)
    result={'status':'ALL_THREE_COWS2021_SEEDS_10_EPOCHS_COMPLETE_FROZEN_BEFORE_VIDEO',
            'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(pp),'conditions':conditions,
            'freeze_sha256':sha(output/'all_checkpoints_frozen_before_video.json'),
            'data_roles':dict(counts),'torch':torch.__version__,'ultralytics':ultralytics.__version__,
            'device':torch.cuda.get_device_name(0),'elapsed_s':time.perf_counter()-started,
            'scope':p['scope'],'candidate_final_image_pixels_accessed':False,'whole_goal_complete':False}
    save(output/'summary.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='conditions'}),flush=True)


if __name__=='__main__':main()
