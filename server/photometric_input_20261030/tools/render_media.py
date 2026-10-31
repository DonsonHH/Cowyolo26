"""All six numeric conditions plus all30 preselected actual input panels."""
from pathlib import Path
from datetime import datetime,timezone
import os,socket,json,hashlib
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'results/study_v2';s=load(source/'summary.json')
assert s['actual_total_forwards']==25350
out=ROOT/'results/media';out.mkdir(exist_ok=False)
conditions=['none','gamma07','clahe_y2'];labels=['Original','Gamma0.7','CLAHE-Y2']
colors=['#397e87','#c47b35'];bars=[]
plt.rcParams['svg.fonttype']='none'
fig,axes=plt.subplots(2,2,figsize=(12,8.5))
for panel,key,title in [(0,'TP','Validation: matched torso references /1864'),(1,'unmatched_prediction','Validation: predictions without matching reference')]:
    axis=axes.flat[panel]
    for mi,mode in enumerate(['FP32','QDQ']):
        values=[next(r[key] for r in s['validation_metrics'] if r['condition']==c and r['mode']==mode) for c in conditions]
        columns=axis.bar(np.arange(3)+(mi-.5)*.32,values,width=.29,color=colors[mi],label=mode)
        for ci,(value,b) in enumerate(zip(values,columns)):
            axis.text(b.get_x()+b.get_width()/2,value+max(values)*.015,str(value),ha='center',fontsize=9)
            bars.append({'panel':panel,'condition':conditions[ci],'mode':mode,'metric':key,'value':value,'x':float(b.get_x()),'width':float(b.get_width())})
    axis.set_ylim(0,2100 if panel==0 else max(b['value'] for b in bars if b['panel']==panel)*1.2)
    axis.set_xticks(range(3),labels);axis.set_xlim(-.6,2.6);axis.set_title(title,fontsize=10);axis.legend(frameon=False,fontsize=8)
axis=axes.flat[2]
for mi,mode in enumerate(['FP32','QDQ']):
    values=[next(r['down'] for r in s['video_metrics'] if r['condition']==c and r['mode']==mode and r['scene']=='original' and r['counter']=='handoff_events') for c in conditions]
    columns=axis.bar(np.arange(3)+(mi-.5)*.32,values,width=.29,color=colors[mi],label=mode)
    for ci,(value,b) in enumerate(zip(values,columns)):
        axis.text(b.get_x()+b.get_width()/2,value+.15,str(value),ha='center',fontsize=9)
        bars.append({'panel':2,'condition':conditions[ci],'mode':mode,'metric':'original_down_handoff','value':value,'x':float(b.get_x()),'width':float(b.get_width())})
axis.axhline(12,color='#af5260',linestyle='--',linewidth=.8)
axis.set_xticks(range(3),labels);axis.set_xlim(-.6,2.6);axis.set_ylim(0,14)
axis.set_title('Development source count: human total12, no event GT',fontsize=10);axis.legend(frameon=False,fontsize=8)
axis=axes.flat[3]
for si,(mode,stride,color) in enumerate([('FP32',6,'#397e87'),('QDQ',6,'#c47b35'),('FP32',1,'#8ebdc1'),('QDQ',1,'#e6c49d')]):
    values=[next(r['formal_event_metrics']['TP'] for r in s['video_metrics'] if r['condition']==c and r['mode']==mode and r['scene']=='toros' and r['stride']==stride and r['counter']=='handoff_events') for c in conditions]
    columns=axis.bar(np.arange(3)+(si-1.5)*.18,values,width=.16,color=color,label=mode+('5Hz' if stride==6 else '30Hz'))
    for ci,(value,b) in enumerate(zip(values,columns)):
        axis.text(b.get_x()+b.get_width()/2,value+.1,str(value),ha='center',fontsize=8)
        bars.append({'panel':3,'condition':conditions[ci],'mode':mode,'stride':stride,'metric':'Toros_handoff_TP','value':value,'x':float(b.get_x()),'width':float(b.get_width())})
