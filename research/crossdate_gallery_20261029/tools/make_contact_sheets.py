from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];STUDY=ROOT/'delivery/results/study_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
FONT='C:/Windows/Fonts/arial.ttf'
def font(n):return ImageFont.truetype(FONT,n)
def sheet(size):return Image.new('RGB',size,'#f6f8fa')
def text(im,xy,s,n=20,color='#17384a'):ImageDraw.Draw(im).text(xy,s,font=font(n),fill=color)
def picture(canvas,path,box):
    with Image.open(path) as im:im.load();photo=ImageOps.contain(im.convert('RGB'),(box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
    x=box[0]+(box[2]-box[0]-photo.width)//2;y=box[1]+(box[3]-box[1]-photo.height)//2
    canvas.paste(photo,(x,y));return {'path':str(Path(path).resolve()),'sha256':sha(Path(path)),'panel_box':list(box),'picture_box':[x,y,x+photo.width,y+photo.height]}
out=ROOT/'results/source_review';out.mkdir(exist_ok=False);record=[];index=load(STUDY/'index.json')
im=sheet((1520,1250));text(im,(22,18),'Fixed Aug19 registration gallery: all 30 camera1 crops',28)
panels=[]
for yi,identity in enumerate(sorted({r['identity'] for r in index['gallery_sets']['new_Aug19']})):
    rows=[r for r in index['gallery_sets']['new_Aug19'] if r['identity']==identity];y=75+yi*190
    text(im,(18,y+55),'ID'+identity,20)
    for j,row in enumerate(rows):
        x=118+j*278;panel=picture(im,row['local_path'],(x,y,x+265,y+145));panel.update({'anonymous_id':identity,'source_filename':row['source_filename']});panels.append(panel)
        text(im,(x,y+150),row['source_filename'],17)
file=out/'all30_Aug19_gallery.jpg';im.save(file,quality=95)
record.append({'file':str(file.resolve()),'sha256':sha(file),'panels':panels})
cases=[r for r in load(ROOT/'results/all_false_accept_cases.json') if r['gallery_condition']=='new_Aug19']
assert len(cases)==8
im=sheet((1370,1645));text(im,(20,16),'All 8 Aug19-gallery false accepts: published query ID is outside gallery',25)
text(im,(420,57),'Query crop (author anonymous ID)',19);text(im,(920,57),'Highest-scoring gallery image',19)
panels=[]
for yi,row in enumerate(cases):
    y=96+yi*187;short=row['condition'].replace('_letterbox_trained_seed','').replace('_letterbox_frozen','').replace('_official_frozen','')
    text(im,(18,y+8),short+'  unknown ID'+row['true_anonymous_id'],19,color='#a43f4e')
    text(im,(18,y+40),'candidate ID'+row['candidate_id'],19)
    text(im,(18,y+71),'score '+format(row['cosine'],'.6f'),18)
    text(im,(18,y+101),'threshold '+format(row['threshold'],'.6f'),18)
    text(im,(18,y+131),'excess +'+format(row['cosine']-row['threshold'],'.6f'),17)
    panels.append(picture(im,row['query_local_path'],(350,y,835,y+160)))
    panels.append(picture(im,row['gallery_local_path'],(855,y,1350,y+160)))
    text(im,(350,y+160),Path(row['query_local_path']).name,16)
    text(im,(855,y+160),'gallery ID'+row['candidate_id']+' / '+row['gallery_filename'],16)
file=out/'all8_new_gallery_false_accepts.jpg';im.save(file,quality=95)
record.append({'file':str(file.resolve()),'sha256':sha(file),'panels':panels,'case_rows':cases})
event=next(r for r in index['real_event_queries'] if r['query_id']=='E010_f9790_tid102')
grows=index['gallery_sets']['new_Aug19'];refs=[(i,r) for i,r in enumerate(grows) if r['identity']=='009']
pred=next(r for r in load(STUDY/'C_letterbox_trained_seed28/new_Aug19_real_event_predictions.json') if r['query_id']==event['query_id'])
assert pred['accepted'] and pred['predicted_id']=='009' and pred['verified_identity'] is False
im=sheet((1440,720));text(im,(20,14),'E010 / new Aug19 ID009 gallery: C28 candidate, identity unverified',28)
text(im,(20,53),'score '+format(pred['similarity'],'.6f')+' >= frozen threshold '+format(pred['threshold'],'.6f')+'; retrospective gallery for Aug14 video',20)
rows=[('Real source query f9745',event['local_path'],None)]
rows.extend(('Aug19 / ID009 / '+r['source_filename'],r['local_path'],pred['gallery_image_cosines'][i]) for i,r in refs)
panels=[]
for j,(label,path,score) in enumerate(rows):
    x=20+(j%3)*475;y=100+(j//3)*300
    panels.append(picture(im,path,(x,y,x+455,y+225)));text(im,(x,y+228),label,19)
    if score is not None:text(im,(x,y+257),'C28 cosine '+format(score,'.6f'),18)
file=out/'E010_crossdate_ID009_all5.jpg';im.save(file,quality=95);record.append({'file':str(file.resolve()),'sha256':sha(file),'panels':panels,'prediction':pred})
path=ROOT/'results/source_review_record.json';assert not path.exists()
path.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'pages':record,'actual_image_panels':sum(len(r['panels']) for r in record),'images_not_model_transformed_for_display':True},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pages':len(record),'panels':sum(len(r['panels']) for r in record)}))
