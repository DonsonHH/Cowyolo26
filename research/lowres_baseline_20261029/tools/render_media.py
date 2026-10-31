from pathlib import Path
from datetime import datetime,timezone
import json,gzip,hashlib,subprocess,os
from collections import defaultdict
import numpy as np,cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype']='none'
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/baseline'
def load(p):return json.loads(p.read_text())
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protocol=load(ROOT/'protocol/baseline_v2_path_fix.json');summary=load(OUT/'summary.json');assert summary['protocol_sha256']==sha(ROOT/'protocol/baseline_v2_path_fix.json')
out=ROOT/'results/media';out.mkdir(exist_ok=False)
models=[m['name'] for m in protocol['models']];sizes=[192,256,320];colors=['#436fbd','#d28a40','#258471']
fig,axes=plt.subplots(2,2,figsize=(12,8));bar_data=[]
for ai,(axis,kind,title,limit) in enumerate([(axes[0,0],'localization','(a) Matched visible torso envelopes / 1,864',2000),
(axes[0,1],'original','(b) Original human-confirmed clip: down count',14),
(axes[1,0],'toros5','(c) Toros correct event matches / 6 at 5Hz',7),
(axes[1,1],'toros30','(d) Toros correct event matches / 6 at 30Hz control',7)]):
    for si,size in enumerate(sizes):
        values=[]
        for model in models:
            cname=model+'_s'+str(size)
            if kind=='localization':value=next(r for r in summary['validation_metrics'] if r['condition']==cname)['matched']
            else:
                scene='original' if kind=='original' else 'toros';stride=5 if scene=='original' else 6 if kind=='toros5' else 1
                row=next(r for r in summary['video_metrics'] if r['condition']==cname and r['scene']==scene and r['sample_stride']==stride and r['counter']=='handoff_events')
                value=row['down'] if scene=='original' else row['formal_event_metrics']['TP']
            values.append(value)
        x=np.arange(4)+(si-1)*.24;bars=axis.bar(x,values,width=.22,label=str(size),color=colors[si])
        for i,(bar,value) in enumerate(zip(bars,values)):
            axis.text(bar.get_x()+bar.get_width()/2,value+limit*.015,str(value),ha='center',va='bottom',fontsize=9)
            bar_data.append({'panel':ai,'model':models[i],'size':size,'value':value,'bar_x':float(bar.get_x()),'width':float(bar.get_width()),'ymax':limit})
    axis.set_ylim(0,limit);axis.set_xlim(-.6,3.6);axis.set_xticks(range(4),models);axis.set_title(title,fontsize=11)
    axis.spines[['top','right']].set_visible(False);axis.grid(axis='y',alpha=.15);axis.set_axisbelow(True)
    if kind=='original':axis.axhline(12,color='#a84452',linestyle='--',linewidth=1);axis.text(3.55,12.15,'12',color='#a84452',ha='right',fontsize=9)
    if kind.startswith('toros'):axis.axhline(6,color='#a84452',linestyle='--',linewidth=1)
    axis.legend(title='Input size',frameon=False,fontsize=8,ncol=3,loc='upper left')
fig.suptitle('192 / 256 / 320 square-input baselines: accuracy and sampling effects',y=.98,fontsize=14)
fig.text(.06,.025,'Four frozen FP32 detectors; same counters and conf0.2. Already-used development data. Server replay rate is not PYNQ throughput.',fontsize=9)
fig.subplots_adjust(left=.07,right=.98,top=.9,bottom=.09,hspace=.36,wspace=.22)
fig.savefig(out/'lowres_baseline_counts.png',dpi=180);fig.savefig(out/'lowres_baseline_counts.svg');plt.close(fig)
(out/'plot_data.json').write_text(json.dumps({'bars':bar_data,'models':models,'sizes':sizes,'image_panels':4},indent=2)+'\n')
cv2.setNumThreads(1);spec=protocol['videos'][0];assert sha(Path(spec['path']))==spec['sha256']
traces={}
for size in sizes:
    traces[size]={}
    for model in models:
        cname=model+'_s'+str(size);trace=loadgz(OUT/'original'/cname/'stride5_counter_trace.json.gz');byframe=defaultdict(list)
        for row in trace['post_tracker']:byframe[row['frame0']].append(row)
        events=[r for r in trace['handoff_events'] if 8912<=r['frame0']<10874]
        traces[size][model]={'boxes':byframe,'events':events}
ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
processes={};logs={};movies={};framecounts={s:0 for s in sizes};sheets={s:[] for s in sizes}
for size in sizes:
    movie=out/('original_4models_s'+str(size)+'.mp4');log=open(out/('encode_'+str(size)+'.log'),'xb')
    process=subprocess.Popen([ffmpeg,'-nostdin','-v','error','-f','rawvideo','-pix_fmt','bgr24','-s','1280x720','-r','25','-i','pipe:0',
    '-an','-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-threads','1','-movflags','+faststart',str(movie)],stdin=subprocess.PIPE,stderr=log)
    processes[size]=process;logs[size]=log;movies[size]=movie