axis.axhline(6,color='#af5260',linestyle='--',linewidth=.8)
axis.set_xticks(range(3),labels);axis.set_xlim(-.6,2.6);axis.set_ylim(0,7)
axis.set_title('Toros side-view reverse stress: TP /6',fontsize=10);axis.legend(frameon=False,fontsize=7,ncol=2)
for axis in axes.flat:
    axis.grid(axis='y',alpha=.12);axis.set_axisbelow(True);axis.spines[['top','right']].set_visible(False)
fig.suptitle('Fixed192 model: all photometric development controls',fontsize=14,y=.98)
fig.text(.055,.025,'Exact same weights, threshold, crop and counting rules. FP32/QDQ server outputs; source sampling Hz is not PYNQ FPS.',fontsize=8)
fig.text(.055,.008,'Unmatched predictions reflect the torso-reference scope. No new independent event or permanent-identity labels.',fontsize=8)
fig.subplots_adjust(left=.065,right=.98,top=.91,bottom=.09,wspace=.22,hspace=.29)
fig.savefig(out/'all_photometric_controls.png',dpi=165);fig.savefig(out/'all_photometric_controls.svg');plt.close(fig)
assert len(bars)==30
fontpath=font_manager.findfont('DejaVu Sans');font=ImageFont.truetype(fontpath,17);small=ImageFont.truetype(fontpath,14)
anchor=load(source/'pixel_controls.json');panels=[]
for scene in ['original','toros']:
    frames=sorted({r['frame0'] for r in anchor if r['scene']==scene})
    width=1220;rowheight=435;header=115;canvas=Image.new('RGB',(width,header+len(frames)*rowheight+50),'#f4f6f7');draw=ImageDraw.Draw(canvas)
    draw.text((16,12),scene+' | actual192 input pixels | all preselected frames',font=font,fill='#172d34')
    draw.text((16,39),'QDQ raw boxes at conf0.2; server outputs, not new PYNQ predictions.',font=small,fill='#40555d')
    for ci,label in enumerate(labels):draw.text((18+ci*402,77),label,font=font,fill='#172d34')
    for ri,frame in enumerate(frames):
        for ci,condition in enumerate(conditions):
            a=next(r for r in anchor if r['condition']==condition and r['scene']==scene and r['frame0']==frame)
            image=Image.open(source/a['pixel_file']).convert('RGB').resize((384,384),Image.Resampling.NEAREST)
            annotate=ImageDraw.Draw(image)
            with np.load(source/a['array_file']) as arrays:boxes=arrays['QDQ'][arrays['QDQ'][:,4]>=.2]
            for box in boxes:
                x1,y1,x2,y2=[float(v)*2 for v in box[:4]]
                if x2<x1 or y2<y1:continue
                annotate.rectangle((x1,y1,x2,y2),outline='#36ed9c',width=2)
                annotate.text((max(0,min(335,x1)),max(0,min(360,y1-15))),format(float(box[4]),'.2f'),font=small,fill='#36ed9c',stroke_width=1,stroke_fill='#10251d')
            x,y=18+ci*402,header+ri*rowheight
            canvas.paste(image,(x,y));draw.text((x,y+391),'source f'+str(frame)+' | kept boxes '+str(len(boxes)),font=small,fill='#172d34')
            panels.append({'scene':scene,'condition':condition,'frame0':frame,'source_pixel_file':a['pixel_file'],'source_pixel_sha256':a['pixel_sha256'],
                'rect':[x,y,384,384],'QDQ_boxes':boxes.tolist(),'display_scale':2,'display_interpolation':'nearest'})
    draw.text((18,canvas.height-36),'Padding remains114 in all conditions. Geometry, model weights and threshold are fixed.',font=small,fill='#40555d')
    canvas.save(out/(scene+'_actual_inputs_QDQ_boxes.png'))
result={'status':'THIRTY_DATA_BARS_AND_THIRTY_ACTUAL_INPUT_PANELS_RENDERED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'job_id':os.environ['SLURM_JOB_ID'],'bars':bars,'input_panels':panels,'new_model_forwards':0,'actual_board_actions':0,'whole_goal_complete':False}
(out/'media_values.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.glob('*')) if p.is_file()],indent=2)+'\n')
print(json.dumps({'status':result['status'],'files':[p.name for p in out.glob('*')],'input_panels':len(panels),'bars':len(bars)}),flush=True)
