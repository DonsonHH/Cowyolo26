from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1];plan=json.loads((ROOT/'protocol/run_v1.json').read_text());dest=ROOT/'results/actual_training_panels';dest.mkdir(exist_ok=False)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14);files=[]
for condition in plan['conditions']:
 name=condition['name'];folder=ROOT/'delivery/results/training'/name;first=json.loads((folder/'actual_updates.jsonl').read_text().splitlines()[0])
 with np.load(folder/'first4_actual_training_inputs.npz')as archive:inputs=archive['input'].copy()
 assert inputs.shape==(4,3,224,224);canvas=Image.new('RGB',(1000,360),'#f4f6f7');draw=ImageDraw.Draw(canvas)
 draw.text((15,12),name+' | first4 of actual first training batch | 224px input',font=font,fill='#19383d')
 draw.text((15,40),'Inverse normalised for viewing; saved tensor bytes unchanged. No model predictions.',font=small,fill='#41575b');panels=[]
 for index,value in enumerate(inputs):
  rgb=np.rint(np.clip((value*np.array([.229,.224,.225],np.float32)[:,None,None]+np.array([.485,.456,.406],np.float32)[:,None,None])*255,0,255)).astype(np.uint8).transpose(1,2,0).copy()
  x,y=15+index*247,80;canvas.paste(Image.fromarray(rgb),(x,y));label=first['identity_labels'][index].split(':')[-1];day=first['dates'][index]
  draw.text((x,310),'ID'+label+' | '+day,font=small,fill='#19383d');panels.append({'input_index':index,'tensor_sha256':hashlib.sha256(value.tobytes()).hexdigest(),'display_RGB_sha256':hashlib.sha256(rgb.tobytes()).hexdigest(),'rect':[x,y,224,224]})
 p=dest/(name+'.png');canvas.save(p);files.append({'condition':name,'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_tensor_file':str(folder/'first4_actual_training_inputs.npz'),'panels':panels})
p=ROOT/'results/training_visual_manifest.json';assert not p.exists();p.write_text(json.dumps({'files':files,'panels':24,'actually_viewed':False,'new_model_forwards':0},indent=2)+'\n');print(json.dumps({'sheets':6,'actual_training_panels':24,'new_model_forwards':0}))
