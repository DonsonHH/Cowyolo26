"""Inspection sheets of every unique runtime crop; labels are candidates only."""
from pathlib import Path
from datetime import datetime,timezone
from collections import OrderedDict
import hashlib,json,math
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1]
jobs=json.loads((ROOT/'results/actual_job_rows.json').read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
groups=OrderedDict()
for job in jobs:
 path=Path(job['photo_file']);assert sha(path)==job['photo_sha256']
 item=groups.setdefault(job['photo_sha256'],{'path':str(path),'sha256':job['photo_sha256'],'frame0':job['source_frame0'],'contexts':[]})
 item['contexts'].append({key:job[key]for key in['run','identity_model','predicted_id','similarity','accepted']})
assert len(groups)==13 and len(jobs)==40
out=ROOT/'results/actual_photos';out.mkdir(exist_ok=False)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
title=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
items=list(groups.values());pages=[]
for page_index in range(math.ceil(len(items)/8)):
 batch=items[page_index*8:page_index*8+8]
 canvas=Image.new('RGB',(1320,640),'white');draw=ImageDraw.Draw(canvas)
 draw.text((18,12),'Runtime crops: 13 unique PNGs from 40 jobs - identity GT unavailable',font=title,fill='#17283b')
 draw.text((18,42),f'Page {page_index+1}; candidate labels show fixed model outputs, not verified cow IDs.',font=font,fill='#43536a')
 for i,item in enumerate(batch):
  column,row=i%4,i//4;x=column*330;y=78+row*270
  draw.rectangle((x+5,y,x+324,y+258),outline='#c9d2db',width=1)
  with Image.open(item['path'])as source:thumb=ImageOps.contain(source.convert('RGB'),(304,170),Image.Resampling.LANCZOS)
  canvas.paste(thumb,(x+13+(304-thumb.width)//2,y+7+(170-thumb.height)//2))
  draw.text((x+14,y+181),f"PNG {page_index*8+i+1:02d} | frame0 {item['frame0']}",font=font,fill='#17283b')
  labels=sorted({(q['identity_model'],q['predicted_id'],round(q['similarity'],4),q['accepted'])for q in item['contexts']})
  for j,(model,candidate,score,accepted)in enumerate(labels):
   draw.text((x+14,y+202+j*20),f"{model} candidate {candidate} | {score:.4f} | {'accept'if accepted else'reject'}",font=font,fill='#275f8f'if model=='old'else'#99551d')
 path=out/f'photos_{page_index+1:02d}.png';canvas.save(path)
 pages.append({'file':str(path.resolve()),'sha256':sha(path),'source_photo_sha256':[item['sha256']for item in batch]})
manifest={'status':'ALL13_UNIQUE_RUNTIME_PHOTO_CROPS_RENDERED_WITH_CANDIDATE_ONLY_LABELS',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_jobs':40,'unique_photos':13,'pages':pages,
 'source_photos':items,'visually_reviewed':False,'new_model_forwards':0,'independent_identity_GT':False}
with(ROOT/'results/photo_panel_manifest.json').open('x',encoding='utf-8')as f:json.dump(manifest,f,indent=2);f.write('\n')
print(json.dumps({'status':manifest['status'],'pages':[p['file']for p in pages],'new_model_forwards':0}))
