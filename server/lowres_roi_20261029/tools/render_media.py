"""Frozen seed26 full/ROI movie, all-model figure, and actual input evidence."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,hashlib,gzip,os,subprocess,socket
import numpy as np,cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype']='none'
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/roi';MEDIA=ROOT/'results/media'
def load(p):return json.loads(p.read_text())
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
p=load(ROOT/'protocol/roi_v1.json');gate=load(ROOT/'protocol/media_and_pixel_v1.json');render=load(ROOT/'protocol/media_render_v1.json')
s=load(OUT/'summary.json');assert s['protocol_sha256']==sha(ROOT/'protocol/roi_v1.json')
assert load(ROOT/'results/pixel_independent_verification.json')['actual_unique_NN_arrays_verified']==24
MEDIA.mkdir(exist_ok=False);models=[m['name'] for m in p['models']];sizes=[192,256,320]
fig,axes=plt.subplots(3,3,figsize=(14,9),sharey='row');bar_data=[]
for row,(scene,stride,label,limit,reference) in enumerate([('original',5,'Original down count (human total12)',14,12),
 ('toros',6,'Toros correct events /6 at5Hz',7,6),('toros',1,'Toros correct events /6 at30Hz control',7,6)]):
    for col,size in enumerate(sizes):
        axis=axes[row,col]
        for mi,mode in enumerate(['full','crop']):
            values=[]
            for model in models:
                paired=next(q for q in s['paired_full_vs_roi'] if q['scene']==scene and q['condition']==model+'_s'+str(size) and q['sample_stride']==stride and q['counter']=='handoff_events')
                values.append(paired[mode+'_down'] if scene=='original' else paired[mode+'_TP_FP_FN'][0])
            bars=axis.bar(np.arange(4)+(mi-.5)*.34,values,width=.31,color=['#8b98aa','#267a76'][mi],label=['Full input','Fixed lane crop'][mi])
            for model,value,bar in zip(models,values,bars):
                axis.text(bar.get_x()+bar.get_width()/2,value+limit*.018,str(value),ha='center',va='bottom',fontsize=8.8)
                bar_data.append({'panel':row*3+col,'scene':scene,'stride':stride,'model':model,'size':size,'mode':mode,
                                 'value':value,'bar_x':float(bar.get_x()),'width':float(bar.get_width()),'ymax':limit,'xlim':[-.6,3.6]})
        axis.set_ylim(0,limit);axis.set_xlim(-.6,3.6);axis.set_xticks(range(4),['COCO','s26','s27','s28'])
        axis.set_title(label+'; input'+str(size),fontsize=9.5);axis.spines[['top','right']].set_visible(False)
        axis.axhline(reference,ls='--',lw=.8,color='#b65059');axis.grid(axis='y',alpha=.15);axis.set_axisbelow(True)
handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.947),ncol=2,frameon=False)
fig.suptitle('Full input vs fixed lane crop at192 /256 /320: all four frozen detectors',y=.982,fontsize=14)
fig.text(.045,.022,'Handoff counter, unchanged thresholds. COCO=official YOLO26n; s26/s27/s28=three training seeds. Already-used development clips; no PYNQ FPS proof.',fontsize=8.5)
fig.subplots_adjust(left=.045,right=.985,top=.89,bottom=.077,hspace=.39,wspace=.15)
fig.savefig(MEDIA/'full_vs_roi_all_models.png',dpi=180);fig.savefig(MEDIA/'full_vs_roi_all_models.svg');plt.close(fig)
(MEDIA/'plot_data.json').write_text(json.dumps({'bars':bar_data,'panels':9,'reference_counts':[12,6,6],'models':models,'sizes':sizes},indent=2)+'\n')

def text(image,value,x,y,scale=.50,color=(238,241,246)):
    cv2.putText(image,value,(x,y),cv2.FONT_HERSHEY_SIMPLEX,scale,color,1,cv2.LINE_AA)
def fit(image,width,height):
    h,w=image.shape[:2];gain=min(width/w,height/h);nw,nh=round(w*gain),round(h*gain)
    canvas=np.full((height,width,3),(23,32,44),np.uint8);x=(width-nw)//2;y=(height-nh)//2
    canvas[y:y+nh,x:x+nw]=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_AREA)
    return canvas
input_sheets=[]
controls=load(OUT/'pixel_controls.json')
for control in controls:
    scene=control['scene'];frame=control['frame0'];video=next(v for v in p['videos'] if v['name']==scene)
    context=cv2.imread(str(ROOT/control['context_file']));crop=cv2.imread(str(ROOT/control['crop_native_file']))
    assert context is not None and crop is not None
    oriented=cv2.rotate(crop,cv2.ROTATE_90_CLOCKWISE) if video['orientation']=='clockwise90' else crop
    canvas=np.full((900,1600,3),(23,32,44),np.uint8)
    context=cv2.resize(context,(800,450),interpolation=cv2.INTER_AREA)
    x0,y0,x1,y1=video['detection_crop_xyxy'];sx,sy=800/video['width'],450/video['height']
    cv2.rectangle(context,(round(x0*sx),round(y0*sy)),(round(x1*sx)-1,round(y1*sy)-1),(0,184,255),2)
    canvas[30:480,:800]=context;canvas[30:480,800:]=fit(oriented,800,450)
    text(canvas,scene+' source frame'+str(frame)+'; fixed crop outlined',10,21)
    text(canvas,'Actual cropped image, orientation used by detector',810,21)
    text(canvas,'Actual NN inputs: RGB recovered from saved FP32 tensors; displayed at1:1 pixel scale',12,510,.53)
    for i,size in enumerate(sizes):
        file=OUT/'pixel_controls'/(scene+'_f'+str(frame)+'_s'+str(size)+'_NN.npz')
        with np.load(file) as a:array=a['actual_input']
        rgb=np.rint(array.transpose(1,2,0)*255).astype(np.uint8);bgr=rgb[:,:,::-1]
        left=i*533+(533-size)//2;top=560+(320-size)//2
        canvas[top:top+size,left:left+size]=bgr
        text(canvas,'Input '+str(size)+' x '+str(size),i*533+15,544,.56)
    name=scene+'_input_f'+str(frame)+'.png';assert cv2.imwrite(str(MEDIA/name),canvas)
    input_sheets.append({'scene':scene,'source_frame0':frame,'path':(MEDIA/name).relative_to(ROOT).as_posix(),
                         'sha256':sha(MEDIA/name),'panels':5,'tensor_sizes':sizes,'actual_inputs_rescaled_for_display':False})

video=p['videos'][0];assert video['name']=='original' and sha(Path(video['path']))==video['sha256']
assert render['primary_model']=='seed26' and gate['preview_source_anchors']==[8995,9345,9790,10830]
prior=Path(p['baseline_root_remote'])/'results/baseline';cases={}
for size in sizes:
    for mode,base in [('full',prior),('crop',OUT)]:
        trace=loadgz(base/'original'/('seed26_s'+str(size))/'stride5_counter_trace.json.gz');byframe=defaultdict(list)
        for post in trace['post_tracker']:byframe[post['frame0']].append(post)
        events=[e for e in trace['handoff_events'] if 8912<=e['frame0']<10874]
        cases[(size,mode)]={'boxes':byframe,'events':events}
ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg';movie=MEDIA/'original_seed26_full_vs_roi_3sizes.mp4'
log=open(MEDIA/'encode.log','xb');process=subprocess.Popen([ffmpeg,'-nostdin','-v','error','-f','rawvideo','-pix_fmt','bgr24','-s','1280x1120','-r','25','-i','pipe:0',
 '-an','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-threads','1','-movflags','+faststart',str(movie)],stdin=subprocess.PIPE,stderr=log)
cap=cv2.VideoCapture(video['path']);assert cap.isOpened();decoded=exported=0;previews=[]
try:
    for frame in range(10874):
        ok,native=cap.read();assert ok;decoded+=1
        if frame<8912:continue
        source=cv2.resize(native,(640,360),interpolation=cv2.INTER_AREA);sample=frame-frame%5
        canvas=np.full((1120,1280,3),(23,32,44),np.uint8);panels=[]
        text(canvas,'Fixed seed26: rows192 /256 /320; columns FULL /LANE CROP. Human confirmed clip total12.',10,17,.48)
        text(canvas,'Source f'+str(frame)+' | detections held from f'+str(sample)+' at5Hz |25fps replay | board FPS unmeasured',10,34,.43)
        for i,size in enumerate(sizes):
            for j,mode in enumerate(['full','crop']):
                tile=source.copy();case=cases[(size,mode)];boxes=case['boxes'][sample]
                for x in [.34,.75]:cv2.line(tile,(round(640*x),0),(round(640*x),359),(0,184,255),1)
                for y in [.4,.6]:cv2.line(tile,(round(640*.34),round(360*y)),(round(640*.75),round(360*y)),(0,184,255),1)
                for box in boxes:
                    x1,y1,x2,y2=[round(v/4) for v in box['xyxy']];cv2.rectangle(tile,(x1,y1),(x2,y2),(100,233,156),1)
                    text(tile,str(box['track_id']) if box['track_id'] is not None else '?',x1,max(34,y1-2),.35,(100,233,156))
                down=sum(e['frame0']<=frame and e['direction']=='A->B' for e in case['events']);up=sum(e['frame0']<=frame and e['direction']=='B->A' for e in case['events'])
                cv2.rectangle(tile,(0,0),(639,27),(23,32,44),-1)
                text(tile,'seed26 | '+str(size)+' | '+mode.upper()+' | down '+str(down)+' up '+str(up),9,19,.52)
                canvas[40+i*360:40+(i+1)*360,j*640:(j+1)*640]=tile
                panels.append({'size':size,'mode':mode,'down':down,'up':up,'held_frame0':sample,'post_tracker_boxes':len(boxes)})
        process.stdin.write(canvas.tobytes());exported+=1
        if frame in gate['preview_source_anchors']:
            path=MEDIA/('source_f'+str(frame)+'.png');assert cv2.imwrite(str(path),canvas)
            previews.append({'source_frame0':frame,'video_frame_index0':frame-8912,'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'panels':panels})
    cap.release();process.stdin.close();assert process.wait(timeout=60)==0;log.close();assert decoded==10874 and exported==1962
except BaseException:
    cap.release()
    if process.poll() is None:process.terminate()
    if not log.closed:log.close()
    raise
meta={'status':'FROZEN_SEED26_SIX_PANEL_MOVIE_ALL72_BARS_AND8_ACTUAL_INPUT_SHEETS_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
      'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/roi_v1.json'),
      'media_gate_sha256':sha(ROOT/'protocol/media_and_pixel_v1.json'),'render_protocol_sha256':sha(ROOT/'protocol/media_render_v1.json'),
      'source_sha256':video['sha256'],'source_decode_frames':decoded,'scope_frame0_inclusive':[8912,10873],
      'primary_model':'seed26','sizes':sizes,'fps':25,'detection_sampling_Hz':5,'dimensions':[1280,1120],
      'movie':{'path':movie.relative_to(ROOT).as_posix(),'sha256':sha(movie),'frames':exported},'preview_frames':previews,
      'input_sheets':input_sheets,'source_NN_panels':40,'movie_anchor_panels':24,'science_figure_panels':9,'science_bar_count':72,
      'new_network_forwards':0,'new_training_updates':0,'board_actions':0,'PYNQ5FPS_proven':False,'whole_goal_complete':False}
(MEDIA/'media_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
(MEDIA/'manifest.json').write_text(json.dumps([{'relative_file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(MEDIA.iterdir()) if f.is_file()],indent=2)+'\n')
print(json.dumps({k:v for k,v in meta.items() if k not in ['preview_frames','input_sheets']}),flush=True)
