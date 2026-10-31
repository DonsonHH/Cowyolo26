from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1];plan=json.loads((ROOT/'protocol/run_v1.json').read_text());rows=plan['Cows_training_images']
indices=[]
for identity in plan['Cows_training_IDs'][:6]:
 candidates=[index for index,row in enumerate(rows)if row['publisher_identity']==identity];indices.extend([candidates[0],candidates[-1]])
protocol={'status':'SOURCE_VISUAL_SELECTION_FROZEN_BEFORE_FIRST_MODEL_FORWARD','created_UTC':datetime.now(timezone.utc).isoformat(),
          'selection':'first_and_last_selected_file_of_first6_frozen_training_IDs','indices':indices,'new_model_forwards':0}
p=ROOT/'protocol/source_visual_v1.json';assert not p.exists();p.write_text(json.dumps(protocol,indent=2)+'\n')
dest=ROOT/'results/source_panels';dest.mkdir(exist_ok=False);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14);files=[]
for page in range(3):
 canvas=Image.new('RGB',(1000,1120),'#f4f6f7');draw=ImageDraw.Draw(canvas);draw.text((15,12),'New training ID source QA | Cows2021 | page'+str(page+1),font=font,fill='#19383d')
 draw.text((15,40),'Fixed training IDs only; future20 pixels closed; no predictions or score-based exclusions.',font=small,fill='#41575b');panels=[]
 for j,index in enumerate(indices[page*4:page*4+4]):
  row=rows[index];path=ROOT/row['relative_file']
  with Image.open(path)as image:rgb=image.convert('RGB')
  rgb.thumbnail((480,465),Image.Resampling.BILINEAR);x=15+(j%2)*495+(480-rgb.width)//2;y=83+(j//2)*510+(465-rgb.height)//2;canvas.paste(rgb,(x,y))
  draw.text((15+(j%2)*495,83+(j//2)*510+475),f"train index{index} | ID{row['publisher_identity']} | {row['day']}",font=small,fill='#19383d')
  panels.append({'source_index':index,'source_file':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rect':[x,y,rgb.width,rgb.height]})
 output=dest/('page'+str(page+1)+'.png');canvas.save(output);files.append({'file':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'panels':panels})
p=ROOT/'results/source_visual_manifest.json';assert not p.exists();p.write_text(json.dumps({'files':files,'panels':12,'actually_viewed':False,'new_model_forwards':0},indent=2)+'\n')
print(json.dumps({'source_QA_panels':12,'new_model_forwards':0}))