cap=cv2.VideoCapture(spec['path']);assert cap.isOpened();anchors=[8995,9345,9790,10830];decoded=0
try:
    for frame in range(10874):
        ok,native=cap.read();assert ok;decoded+=1
        if frame<8912:continue
        source=cv2.resize(native,(640,360),interpolation=cv2.INTER_AREA);sample=frame-frame%5
        for size in sizes:
            canvas=np.zeros((720,1280,3),np.uint8)
            for i,model in enumerate(models):
                tile=source.copy();case=traces[size][model]
                for x in [.34,.75]:cv2.line(tile,(round(640*x),0),(round(640*x),359),(0,180,255),1)
                for y in [.4,.6]:cv2.line(tile,(round(640*.34),round(360*y)),(round(640*.75),round(360*y)),(0,180,255),1)
                for row in case['boxes'][sample]:
                    x1,y1,x2,y2=[round(v/4) for v in row['xyxy']];cv2.rectangle(tile,(x1,y1),(x2,y2),(95,236,155),1)
                    tid=row['track_id'];cv2.putText(tile,str(tid) if tid is not None else '?',(x1,max(42,y1-3)),cv2.FONT_HERSHEY_SIMPLEX,.40,(95,236,155),1)
                down=sum(e['frame0']<=frame and e['direction']=='A->B' for e in case['events'])
                up=sum(e['frame0']<=frame and e['direction']=='B->A' for e in case['events'])
                cv2.rectangle(tile,(0,0),(640,37),(19,27,39),-1);cv2.putText(tile,model+' / square'+str(size)+' / down '+str(down)+' up '+str(up),(7,17),cv2.FONT_HERSHEY_SIMPLEX,.47,(242,242,242),1)
                cv2.putText(tile,'source f'+str(frame)+'; held sample '+str(sample)+' at 5Hz',(7,33),cv2.FONT_HERSHEY_SIMPLEX,.40,(218,225,235),1)
                y=(i//2)*360;x=(i%2)*640;canvas[y:y+360,x:x+640]=tile
            processes[size].stdin.write(canvas.tobytes());framecounts[size]+=1
            if frame in anchors:
                file=out/('s'+str(size)+'_f'+str(frame)+'.jpg');assert cv2.imwrite(str(file),canvas)
                sheets[size].append({'path':file.relative_to(ROOT).as_posix(),'sha256':sha(file),'source_frame0':frame,'held_sample_frame0':sample,'model_panels':models})
    cap.release()
    for size in sizes:
        processes[size].stdin.close();assert processes[size].wait(timeout=60)==0;logs[size].close();assert framecounts[size]==1962
except BaseException:
    cap.release()
    for size,p in processes.items():
        if p.poll() is None:p.terminate()
        if not logs[size].closed:logs[size].close()
    raise
metadata={'status':'THREE4MODEL_SOURCE_REPLAYS_AND_ONE4PANEL_FIGURE_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],'source_SHA256':spec['sha256'],'source_decode_frames':decoded,'export_interval_inclusive':[8912,10873],
'movies':[{'size':size,'path':movies[size].relative_to(ROOT).as_posix(),'sha256':sha(movies[size]),'frames':1962,'fps':25,'dimensions':[1280,720]} for size in sizes],
'preview_frames':{str(k):v for k,v in sheets.items()},'anchor_frames':anchors,'preview_actual_image_panels':48,'science_figure_panels':4,
'new_model_forwards':0,'new_training_updates':0,'board_FPS_claimed':False}
(out/'media_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'relative_file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.iterdir()) if f.is_file()],indent=2)+'\n')
print(json.dumps(metadata),flush=True)
