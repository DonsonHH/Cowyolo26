from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,os,socket,subprocess
import cv2,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
def load(p):return json.loads(Path(p).read_text())
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=load(ROOT/'protocol/media_v1.json');ep=load(ROOT/'protocol/evaluation_v2.json');source=ROOT/'results/evaluation_v2';s=load(source/'summary.json')
assert s['actual_source_image_forwards']==25350
out=ROOT/'results/media';out.mkdir(exist_ok=False)
fig,axes=plt.subplots(2,2,figsize=(12,8.3));plt.rcParams['svg.fonttype']='none';bars=[]
def value(kind,arm,seed,stride=None):
    name=arm+'_seed'+str(seed)
    if kind in ['TP','unmatched_prediction']:return next(r[kind] for r in s['validation_metrics'] if r['condition']==name)
    r=next(r for r in s['video_metrics'] if r['condition']==name and r['counter']=='handoff_events' and r['scene']==('original' if kind=='down' else 'toros') and r['stride']==(5 if kind=='down' else stride))
    return r['down'] if kind=='down' else r['formal_event_metrics']['TP']
for panel,kind,title in [(0,'TP','CW90 validation: matched torso references /1864'),(1,'unmatched_prediction','Validation: predictions without matching reference'),(2,'down','Original development clip count: human total12')]:
    axis=axes.flat[panel];highest=0
    for i,(arm,color,label) in enumerate([('mosaic100','#32827d','Mosaic1.0'),('mosaic050','#c3823d','Mosaic0.5')]):
        values=[value(kind,arm,seed) for seed in [26,27,28]];highest=max(highest,max(values))
        columns=axis.bar(np.arange(3)+(i-.5)*.32,values,width=.29,color=color,label=label)
        for seed,number,b in zip([26,27,28],values,columns):
            axis.text(b.get_x()+b.get_width()/2,number+(20 if panel<2 else .15),str(number),ha='center',fontsize=9)
            bars.append({'panel':panel,'arm':arm,'seed':seed,'kind':kind,'value':number,'x':float(b.get_x()),'width':float(b.get_width())})
    axis.set_ylim(0,2100 if panel==0 else max(10,highest*1.2) if panel==1 else max(14,highest+2))
    if panel==2:axis.axhline(12,color='#b85665',linestyle='--',linewidth=.8)
    axis.set_title(title,fontsize=10);axis.set_xticks(range(3),['seed26','seed27','seed28']);axis.set_xlim(-.6,2.6);axis.legend(frameon=False,fontsize=8)
axis=axes.flat[3]
for i,(arm,stride,color,label) in enumerate([('mosaic100',6,'#32827d','M1.0 5Hz'),('mosaic050',6,'#c3823d','M0.5 5Hz'),('mosaic100',1,'#8ebeba','M1.0 30Hz'),('mosaic050',1,'#dfc39e','M0.5 30Hz')]):
    values=[value('Toros',arm,seed,stride) for seed in [26,27,28]]
    columns=axis.bar(np.arange(3)+(i-1.5)*.18,values,width=.16,color=color,label=label)
    for seed,number,b in zip([26,27,28],values,columns):
        axis.text(b.get_x()+b.get_width()/2,number+.1,str(number),ha='center',fontsize=8)
        bars.append({'panel':3,'arm':arm,'seed':seed,'stride':stride,'kind':'TorosTP','value':number,'x':float(b.get_x()),'width':float(b.get_width())})
