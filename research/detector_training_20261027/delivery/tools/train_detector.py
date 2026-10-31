"""Public-label detector expansion, fixed20 epochs and all3seeds before video use."""
from pathlib import Path
import csv,hashlib,json,os,shutil,time
import torch,ultralytics
from ultralytics import YOLO

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT=PROJECT/'detector_training'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def save(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,indent=2),encoding='utf-8')


def main():
    os.environ['YOLO_AUTOINSTALL']='false'
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'cache/ultralytics')
    (ROOT/'cache/ultralytics/Ultralytics').mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(4)
    assert torch.cuda.is_available() and ultralytics.__version__=='8.4.63'
    pp=ROOT/'protocol/detector_v1.json';p=json.loads(pp.read_text())
    OUT=ROOT/'results/training';OUT.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    data=PROJECT/'data/opencows2020/derived_detection'
    source=PROJECT/'models/yolo26n.pt'
    assert sha(source)==p['source_weights_sha256']
    manifest=json.loads((data/'manifest.json').read_text())
    roles={s:[r for r in manifest if r['split']==s] for s in ['train','val','dev_test','quarantine_duplicate_of_holdout']}
    assert {k:len(v) for k,v in roles.items()}==p['expected_split_counts']
    assert not {r['sha256'] for r in roles['train']}&{r['sha256'] for r in roles['val']+roles['dev_test']}
    # Audit only actual training/validation image bytes and copied cleaned labels.
    inputs=[]
    for role in ['train','val']:
        for row in roles[role]:
            image=Path(row['image']);label=Path(row['derived_label'])
            assert sha(image)==row['sha256'] and label.is_file()
            for line in label.read_text().splitlines():
                if not line.strip():continue
                cls,cx,cy,w,h=map(float,line.split())
                assert cls==0 and w>0 and h>0 and 0<=cx<=1 and 0<=cy<=1
                assert cx-w/2>=-1e-8 and cx+w/2<=1+1e-8 and cy-h/2>=-1e-8 and cy+h/2<=1+1e-8
            inputs.append({'image':str(image),'split':role,'image_sha256':row['sha256'],'label':str(label),'label_sha256':sha(label)})
    for name in ['data.yaml','manifest.json','summary.json']:
        shutil.copy2(data/name,OUT/name)
    input_record={'protocol_sha256':sha(pp),'source_weights_sha256':sha(source),'rows':inputs,
                  'split_counts':{k:len(v) for k,v in roles.items()},'dataset_manifest_sha256':sha(data/'manifest.json'),
                  'data_yaml_sha256':sha(data/'data.yaml'),'raw_source_video_opened':False,'dev_test_forward_performed':False,
                  'status':'TRAIN_VAL_IMAGE_LABEL_AND_EXACT_DUPLICATE_AUDIT_PASS'}
    save(OUT/'input_audit.json',input_record)
    conditions=[]
    for seed in p['seeds']:
        model=YOLO(str(source))
        assert model.task=='detect'
        training_start=time.perf_counter();optimizer_records=[]
        def record_optimizer(trainer):
            optimizer_records.append({'type':type(trainer.optimizer).__name__,
                   'parameter_groups':[{k:v for k,v in group.items() if k!='params'} for group in trainer.optimizer.param_groups],
                   'nc':trainer.data['nc'],'train_images':len(trainer.train_loader.dataset),'validation_images':len(trainer.test_loader.dataset)})
        model.add_callback('on_train_start',record_optimizer)
        cfg=p['train_kwargs']
        result=model.train(data=str(data/'data.yaml'),project=str(OUT),name=f'seed{seed}',seed=seed,device=0,
                           epochs=p['epochs'],exist_ok=False,**cfg)
        dest=Path(model.trainer.save_dir)
        rows=list(csv.DictReader((dest/'results.csv').open()))
        assert len(rows)==p['epochs'] and [int(r['epoch']) for r in rows]==list(range(1,p['epochs']+1))
        last=dest/'weights/last.pt';best=dest/'weights/best.pt'
        assert last.is_file() and best.is_file() and len(optimizer_records)==1
        record={'seed':seed,'epochs_completed':len(rows),'selected_checkpoint_rule':'Fixed final epoch last.pt for every seed; not selected on video or external counts',
                'checkpoint':str(last),'checkpoint_sha256':sha(last),'saved_validation_best_checkpoint':str(best),
                'saved_validation_best_sha256':sha(best),'video_use_checkpoint':str(last),'elapsed_s':time.perf_counter()-training_start,
                'last_epoch_validation':{k:float(v) for k,v in rows[-1].items() if k.startswith('metrics/')},
                'trainer_return_metrics_for_saved_best':result.results_dict,
                'optimizer':optimizer_records[0],'training_csv_sha256':sha(dest/'results.csv'),
                'effective_args_sha256':sha(dest/'args.yaml')}
        conditions.append(record);save(OUT/f'seed{seed}_training_record.json',record)
        save(OUT/'training_progress.json',{'completed_conditions':conditions,'remaining_seeds':[s for s in p['seeds'] if s>seed]})
        print(json.dumps({'completed_seed':seed,'epochs':len(rows),'last_epoch_validation':record['last_epoch_validation'],
                          'checkpoint_sha256':record['checkpoint_sha256']}),flush=True)
        del model;torch.cuda.empty_cache()
    assert len(conditions)==3
    freeze={'frozen_at_unix':time.time(),'protocol_sha256':sha(pp),'dataset_manifest_sha256':input_record['dataset_manifest_sha256'],
            'conditions':conditions,'video_or_external_inference_performed':False,
            'all_seeds_reported':True,'selection':p['checkpoint_selection']}
    save(OUT/'all_checkpoints_frozen_before_video.json',freeze)
    summary={'status':'COMPLETED_PUBLIC_LABEL_TRAINING_3SEEDS_20EPOCHS','job_id':os.environ['SLURM_JOB_ID'],
             'protocol_sha256':sha(pp),'torch':torch.__version__,'ultralytics':ultralytics.__version__,
             'gpu':torch.cuda.get_device_name(0),'input_audit_sha256':sha(OUT/'input_audit.json'),
             'conditions':conditions,'freeze_sha256':sha(OUT/'all_checkpoints_frozen_before_video.json'),
             'elapsed_seconds':time.perf_counter()-started,'scope':p['scope']}
    save(OUT/'summary.json',summary)
    print(json.dumps({'status':summary['status'],'elapsed_seconds':summary['elapsed_seconds']}),flush=True)


if __name__=='__main__':main()
