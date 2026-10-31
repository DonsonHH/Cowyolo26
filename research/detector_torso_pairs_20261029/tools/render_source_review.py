from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import math,json,hashlib,gzip
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'delivery/results/pairs'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def text(im,xy,s,n=18,fill='#153849'):ImageDraw.Draw(im).text(xy,s,font=font(n),fill=fill)
def fit(canvas,photo,box):
    scaled=ImageOps.contain(photo,(box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
    x=box[0]+(box[2]-box[0]-scaled.width)//2;y=box[1]+(box[3]-box[1]-scaled.height)//2;canvas.paste(scaled,(x,y))
def reference_view(native,reference):
    x,y,w,h,theta=reference['bbox_xywh_angle_rad'];cx=x+w/2;cy=y+h/2;long=max(w,h);short=min(w,h)
    angle=(theta+(math.pi/2 if h>w else 0))%math.pi;ow=max(1,math.ceil(min(800,long)));oh=max(1,round(ow*short/long))
    c=math.cos(angle);s=math.sin(angle)
    inverse=[c*long/ow,-s*short/oh,cx-c*long/2+s*short/2,
             s*long/ow,c*short/oh,cy-s*long/2-c*short/2]
    photo=native.transform((ow,oh),Image.Transform.AFFINE,inverse,resample=Image.Resampling.BILINEAR,fillcolor=(127,127,127))
    return photo,{'output_size_WH':[ow,oh],'inverse_affine':inverse,'headtail_direction_known':False}
dest=ROOT/'results/source_review';dest.mkdir(exist_ok=False);cases=load(OUT/'case_selection.json');record=[]
for page in range(math.ceil(len(cases)/3)):
    subset=cases[page*3:page*3+3];canvas=Image.new('RGB',(1530,1090),'#f5f8fa')
    text(canvas,(15,10),'Source / actual detector crop / rotated reference: cases '+str(page*3+1)+'-'+str(page*3+len(subset)),26)
    text(canvas,(15,47),'Green: published body reference. Orange: detector crop. Reference is a rectangle, not segmentation; head-tail unknown.',18)
    panels=[]
    for j,case in enumerate(subset):
        top=90+j*320;source=ROOT/'delivery'/case['source_file_relative'];assert sha(source)==case['source_sha256']
        with Image.open(source) as im:im.load();native=im.convert('RGB')
        ref=case['reference'];pair=case['pair'];context=native.copy();draw=ImageDraw.Draw(context)
        draw.line([tuple(p) for p in ref['full_native_quad']]+[tuple(ref['full_native_quad'][0])],fill='#30d398',width=5)
        for pred in case['all_native_predictions']:draw.rectangle(pred['native_xyxy'],outline='#f4a44d',width=3)
        label=case['condition']+' / '+source.name+' / '+ref['annotation_key'].split(':')[-1]
        text(canvas,(15,top-8),label,19);text(canvas,(510,top-8),'Actual integer crop',19);text(canvas,(1020,top-8),'Undirected rotated reference',19)
        box=[15,top+22,495,top+292];fit(canvas,context,box)
        panels.append({'kind':'native_context','source_path':str(source.resolve()),'source_sha256':sha(source),'panel_box':box,'annotation_key':ref['annotation_key']})
        if pair['matched_prediction_index'] is not None:
            crop=native.crop(pair['crop_box']);box=[510,top+22,990,top+247];fit(canvas,crop,box)
            panels.append({'kind':'actual_detector_crop','source_path':str(source.resolve()),'source_sha256':sha(source),'panel_box':box,'crop_box':pair['crop_box'],
                'RGB_pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest()})
            m=pair['crop_metrics'];text(canvas,(510,top+253),'coverage '+format(m['reference_coverage'],'.3f')+' / exterior '+format(m['reference_exterior_fraction'],'.3f'),17)
            text(canvas,(510,top+279),'AABB IoU '+format(pair['matched_reference_AABB_IoU'],'.3f'),17)
        else:
            text(canvas,(560,top+95),'NO MATCH AT IoU >= 0.5',21,fill='#ad4051')
            text(canvas,(530,top+145),'Blank panel retained as a missed reference',17)
        photo,warp=reference_view(native,ref);box=[1020,top+22,1500,top+247];fit(canvas,photo,box)
        panels.append({'kind':'rotated_reference_visual','source_path':str(source.resolve()),'source_sha256':sha(source),'panel_box':box,
            'RGB_pixel_sha256':hashlib.sha256(photo.tobytes()).hexdigest(),'reference':ref,'warp':warp})
        text(canvas,(1020,top+252),'visible fraction '+format(ref['visible_reference_fraction'],'.3f'),17)
        text(canvas,(1020,top+278),'ideal AABB exterior '+format(ref['ideal_AABB_exterior_fraction'],'.3f'),17)
    file=dest/('case_page'+str(page+1).zfill(2)+'.jpg');canvas.save(file,quality=95)
    record.append({'path':str(file.resolve()),'sha256':sha(file),'panels':panels,'case_indices':list(range(page*3,page*3+len(subset)))})
probe=load(ROOT/'delivery/results/input_controls/rows.json');geometry=loadgz(OUT/'source_geometry.json.gz')['val'];by_image={r['file_name']:r for r in geometry}
p=load(ROOT/'protocol/pairs_v1.json');names=p['fixed_validation_sample_names']
for page in range(2):
    canvas=Image.new('RGB',(1470,1690),'#f5f8fa');text(canvas,(15,10),'Seed26 fixed-source control: CW90, rect=True, conf0.2',28)
    text(canvas,(15,50),'320 input versus 640 input; overlays restored to the same native pixels. No source-case replacement.',19)
    panels=[]
    for j,filename in enumerate(names[page*4:page*4+4]):
        source=OUT/'case_sources'/filename
        with Image.open(source) as im:im.load();native=im.convert('RGB')
        for col,size in enumerate([320,640]):
            r=next(r for r in probe if r['condition']=='seed26' and r['file_name']==filename and r['config']['orientation']=='clockwise90' and r['config']['rect'] is True and r['config']['imgsz']==size and not r['config']['repeat'])
            view=native.copy();draw=ImageDraw.Draw(view)
            for ref in by_image[filename]['references']:draw.line([tuple(p) for p in ref['full_native_quad']]+[tuple(ref['full_native_quad'][0])],fill='#30d398',width=5)
            for pred in r['predictions']:draw.rectangle(pred['native_xyxy'],outline='#f4a44d',width=4)
            x=15+col*730;y=105+j*385
            text(canvas,(x,y),filename+' / '+str(size)+' / matched '+str(r['matched'])+'/'+str(r['references']),21)
            box=[x,y+32,x+710,y+365];fit(canvas,view,box)
            panels.append({'kind':'input_size_same_source_control','source_path':str(source.resolve()),'source_sha256':sha(source),'panel_box':box,
                'condition':'seed26','input_size':size,'probe_config_index':r['config_index'],'matched':r['matched'],'references':r['references']})
    file=dest/('fixed8_320vs640_page'+str(page+1)+'.jpg');canvas.save(file,quality=95);record.append({'path':str(file.resolve()),'sha256':sha(file),'panels':panels})
file=ROOT/'results/source_review_record.json';assert not file.exists();file.write_text(json.dumps({'pages':record,
'actual_image_panels':sum(len(r['panels']) for r in record),'missed_reference_blank_slots_not_counted_as_images':sum(c['pair']['matched_prediction_index'] is None for c in cases)},indent=2)+'\n')
print(json.dumps({'contact_pages':len(record),'actual_image_panels':sum(len(r['panels']) for r in record),'cases':len(cases)}))