axis.axhline(6,color='#b85665',linestyle='--',linewidth=.8);axis.set_ylim(0,7);axis.set_xlim(-.6,2.6);axis.set_xticks(range(3),['seed26','seed27','seed28'])
axis.set_title('Toros side-view stress: TP /6; all FP/FN in report',fontsize=10);axis.legend(frameon=False,fontsize=7,ncol=2)
for ax in axes.flat:ax.grid(axis='y',alpha=.12);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
fig.suptitle('Fresh paired training: six frozen last-epoch models, fixed192 inputs',fontsize=13,y=.98)
fig.text(.06,.025,'Every seed retained. Original human total12 is not event-level GT. Server FP32 replay, not new PYNQ performance.',fontsize=8)
fig.text(.06,.008,'All weights frozen before replay. Source sampling5/30Hz does not mean board inference FPS. No global model replacement.',fontsize=8)
fig.subplots_adjust(left=.065,right=.98,top=.91,bottom=.09,wspace=.22,hspace=.29)
fig.savefig(out/'all_six_mosaic_controls.png',dpi=165);fig.savefig(out/'all_six_mosaic_controls.svg');plt.close(fig)
cases=[]
for arm in ['mosaic100','mosaic050']:
    name=arm+'_seed26';trace=gz(source/name/'original/stride5_counter_trace.json.gz');byframe=defaultdict(list)
    for r in trace['post_tracker']:byframe[r['frame0']].append(r)
    cases.append({'name':name,'boxes':byframe,'events':[r for r in trace['handoff_events'] if 8912<=r['frame0']<=10873]})
ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg';movie=out/'original_seed26_mosaic100_vs050_FP32.mp4';log=(out/'encode.log').open('xb')
process=subprocess.Popen([ffmpeg,'-nostdin','-v','error','-f','rawvideo','-pix_fmt','bgr24','-s','1152x560','-r','25','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-threads','1','-movflags','+faststart',str(movie)],stdin=subprocess.PIPE,stderr=log)
spec=ep['videos'][0];assert sha(spec['path'])==spec['sha256'];cap=cv2.VideoCapture(spec['path']);assert cap.isOpened();count=0;previews=[]
try:
    for frame in range(10874):
        ok,native=cap.read();assert ok
        if frame<8912:continue
        rotated=cv2.rotate(native[:,870:1920].copy(),cv2.ROTATE_90_CLOCKWISE);tile=cv2.resize(rotated,(576,420),interpolation=cv2.INTER_AREA)
        canvas=np.full((560,1152,3),(25,34,42),np.uint8);sample=frame-frame%5;panels=[]
        cv2.putText(canvas,'Fixed seed26 | native-source replay with192-network predictions',(10,25),cv2.FONT_HERSHEY_SIMPLEX,.58,(238,242,247),1,cv2.LINE_AA)
        for i,case in enumerate(cases):
            panel=tile.copy()
            for r in case['boxes'][sample]:
                x1,y1,x2,y2=r['xyxy'];a,b,c,d=(1440-y2)*.4,(x1-870)*.4,(1440-y1)*.4,(x2-870)*.4
                cv2.rectangle(panel,(round(a),round(b)),(round(c),round(d)),(68,222,126),1)
                tid='det' if r['track_id'] is None else 'T'+str(r['track_id'])
                cv2.putText(panel,tid+' '+format(r['confidence'],'.2f'),(max(0,min(490,round(a))),max(14,min(410,round(b)-3))),cv2.FONT_HERSHEY_SIMPLEX,.4,(68,222,126),1,cv2.LINE_AA)
            down=sum(r['direction']=='A->B' and r['frame0']<=frame for r in case['events']);up=sum(r['direction']=='B->A' and r['frame0']<=frame for r in case['events'])
            canvas[80:500,i*576:(i+1)*576]=panel
            cv2.putText(canvas,case['name']+' down='+str(down)+' up='+str(up),(i*576+10,60),cv2.FONT_HERSHEY_SIMPLEX,.52,(238,242,247),1,cv2.LINE_AA)
            panels.append({'condition':case['name'],'sample_frame0':sample,'down':down,'up':up,'post_tracker_boxes':len(case['boxes'][sample])})
        cv2.putText(canvas,'Source f'+str(frame)+' | detection5Hz, playback25fps | T=temporary track ID',(10,525),cv2.FONT_HERSHEY_SIMPLEX,.48,(227,234,240),1,cv2.LINE_AA)
        cv2.putText(canvas,'FP32 server outputs; no new PYNQ run. Human total12 only; permanent IDs unverified.',(10,550),cv2.FONT_HERSHEY_SIMPLEX,.46,(227,234,240),1,cv2.LINE_AA)
        process.stdin.write(canvas.tobytes());count+=1
        if frame in p['source_anchor_frames']:
            file=out/('source_f'+str(frame)+'.png');assert cv2.imwrite(str(file),canvas)
            previews.append({'source_frame0':frame,'video_index0':frame-8912,'file':file.name,'sha256':sha(file),'panels':panels})
    cap.release();process.stdin.close();assert process.wait(timeout=60)==0;log.close();assert count==1962
except BaseException:
    cap.release()
    try:process.stdin.close()
    except Exception:pass
    process.terminate();log.close();raise
data={'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'bars':bars,'previews':previews,
    'movie_file':movie.name,'movie_sha256':sha(movie),'movie_frames':count,'movie_size':[1152,560],'movie_fps':25,
    'primary_seed_fixed_before_result_selection':26,'new_model_forwards':0,'actual_board_actions':0,'whole_goal_complete':False}
(out/'media_values.json').write_text(json.dumps(data,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.glob('*')) if f.is_file()],indent=2)+'\n')
print(json.dumps({'status':'ALL6_MODEL30_BARS_AND_FIXED_SEED26_1962_FRAME_SOURCE_MOVIE_RENDERED','frames':count,'source_anchors':len(previews),'new_model_forwards':0}),flush=True)
