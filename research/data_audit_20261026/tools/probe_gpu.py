from pathlib import Path
import os,json,time,sys
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
import torch,cv2,numpy as np
print(json.dumps({'job':os.environ.get('SLURM_JOB_ID'),'hostname':os.uname().nodename,'torch':torch.__version__,'cuda_available':torch.cuda.is_available(),'cuda_device':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}),flush=True)
assert torch.cuda.is_available()
x=torch.ones((64,64),device='cuda');assert float((x@x)[0,0])==64
from ultralytics import YOLO
model=YOLO(str(ROOT/'models/yolo26n.pt'))
r=model.predict(np.zeros((320,320,3),dtype=np.uint8),imgsz=320,device=0,verbose=False)
info={'job':os.environ['SLURM_JOB_ID'],'host':os.uname().nodename,'torch':torch.__version__,'cuda_device':torch.cuda.get_device_name(0),'test_inference':True,'classes':model.names,'params':sum(p.numel() for p in model.model.parameters())}
(OUT/'gpu_probe.json').write_text(json.dumps(info,indent=2),encoding='utf8');print(json.dumps(info),flush=True)
