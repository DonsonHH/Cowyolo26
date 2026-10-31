from pathlib import Path
import os,json,hashlib,time,torch
from ultralytics import YOLO
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'results/detection_pilot';OUT.mkdir(exist_ok=True)
assert torch.cuda.is_available()
model=YOLO(str(ROOT/'models/yolo26n.pt'))
start=time.time()
result=model.train(data=str(ROOT/'data/opencows2020/derived_detection/data.yaml'),epochs=5,imgsz=320,batch=32,device=0,workers=4,project=str(OUT),name='five_epoch_dev',seed=26,deterministic=True,pretrained=True,amp=False,plots=False,save=True,cache=False,close_mosaic=0,patience=5,verbose=False,exist_ok=False)
save=Path(model.trainer.save_dir);best=save/'weights/best.pt'
record={'job_id':os.environ['SLURM_JOB_ID'],'gpu':torch.cuda.get_device_name(0),'epochs_requested':5,'imgsz':320,'batch':32,'seed':26,'input_weights_sha256':'9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef','dataset':str(ROOT/'data/opencows2020/derived_detection/data.yaml'),'split_scope':'development hash-group split; source/augmentation leakage not resolved, no final generalization claim','save_dir':str(save),'best_weights':str(best),'best_sha256':hashlib.sha256(best.read_bytes()).hexdigest(),'elapsed_s':time.time()-start,'metrics':result.results_dict}
(OUT/'training_record.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps(record),flush=True)
