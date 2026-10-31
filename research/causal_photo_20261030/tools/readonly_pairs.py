from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,math
from PIL import Image,ImageDraw,ImageFont
import numpy as np
from causal_selector import CausalSelector
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
p=load(ROOT/'protocol/run_v1.json');m=load(ROOT/'results/payload_manifest.json');assert sha(ROOT/'protocol/run_v1.json')==m['protocol_sha256']
trace=Path(p['local_readonly_source']['trace']);assert sha(trace)==p['local_readonly_source']['trace_sha256']
camera=PROJECT/'pynq_periodic_joint_20261030/camera_delivery';manifest=load(camera/'manifest.json');assert sha(camera/'manifest.json')==p['local_readonly_source']['camera_manifest_sha256']
for row in manifest:assert sha(camera/row['file'])==row['sha256']
t=json.loads(gzip.decompress(trace.read_bytes()));byframe=defaultdict(list);events=defaultdict(list)
for row in t['post_tracker']:byframe[row['frame0']].append(row)
for event in t['handoff_events']:
 if 8912<=event['frame0']<=10873:events[event['frame0']].append(event)
dest=ROOT/'results/readonly_photos';dest.mkdir(exist_ok=False);selector=CausalSelector();pairs=[]
for frame in range(8915,10874,5):
 selector.observe(frame,byframe[frame])
 for event in events[frame]:
  selection=selector.choose(frame,event['track_id']);pair={'event':event,'selection':selection}
  for kind in ['current','selected']:
   row=selection[kind];x,y,z,w=row['xyxy'];crop=[max(0,math.floor(x-870)),max(0,math.floor(y)),min(1050,math.ceil(z-870)),min(1440,math.ceil(w))]
   file=camera/'highres'/('f'+str(row['frame0']).zfill(5)+'.jpg')
   with Image.open(file) as im:im.load();photo=im.convert('RGB').crop(crop).transpose(Image.Transpose.ROTATE_270)
   out=dest/('event'+str(len(pairs)).zfill(2)+'_'+kind+'_f'+str(row['frame0'])+'.png');photo.save(out,compress_level=0)
   gray=np.asarray(photo.convert('L').resize((128,128),Image.Resampling.BILINEAR),dtype=np.float64)
   lap=gray[1:-1,:-2]+gray[1:-1,2:]+gray[:-2,1:-1]+gray[2:,1:-1]-4*gray[1:-1,1:-1]
   pair[kind]={'file':str(out.relative_to(ROOT).as_posix()),'sha256':sha(out),'native_JPEG_sha256':sha(file),'source_frame0':row['frame0'],'native_crop_xyxy':crop,'photo_size_WH':list(photo.size),'fixed128_laplacian_variance_proxy':float(lap.var()),'photo_pixel_sha256':hashlib.sha256(photo.tobytes()).hexdigest()}
  pairs.append(pair)
save(ROOT/'results/readonly_pairs.json',{'created_UTC':datetime.now(timezone.utc).isoformat(),'status':'FROZEN_SELECTOR_PAIRED_ALL10_EXISTING_O8_DEVELOPMENT_EVENTS','protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'pairs':pairs,'JPEG_manifest_files_verified':len(manifest),'changed_photo_frames':sum(r['current']['source_frame0']!=r['selected']['source_frame0'] for r in pairs),'new_model_forwards':0,'new_training_updates':0,'permanent_identity_GT':False,'whole_goal_complete':False})
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14);panels=[]
for page in range(2):
 canvas=Image.new('RGB',(1100,1160),'#f4f6f7');draw=ImageDraw.Draw(canvas);draw.text((15,12),'All10 event pairs | CURRENT vs PAST-ONLY selected | page'+str(page+1),font=font,fill='#203c42')
 draw.text((15,41),'No identity truth. Geometry proxies do not prove full-body visibility or identity correctness.',font=small,fill='#4b6167')
 rects=[]
 for k,pair in enumerate(pairs[page*5:page*5+5]):
  top=82+k*210
  for col,kind in enumerate(['current','selected']):
   row=pair[kind];file=ROOT/row['file']
   with Image.open(file) as im:im.load();thumb=im.convert('RGB');thumb.thumbnail((520,160),Image.Resampling.BILINEAR)
   x=15+col*550;canvas.paste(thumb,(x,top));q=pair['selection'][kind]
   draw.text((x,top+163),kind+' f'+str(row['source_frame0'])+' | event f'+str(pair['event']['frame0'])+' T'+str(pair['event']['track_id']),font=small,fill='#203c42')
   draw.text((x,top+183),'edge '+format(q['minimum_edge_margin_px'],'.1f')+'px | overlap '+format(q['max_other_box_overlap_fraction'],'.2f')+' | area '+str(round(q['visible_box_area_px2'])),font=small,fill='#4b6167')
   rects.append({'file':str(file.resolve()),'sha256':sha(file),'rect':[x,top,thumb.width,thumb.height]})
 file=dest/('all_pairs_page'+str(page+1)+'.png');canvas.save(file);panels.append({'file':str(file.resolve()),'sha256':sha(file),'panels':rects})
save(ROOT/'results/readonly_visual_manifest.json',{'files':panels,'panels':20,'actually_viewed':False})
print(json.dumps({'events':len(pairs),'changed_frames':sum(r['current']['source_frame0']!=r['selected']['source_frame0'] for r in pairs),'selected_ages':[r['selection']['selected_age_frames'] for r in pairs],'new_model_forwards':0}))
