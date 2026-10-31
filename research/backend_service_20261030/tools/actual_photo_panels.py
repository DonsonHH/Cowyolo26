from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
p=load(ROOT/'protocol/run_v1.json');v=load(ROOT/'results/recovery_independent_verification.json');jobs=load(ROOT/'results/actual_job_rows.json')
dest=ROOT/'results/actual_photo_panels';dest.mkdir(exist_ok=False);sheets=[];font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
for run in p['runs']:
 if run['policy']=='foreground_only':continue
 rows=[j for j in jobs if j['run']==run['run']];canvas=Image.new('RGB',(1500,92+max(1,math.ceil(len(rows)/5))*240+40),'#f4f6f7');draw=ImageDraw.Draw(canvas)
 draw.text((15,12),run['run']+' | all'+str(len(rows))+' actual ARM identity photos',font=font,fill='#203c42')
 draw.text((15,42),'Pixels matched to original board photos by audited hashes; reconstructed PNGs. No permanent-ID truth.',font=small,fill='#4b6167');panels=[]
 for i,j in enumerate(rows):
  file=Path(j['photo_file']);assert sha(file)==j['photo_sha256']
  with Image.open(file) as im:im.load();thumb=im.convert('RGB');thumb.thumbnail((280,160),Image.Resampling.BILINEAR)
  x=10+(i%5)*296;y=92+(i//5)*240;canvas.paste(thumb,(x,y))
  draw.text((x,y+163),'photo f'+str(j['source_frame0'])+' | event f'+str(j['event']['frame0']),font=small,fill='#203c42')
  draw.text((x,y+182),'T'+str(j['event']['track_id'])+' | candidate '+j['predicted_id']+' '+format(j['similarity'],'.3f'),font=small,fill='#203c42')
  draw.text((x,y+201),('ACCEPT' if j['accepted'] else 'REJECT')+' | age '+format(j['selected_age_frames']/25,'.1f')+'s',font=small,fill='#9b4d48' if j['accepted'] else '#4b676d')
  panels.append({'photo_file':str(file),'photo_sha256':sha(file),'rect':[x,y,thumb.width,thumb.height]})
 draw.text((15,canvas.height-27),'Public replay; simulated unreadRFID; Aug19 gallery querying Aug14 events is retrospective.',font=small,fill='#4b6167')
 file=dest/(run['run']+'.png');canvas.save(file);sheets.append({'file':str(file.resolve()),'sha256':sha(file),'panels':panels})
assert sum(len(r['panels']) for r in sheets)==v['actual_background_identity_jobs']
save(ROOT/'results/actual_photo_manifest.json',{'files':sheets,'actual_photos':v['actual_background_identity_jobs'],'new_model_forwards':0})
paired=[];unmatched=[]
for repeat in [1,2]:
 current={tuple(j['event'][k] for k in ['frame0','track_id','direction']):j for j in jobs if j['repeat']==repeat and j['policy']=='idle_gate'}
 causal={tuple(j['event'][k] for k in ['frame0','track_id','direction']):j for j in jobs if j['repeat']==repeat and j['policy']=='low_priority_parallel'}
 for key in sorted(set(current)|set(causal)):
  if key not in current or key not in causal:
   unmatched.append({'repeat':repeat,'event_key':key,'present_policy':'idle_gate' if key in current else 'low_priority_parallel'});continue
  a=current[key];b=causal[key];paired.append({'repeat':repeat,'event':a['event'],'idle_gate':a,'low_priority_parallel':b,'different_photo_frame':a['source_frame0']!=b['source_frame0'],
   'different_provisional_ID':a['predicted_id']!=b['predicted_id'],'score_delta_parallel_minus_idle':b['similarity']-a['similarity'],'accepted_idle_gate':a['accepted'],'accepted_low_priority_parallel':b['accepted']})
save(ROOT/'results/paired_identity_observations.json',{'status':'ALL_EXACT_EVENT_KEYS_PAIRED_WITH_UNMATCHED_RETAINED','created_UTC':datetime.now(timezone.utc).isoformat(),'pairs':paired,'unmatched':unmatched,
 'paired_events':len(paired),'unmatched_events':len(unmatched),'same_source_repeats_not_unique_cows':True,'permanent_ID_accuracy_estimated':False,'gallery_and_threshold_unchanged':True})
print(json.dumps({'contact_sheets':len(sheets),'actual_photos':v['actual_background_identity_jobs'],'paired_events':len(paired),'unmatched_events':len(unmatched)}))
