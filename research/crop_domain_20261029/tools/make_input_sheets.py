from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from crop_rules import apply_rule
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
audit=json.loads((ROOT/'results/input_audit.json').read_text());p=json.loads((ROOT/'protocol/study_v1.json').read_text())
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def txt(canvas,x,y,s,n=20):ImageDraw.Draw(canvas).text((x,y),s,font=font(n),fill='#16384a')
def paste(canvas,photo,box):
    fit=ImageOps.contain(photo,(box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
    x=box[0]+(box[2]-box[0]-fit.width)//2;y=box[1]+(box[3]-box[1]-fit.height)//2;canvas.paste(fit,(x,y))
out=ROOT/'results/source_review';out.mkdir(exist_ok=False);records=[]
rows=audit['groups']['validation_gallery'];im=Image.new('RGB',(1510,1080),'#f6f8fa');txt(im,20,14,'Fixed Aug17 validation gallery: all 25 camera1 images',28);panels=[]
for yi,identity in enumerate(sorted({r['identity'] for r in rows})):
    txt(im,15,100+yi*196,'ID'+identity,20)
    for j,row in enumerate([r for r in rows if r['identity']==identity]):
        x=110+j*279;y=75+yi*196;path=Path(row['local_path'])
        with Image.open(path) as photo:photo.load();paste(im,photo.convert('RGB'),(x,y,x+270,y+153))
        txt(im,x,y+155,row['source_filename'],17);panels.append({'source_path':str(path.resolve()),'source_sha256':sha(path),'box':[x,y,x+270,y+153]})
file=out/'all25_validation_gallery_Aug17.jpg';im.save(file,quality=95);records.append({'path':str(file.resolve()),'sha256':sha(file),'panels':panels})
examples=[('validation_gallery',audit['groups']['validation_gallery'][0],'Aug17 gallery / ID007'),
('validation_query',next(r for r in audit['groups']['validation_query'] if r['identity']=='007'),'Aug18 known query / ID007'),
('validation_query',next(r for r in audit['groups']['validation_query'] if r['identity']=='012'),'Aug18 gallery-excluded / ID012'),
('real_event_query',audit['groups']['real_event_query'][0],'Real E001 / identity unverified')]
im=Image.new('RGB',(1530,1130),'#f6f8fa');txt(im,20,10,'Prespecified geometry controls before encoder preprocessing',27)
names=['P0 original','P1 trim8% each edge / both','P2 query center70x80','P3 query180 / control']
for j,name in enumerate(names):txt(im,12+j*382,54,name,18)
panels=[]
for yi,(group,row,label) in enumerate(examples):
    path=Path(row['local_path'])
    with Image.open(path) as source:source.load();source=source.convert('RGB')
    y=98+yi*252
    for j,rule in enumerate(p['crop_rules']):
        image,crop=apply_rule(source,rule,group);x=12+j*382
        paste(im,image,(x,y,x+367,y+183));txt(im,x,y+186,label,17);txt(im,x,y+214,'box '+str(crop['crop_box']),16)
        panels.append({'source_path':str(path.resolve()),'source_sha256':sha(path),'group':group,'rule':rule['name'],
        'transformed_pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest(),'crop':crop,'box':[x,y,x+367,y+183]})
file=out/'fixed_crop_examples.jpg';im.save(file,quality=95);records.append({'path':str(file.resolve()),'sha256':sha(file),'panels':panels})
path=ROOT/'results/source_review_record.json';assert not path.exists();path.write_text(json.dumps({'pages':records,'actual_image_panels':41},indent=2)+'\n')
print(json.dumps({'pages':2,'image_panels':41}))
