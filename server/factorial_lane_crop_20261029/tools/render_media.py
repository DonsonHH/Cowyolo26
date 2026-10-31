"""Fixed-seed two-movie comparison; all18 factor/seed pairs in one figure."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,os,socket,subprocess
import cv2,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype']='none'
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
p=load(ROOT/'protocol/crop_v1.json');gate=load(ROOT/'protocol/media_v1.json');s=load(ROOT/'results/roi/summary.json')
assert s['protocol_sha256']==sha(ROOT/'protocol/crop_v1.json') and gate['primary_seed']==26
out=ROOT/'results/media';out.mkdir(exist_ok=False)
full=PROJECT/'detector_factorial_20261029/results/evaluation';crop=ROOT/'results/roi'
historical_full=PROJECT/'lowres_baseline_20261029/results/baseline';historical_crop=PROJECT/'lowres_roi_20261029/results/roi'
def locator(size,variant,seed,mode):
    if size==320 and variant=='plain':base=historical_full if mode=='full' else historical_crop;condition='seed'+str(seed)+'_s320'
    else:base=full if mode=='full' else crop;condition='S'+str(size)+'_'+variant+'_seed'+str(seed)
    return base/'original'/condition
def summary(size,variant,seed,mode):return next(r for r in load(locator(size,variant,seed,mode)/'stride5_summary.json') if r['counter']=='handoff_events')
fig,axes=plt.subplots(3,2,figsize=(11,10),sharey=True);bars=[]
for i,size in enumerate(gate['sizes']):
    for j,variant in enumerate(['plain','rot90']):
        axis=axes[i,j]
        for mi,mode in enumerate(['full','crop']):
            values=[summary(size,variant,seed,mode)['down'] for seed in [26,27,28]]
            columns=axis.bar(np.arange(3)+(mi-.5)*.34,values,width=.31,label=['Full input','Fixed lane crop'][mi],color=['#8797ac','#247e76'][mi])
            for seed,value,b in zip([26,27,28],values,columns):
                axis.text(b.get_x()+b.get_width()/2,value+.16,str(value),ha='center',va='bottom',fontsize=10)
                bars.append({'panel':i*2+j,'size':size,'variant':variant,'seed':seed,'mode':mode,'value':value,
                   'bar_x':float(b.get_x()),'width':float(b.get_width()),'ymax':14,'xlim':[-.6,2.6],
                   'historical_control':size==320 and variant=='plain'})
        title=str(size)+' / '+variant+(' (historical320 controls)' if size==320 and variant=='plain' else '')
        axis.set_title(title,fontsize=11);axis.set_xticks(range(3),['seed26','seed27','seed28']);axis.set_ylim(0,14);axis.set_xlim(-.6,2.6)
        axis.axhline(12,color='#bb5660',linestyle='--',linewidth=.8);axis.grid(axis='y',alpha=.13);axis.set_axisbelow(True);axis.spines[['top','right']].set_visible(False)
handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.947),ncol=2,frameon=False)
fig.suptitle('New low-resolution models: full input vs fixed lane crop',y=.985,fontsize=14)
fig.text(.055,.024,'Original clip human total12; unchanged5Hz tracker and handoff counter. Fifteen new models plus three historical320plain controls.',fontsize=8)
fig.text(.055,.008,'Already-used development clip; total agreement is not event-level correctness. Server sampling is not PYNQ throughput.',fontsize=8)
fig.subplots_adjust(left=.06,right=.985,top=.885,bottom=.08,hspace=.30,wspace=.13)
fig.savefig(out/'all18_full_crop_counts.png',dpi=180);fig.savefig(out/'all18_full_crop_counts.svg');plt.close(fig)
(out/'plot_data.json').write_text(json.dumps({'bars':bars,'panels':6,'bars_count':36},indent=2)+'\n')
cases={};previews=[]
for variant in ['plain','rot90']:
    for size in [192,256,320]:
        for mode in ['full','crop']:
            trace=loadgz(locator(size,variant,26,mode)/'stride5_counter_trace.json.gz');boxes=defaultdict(list)
            for row in trace['post_tracker']:boxes[row['frame0']].append(row)
            events=[e for e in trace['handoff_events'] if 8912<=e['frame0']<=10873]
            cases[(variant,size,mode)]={'boxes':boxes,'events':events}
ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg';processes={};logs={};movies={};counts={v:0 for v in ['plain','rot90']}
for variant in ['plain','rot90']:
    file=out/('seed26_'+variant+'_full_vs_crop.mp4');log=(out/('encode_'+variant+'.log')).open('xb')
    process=subprocess.Popen([ffmpeg,'-nostdin','-v','error','-f','rawvideo','-pix_fmt','bgr24','-s','1280x1120','-r','25','-i','pipe:0',
      '-an','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-threads','1','-movflags','+faststart',str(file)],stdin=subprocess.PIPE,stderr=log)
    processes[variant]=process;logs[variant]=log;movies[variant]=file
video=p['videos'][0];assert sha(video['path'])==video['sha256'];capture=cv2.VideoCapture(video['path']);assert capture.isOpened();decoded=0
try:
    for frame in range(10874):
        ok,native=capture.read();assert ok and native.shape==(1440,2560,3);decoded+=1
        if frame<8912:continue
        source=cv2.resize(native,(640,360),interpolation=cv2.INTER_AREA);sample=frame-frame%5
        for variant in ['plain','rot90']:
            canvas=np.full((1120,1280,3),(24,32,44),np.uint8);panelrows=[]
            title='Fixed seed26 '+variant+': rows192/256/320; columnsFULL/CROP'+(' (320plain historical)' if variant=='plain' else '')
            cv2.putText(canvas,title,(8,17),cv2.FONT_HERSHEY_SIMPLEX,.44,(240,244,248),1,cv2.LINE_AA)
            cv2.putText(canvas,'Source f'+str(frame)+'; held sample f'+str(sample)+' at5Hz;25fps playback; human total12; not board FPS',(8,34),cv2.FONT_HERSHEY_SIMPLEX,.40,(220,228,238),1,cv2.LINE_AA)
            for i,size in enumerate([192,256,320]):
                for j,mode in enumerate(['full','crop']):
                    tile=source.copy();case=cases[(variant,size,mode)]
                    for x in [.34,.75]:cv2.line(tile,(round(640*x),0),(round(640*x),359),(0,184,255),1)
                    for y in [.4,.6]:cv2.line(tile,(round(640*.34),round(360*y)),(round(640*.75),round(360*y)),(0,184,255),1)
                    for row in case['boxes'][sample]:
                        a,b,c,d=[round(v/4) for v in row['xyxy']];cv2.rectangle(tile,(a,b),(c,d),(100,235,156),1)
                        cv2.putText(tile,str(row['track_id']) if row['track_id'] is not None else '?',(a,max(33,b-2)),cv2.FONT_HERSHEY_SIMPLEX,.35,(100,235,156),1)
                    down=sum(e['frame0']<=frame and e['direction']=='A->B' for e in case['events']);up=sum(e['frame0']<=frame and e['direction']=='B->A' for e in case['events'])
                    cv2.rectangle(tile,(0,0),(639,27),(24,32,44),-1)
                    cv2.putText(tile,str(size)+' / '+mode.upper()+' / down '+str(down)+' up '+str(up),(8,19),cv2.FONT_HERSHEY_SIMPLEX,.53,(240,244,248),1,cv2.LINE_AA)
                    canvas[40+i*360:40+(i+1)*360,j*640:(j+1)*640]=tile
                    panelrows.append({'size':size,'mode':mode,'down':down,'up':up,'sample_frame0':sample,'post_tracker_boxes':len(case['boxes'][sample]),'historical_control':size==320 and variant=='plain'})
            processes[variant].stdin.write(canvas.tobytes());counts[variant]+=1
            if frame in gate['source_anchors']:
                file=out/(variant+'_f'+str(frame)+'.png');assert cv2.imwrite(str(file),canvas)
                previews.append({'variant':variant,'source_frame0':frame,'video_index0':frame-8912,'path':file.relative_to(ROOT).as_posix(),'sha256':sha(file),'panels':panelrows})
    capture.release()
    for variant in ['plain','rot90']:
        processes[variant].stdin.close();assert processes[variant].wait(timeout=60)==0;logs[variant].close();assert counts[variant]==1962
except BaseException:
    capture.release()
    for variant,process in processes.items():
        if process.poll() is None:process.terminate()
        if not logs[variant].closed:logs[variant].close()
    raise
record={'status':'TWO_FIXED_SEED26_MOVIES_AND_ALL18_CONDITION_FIGURE_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
 'Slurm_job_id':os.environ['SLURM_JOB_ID'],'media_protocol_sha256':sha(ROOT/'protocol/media_v1.json'),'source_sha256':video['sha256'],
 'source_decoded_frames':decoded,'scope_frame0_inclusive':[8912,10873],'sample_Hz':5,'playback_fps':25,'dimensions':[1280,1120],
 'movies':[{'variant':v,'path':movies[v].relative_to(ROOT).as_posix(),'sha256':sha(movies[v]),'frames':1962} for v in ['plain','rot90']],
 'preview_frames':previews,'actual_preview_panels':48,'science_figure_panels':6,'science_bar_count':36,
 'model_selection_not_based_on_new_ROI_counts':True,'new_network_forwards':0,'new_training_updates':0,'PYNQ_FPS_claimed':False,'whole_goal_complete':False}
(out/'media_metadata.json').write_text(json.dumps(record,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'relative_file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()],indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='preview_frames'}),flush=True)
