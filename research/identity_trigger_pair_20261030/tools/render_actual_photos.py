from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
import hashlib,json,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
jobs=load(ROOT/'results/actual_job_rows.json');groups=defaultdict(list)
for j in jobs:groups[j['photo_sha256']].append(j)
out=ROOT/'results/actual_photo_panels';out.mkdir(exist_ok=False);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14);records=[];items=sorted(groups.items(),key=lambda x:(x[1][0]['source_frame0'],x[0]))
for page in range(math.ceil(len(items)/6)):
 canvas=Image.new('RGB',(1200,1120),'#f8f9fa');d=ImageDraw.Draw(canvas);d.text((20,15),'Actual trigger photos: every unique saved image; all repeated jobs mapped in manifest',font=font,fill='#172127')
 for pos,(digest,rows)in enumerate(items[6*page:6*page+6]):
  first=rows[0];x=20+(pos%2)*600;y=60+(pos//2)*340;photo=Path(first['photo_file']);assert sha(photo)==digest
  with Image.open(photo)as image:image=image.convert('RGB');wh=image.size;pixel=hashlib.sha256(image.tobytes()).hexdigest();image.thumbnail((555,235));canvas.paste(image,(x+(555-image.width)//2,y+75+(235-image.height)//2))
  d.text((x,y),f"Frame {first['source_frame0']}  selected age {first['selected_age_frames']} frames  copies {len(rows)}",font=font,fill='#172127')
  for line,model in enumerate(['old','new']):
   rr=[r for r in rows if r['identity_model']==model];caption=model+': '+(', '.join(sorted({f"ID{r['predicted_id']} {r['similarity']:.3f} "+('ACCEPT'if r['accepted']else'REJECT')for r in rr}))if rr else'no matching photo in this model')
   d.text((x,y+24+line*21),caption,font=small,fill='#4d555b')
  records.append({'photo_sha256':digest,'RGB_sha256':pixel,'WH':list(wh),'example_file':str(photo),'jobs':[{'run':r['run'],'model':r['identity_model'],'event':r['event'],'photo_file':r['photo_file']}for r in rows]})
 d.text((20,1090),'All outputs are candidates. Permanent event IDs are unavailable; repeated photos are not independent cows.',font=small,fill='#4d555b');canvas.save(out/f'page{page+1}.png')
v={'status':'ALL_UNIQUE_ACTUAL_TRIGGER_PHOTOS_RENDERED_WITH_ALL_JOBS_MAPPED','created_UTC':datetime.now(timezone.utc).isoformat(),'actual_jobs':len(jobs),'unique_photos':len(items),'records':records,'pages':[{'file':str(p.resolve()),'sha256':sha(p)}for p in sorted(out.glob('*.png'))],'new_model_forwards':0};target=ROOT/'results/photo_panel_manifest.json';assert not target.exists();target.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]));print(json.dumps({'jobs':len(jobs),'unique_photos':len(items),'pages':len(v['pages'])}))
