from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];STUDY=ROOT/'delivery/results/study';sys.path.insert(0,str(ROOT/'tools'))
from crop_rules import apply_rule
p=json.loads((ROOT/'protocol/study_v1.json').read_text());idx=json.loads((STUDY/'input_index.json').read_text());frozen=json.loads((STUDY/'selection_frozen.json').read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def txt(canvas,xy,s,n=20,color='#16384a'):ImageDraw.Draw(canvas).text(xy,s,font=font(n),fill=color)
def image(canvas,path,box,rule,group):
    with Image.open(path) as im:im.load();im,crop=apply_rule(im,rule,group)
    fit=ImageOps.contain(im,(box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
    x=box[0]+(box[2]-box[0]-fit.width)//2;y=box[1]+(box[3]-box[1]-fit.height)//2;canvas.paste(fit,(x,y))
    return {'source_path':str(Path(path).resolve()),'source_sha256':sha(path),'rule':rule['name'],'group':group,
        'transformed_pixel_sha256':hashlib.sha256(im.tobytes()).hexdigest(),'crop':crop,'panel_box':list(box)}
out=ROOT/'results/source_review'
cases=json.loads((ROOT/'results/selected_rule_false_accept_cases.json').read_text());assert len(cases)==9
canvas=Image.new('RGB',(1370,1845),'#f6f8fa');txt(canvas,(20,12),'All 9 evaluation false accepts after validation-only selection',27)
txt(canvas,(370,55),'Published query ID outside gallery',19);txt(canvas,(900,55),'Nearest registered gallery image',19)
panels=[]
for y,row in enumerate(cases):
    top=90+y*190;short=row['condition'][0]+(row['condition'].split('seed')[-1] if 'seed' in row['condition'] else '')
    txt(canvas,(18,top+10),short+'  unknown ID'+row['true_anonymous_id'],20,'#a43f4e')
    txt(canvas,(18,top+42),'candidate ID'+row['candidate_id'],19)
    txt(canvas,(18,top+74),'score '+format(row['cosine'],'.6f'),18)
    txt(canvas,(18,top+104),'threshold '+format(row['threshold'],'.6f'),18)
    txt(canvas,(18,top+136),'margin +'+format(row['cosine']-row['threshold'],'.6f'),17)
    rule=next(r for r in p['crop_rules'] if r['name']==row['rule'])
    panels.append(image(canvas,row['query_local_path'],(350,top,835,top+160),rule,'evaluation_query'))
    panels.append(image(canvas,row['gallery_local_path'],(855,top,1350,top+160),rule,'evaluation_gallery'))
    txt(canvas,(350,top+162),Path(row['query_local_path']).name,16);txt(canvas,(855,top+162),'ID'+row['candidate_id']+' / '+Path(row['gallery_local_path']).name,16)
file=out/'all9_validation_selected_errors.jpg';canvas.save(file,quality=95);records=[{'path':str(file.resolve()),'sha256':sha(file),'panels':panels,'cases':cases}]
condition='C_letterbox_trained_seed28';p0=p['crop_rules'][0];p1=p['crop_rules'][1]
query=next(r for r in idx['real_event_query'] if r['query_id']=='E010_f9790_tid102')
directory=STUDY/(condition+'__'+p1['name']);result=next(r for r in json.loads((directory/'real_event_validation_calibrated_predictions.json').read_text()) if r['query_id']==query['query_id'])
assert result['accepted'] and result['predicted_id']=='009' and result['verified_identity'] is False
old=next(r for r in json.loads((STUDY/(condition+'__'+p0['name'])/'real_event_original_fixed_predictions.json').read_text()) if r['query_id']==query['query_id'])
canvas=Image.new('RGB',(1440,1020),'#f6f8fa');txt(canvas,(18,10),'E010 / C28: selected crop retains an anonymous ID009 candidate',27)
panels=[]
panels.append(image(canvas,query['local_path'],(18,70,465,285),p0,'real_event_query'));txt(canvas,(18,290),'P0 query / score '+format(old['similarity'],'.6f'),19)
panels.append(image(canvas,query['local_path'],(493,70,940,285),p1,'real_event_query'));txt(canvas,(493,290),'P1 query / score '+format(result['similarity'],'.6f'),19)
txt(canvas,(965,90),'Frozen validation choice: P1',20);txt(canvas,(965,128),'new threshold '+format(result['threshold'],'.6f'),19)
txt(canvas,(965,170),'Identity unverified',23,'#a43f4e');txt(canvas,(965,213),'Retrospective Aug19 gallery',19);txt(canvas,(965,248),'Aug14 source query f9745',19)
refs=[(i,r) for i,r in enumerate(idx['evaluation_gallery']) if r['identity']=='009']
for j,(i,row) in enumerate(refs):
    x=18+(j%3)*475;y=365+(j//3)*300
    panels.append(image(canvas,row['local_path'],(x,y,x+447,y+215),p1,'evaluation_gallery'))
    txt(canvas,(x,y+220),'Aug19 / ID009 / '+row['source_filename'],18)
    txt(canvas,(x,y+249),'C28 cosine '+format(result['gallery_image_cosines'][i],'.6f'),18)
file=out/'selected_E010_ID009_query_all5.jpg';canvas.save(file,quality=95);records.append({'path':str(file.resolve()),'sha256':sha(file),'panels':panels,'prediction':result})
record=ROOT/'results/case_review_record.json';assert not record.exists();record.write_text(json.dumps({'pages':records,'actual_image_panels':25},indent=2)+'\n')
print(json.dumps({'pages':2,'panels':25,'selected_error_model_query_pairs':9,'distinct_error_queries':len({r['query_id'] for r in cases}),'distinct_unknown_IDs':len({r['true_anonymous_id'] for r in cases})}))
