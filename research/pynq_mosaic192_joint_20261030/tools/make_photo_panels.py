"""All actual photos, including rejections, with independently bound vectors."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'delivery'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');p=load(ROOT/'protocol/run_v1.json')
assert v['all_runtime_photos_inputs_features_scores_recomputed']
fontpath=Path('C:/Windows/Fonts/arial.ttf');font=ImageFont.truetype(str(fontpath),17);small=ImageFont.truetype(str(fontpath),13)
dest=ROOT/'results/photo_panels';dest.mkdir(exist_ok=False);records=[]
for run in p['runs']:
    if run['policy']=='foreground_only':continue
    folder=OUT/'results'/run['run']/'background';jobs=load(folder/'record.json')['jobs']
    width=1500;cellw=296;cellh=235;header=92;rows=math.ceil(len(jobs)/5)
    canvas=Image.new('RGB',(width,header+max(1,rows)*cellh+45),'#f4f6f7');draw=ImageDraw.Draw(canvas)
    draw.text((15,12),run['run']+' | all'+str(len(jobs))+' actual same-board identity jobs',font=font,fill='#203c42')
    draw.text((15,40),'Predicted IDs are provisional: no permanent-ID ground truth. All accepted and rejected photos retained.',font=small,fill='#485c63')
    panels=[]
    for i,job in enumerate(jobs):
        file=folder/job['photo_file'];assert sha(file)==job['photo_sha256']
        with Image.open(file) as im:im.load();photo=im.convert('RGB');photo.thumbnail((280,160),Image.Resampling.BILINEAR)
        x=10+(i%5)*cellw;y=header+(i//5)*cellh
        canvas.paste(photo,(x,y));draw.text((x,y+164),'f'+str(job['source_frame0'])+' T'+str(job['event']['track_id']),font=small,fill='#203c42')
        draw.text((x,y+183),'candidate '+job['predicted_id']+' score '+format(job['similarity'],'.3f'),font=small,fill='#203c42')
        draw.text((x,y+201),('ACCEPT' if job['accepted'] else 'REJECT')+' | queue '+format(job['queue_wait_ms']/1000,'.2f')+'s',font=small,fill='#9b4d48' if job['accepted'] else '#4b676d')
        panels.append({'run':run['run'],'source_frame0':job['source_frame0'],'track_id':job['event']['track_id'],'candidate':job['predicted_id'],
            'accepted':job['accepted'],'photo_path':str(file.resolve()),'photo_sha256':sha(file),'rect':[x,y,photo.width,photo.height]})
    draw.text((15,canvas.height-28),'Public high-resolution replay; simulated unreadRFID. Aug19 gallery vs Aug14 events is retrospective.',font=small,fill='#485c63')
    file=dest/(run['run']+'.png');canvas.save(file)
    records.append({'file':str(file.resolve()),'sha256':sha(file),'panels':panels})
assert sum(len(r['panels']) for r in records)==v['actual_background_identity_jobs']
target=dest/'manifest.json';target.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'files':records,
    'actual_photos':sum(len(r['panels']) for r in records),'new_network_forwards':0,'whole_goal_complete':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'contact_sheets':len(records),'actual_photos':sum(len(r['panels']) for r in records)}))
