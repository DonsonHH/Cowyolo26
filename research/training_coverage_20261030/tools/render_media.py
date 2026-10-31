from pathlib import Path
from datetime import datetime,timezone
import os,socket,json,hashlib
import cv2,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=ROOT/'results/media';out.mkdir(exist_ok=False)
audit=ROOT/'results/audit';rows=load(audit/'objects.json');s=load(audit/'summary.json');train={r['file_name']:r for r in load(ROOT/'input/train_only.json')}
assert len(rows)==8888
specs=[('Y_median','Region median Y /0-255',np.arange(0,257,8),80),
    ('absolute_median_contrast','Absolute region-background median difference',np.arange(0,257,8),15),
    ('short_side_at192','Native rectangle short side projected at192 /px',np.arange(0,193,8),24),
    ('max_overlap_over_min_area','Rectangle intersection /smaller visible area',np.linspace(0,1.00001,21),.1)]
plt.rcParams['svg.fonttype']='none';fig,axes=plt.subplots(2,2,figsize=(12,8.3));histograms=[]
for panel,(key,label,bins,threshold) in enumerate(specs):
    values=[r[key] for r in rows if r[key] is not None]
    counts,edges,_=axes.flat[panel].hist(values,bins=bins,color='#34847e',edgecolor='white',linewidth=.3)
    assert int(sum(counts))==len(values)
    axes.flat[panel].axvline(threshold,color='#bd616b',linestyle='--',linewidth=1)
    axes.flat[panel].set_xlabel(label,fontsize=9);axes.flat[panel].set_ylabel('Training body rectangles',fontsize=9)
    axes.flat[panel].set_title('N='+str(len(values))+'; fixed proxy boundary='+str(threshold),fontsize=10)
    axes.flat[panel].spines[['top','right']].set_visible(False);axes.flat[panel].grid(axis='y',alpha=.12);axes.flat[panel].set_axisbelow(True)
    histograms.append({'panel':panel,'key':key,'edges':edges.tolist(),'counts':counts.astype(int).tolist(),'threshold':threshold,'samples':len(values)})
fig.suptitle('Training-only coverage:6809 images,8888 labeled body rectangles',fontsize=13,y=.98)
fig.text(.06,.024,'Native unaugmented proxies, not actual training-loader exposures. Rectangles are not body segmentation or occlusion ground truth.',fontsize=8)
fig.text(.06,.007,'No validation, holdout or source-video pixels read. No neural forwards. Dashed boundaries were fixed before audit.',fontsize=8)
fig.subplots_adjust(left=.07,right=.985,top=.91,bottom=.11,wspace=.22,hspace=.32)
fig.savefig(out/'training_coverage_histograms.png',dpi=160);fig.savefig(out/'training_coverage_histograms.svg');plt.close(fig)
selected=[];used=set()
for category,key,reverse in [('low_luminance','Y_median',False),('low_background_contrast','absolute_median_contrast',False),('rectangle_overlap','max_overlap_over_min_area',True),('small192_shortside','short_side_at192',False)]:
    ordered=sorted([r for r in rows if r[key] is not None],key=lambda r:((-r[key]) if reverse else r[key],r['annotation_key']))
    group=[]
    for r in ordered:
        if r['annotation_key'] in used:continue
        used.add(r['annotation_key']);group.append({**r,'selection_category':category})
        if len(group)==3:break
    assert len(group)==3;selected.extend(group)
fontfile=font_manager.findfont('DejaVu Sans');font=ImageFont.truetype(fontfile,17);small=ImageFont.truetype(fontfile,13)
canvas=Image.new('RGB',(1248,1242),'#f4f6f7');draw=ImageDraw.Draw(canvas)
draw.text((16,12),'Training-only examples selected by fixed proxy extrema',font=font,fill='#1a353c')
draw.text((16,38),'Published body rectangles; green is selected. These are not coat-color or occlusion labels.',font=small,fill='#40565f')
panels=[]
for i,r in enumerate(selected):
    image=train[r['file_name']];assert sha(image['image_alias'])==r['source_sha256']
    native=Image.open(image['image_alias']).convert('RGB');thumb=native.resize((384,216),Image.Resampling.BILINEAR);overlay=ImageDraw.Draw(thumb)
    for other in [v for v in rows if v['file_name']==r['file_name']]:
        points=[(a*.3,b*.3) for a,b in other['visible_polygon']];overlay.line(points+[points[0]],fill='#b2c7c5',width=1)
    points=[(a*.3,b*.3) for a,b in r['visible_polygon']];overlay.line(points+[points[0]],fill='#26ef99',width=2)
    x=16+(i%3)*411;y=82+(i//3)*286
    canvas.paste(thumb,(x,y))
    draw.text((x,y+222),r['selection_category']+' | '+r['file_name'],font=small,fill='#1a353c')
    contrast='NA' if r['absolute_median_contrast'] is None else format(r['absolute_median_contrast'],'.1f')
    draw.text((x,y+241),'Y='+format(r['Y_median'],'.1f')+' delta='+contrast+' overlap='+format(r['max_overlap_over_min_area'],'.2f'),font=small,fill='#1a353c')
    draw.text((x,y+259),'short192='+format(r['short_side_at192'],'.1f')+'px; visible='+format(r['visible_reference_fraction'],'.2f'),font=small,fill='#1a353c')
    panels.append({'annotation_key':r['annotation_key'],'selection_category':r['selection_category'],'file_name':r['file_name'],
        'source_sha256':r['source_sha256'],'rect':[x,y,384,216]})
canvas.save(out/'training_proxy_extremes12.png')
(out/'selected_examples.json').write_text(json.dumps(selected,indent=2)+'\n')
data={'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'histograms':histograms,'input_panels':panels,
    'source_training_only':True,'new_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
(out/'media_values.json').write_text(json.dumps(data,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.glob('*'))],indent=2)+'\n')
print(json.dumps({'status':'FOUR_TRAINING_HISTOGRAMS_AND_TWELVE_FIXED_EXTREME_EXAMPLES_RENDERED','new_model_forwards':0}))
