"""Slurm-only source decode and paired media for all nine predefined caches."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,socket,subprocess,tarfile
import cv2,numpy as np
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/firststage_iou_regression_20261029')
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
def read(p):
    with Path(p).open(newline='') as f:return list(csv.DictReader(f))

def panel(image,source,variant,data,frame,scene,case_gt,gt):
    H,W=image.shape[:2];view=image.copy();sample=frame-frame%source['stride']
    if scene=='toros_used_reverse':
        for x in [.4,.6]:cv2.line(view,(round(x*W),round(.1*H)),(round(x*W),round(.95*H)),(0,185,255),3)
        size=(640,360)
    else:
        for y in [.4,.6]:cv2.line(view,(870,round(y*H)),(1920,round(y*H)),(0,185,255),3)
        size=(525,720)
    if case_gt:
        for row in gt[frame]:
            if int(row[1]) not in [14,7]:continue
            tid=int(row[1]);x,y,w,h=row[2:6];color=(255,170,50) if tid==14 else (235,110,230)
            cv2.rectangle(view,(round(x),round(y)),(round(x+w),round(y+h)),color,3)
            cv2.putText(view,f'Publisher {tid}',(max(0,round(x)),max(30,round(y)-8)),cv2.FONT_HERSHEY_SIMPLEX,.88,color,2)
    for box in data[variant]['boxes'][sample]:
        if not box['track_id']:continue
        x1,y1,x2,y2=[float(box[k]) for k in ['x1','y1','x2','y2']];tid=int(box['track_id'])
        cross=(y1+y2)/(2*H) if source['axis']=='x' else (x1+x2)/(2*W)
        a,b=source['perpendicular_ROI']
        if not a<cross<b:continue
        cv2.rectangle(view,(round(x1),round(y1)),(round(x2),round(y2)),(120,235,150),3)
        cv2.putText(view,f'ID{tid} {float(box["confidence"]):.2f}',(max(0,round(x1)),min(H-5,max(40,round(y1)+25))),cv2.FONT_HERSHEY_SIMPLEX,.86,(120,235,150),2)
    if scene!='toros_used_reverse':view=view[:,870:1920]
    return cv2.resize(view,size,interpolation=cv2.INTER_AREA)

def composite(image,source,data,frame,video_spec,gt,show_gt=False):
    scene=source['scene'];overhead=scene!='toros_used_reverse';width,height=(1080,840) if overhead else (1280,480)
    canvas=np.full((height,width,3),(25,23,17),np.uint8);start,end=video_spec['start_frame0'],video_spec['end_frame0_exclusive']
    cv2.putText(canvas,f'{source["name"]} | native frame0 {frame} | {frame/source["fps"]:.3f}s',(10,22),cv2.FONT_HERSHEY_SIMPLEX,.57,(245,245,245),1)
    count_rows=[]
    for index,variant in enumerate(['original_fused','firststage_pure_IoU']):
        x=(10+535*index) if overhead else index*640
        title='Original fused first stage' if index==0 else 'Candidate: first stage pure IoU'
        cv2.putText(canvas,title,(x+2,48),cv2.FONT_HERSHEY_SIMPLEX,.54,(180,245,200),1)
        events=[e for e in data[variant]['events'] if start<=e['frame0']<=frame and e['frame0']<end]
        ab=sum(e['direction']=='A->B' for e in events);ba=sum(e['direction']=='B->A' for e in events)
        cv2.putText(canvas,f'Predicted A->B {ab}, B->A {ba}',(x+2,71),cv2.FONT_HERSHEY_SIMPLEX,.53,(245,245,245),1)
        image_panel=panel(image,source,variant,data,frame,scene,show_gt,gt);ph,pw=image_panel.shape[:2]
        canvas[80:80+ph,x:x+pw]=image_panel;count_rows.append({'variant':variant,'A_to_B':ab,'B_to_A':ba})
    cv2.putText(canvas,'Same source pixels; current confirmed predictions; track IDs are temporary.',(10,height-24),cv2.FONT_HERSHEY_SIMPLEX,.48,(225,225,225),1)
    footer='Case only: publisher14 blue, publisher7 pink; predictions green.' if show_gt else 'Candidate is under evaluation; numeric IDs cannot be equated across variants.'
    cv2.putText(canvas,footer,(10,height-6),cv2.FONT_HERSHEY_SIMPLEX,.46,(225,225,225),1)
    return canvas,count_rows

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
    p=load(ROOT/'protocol/regression_v1.json');q=load(ROOT/'protocol/media_v1.json')
    assert q['regression_protocol_sha256']==sha(ROOT/'protocol/regression_v1.json') and q['summary_sha256']==sha(ROOT/'results/summary.json')
    out=ROOT/'results/media';out.mkdir(exist_ok=False);(out/'native').mkdir();(out/'cases').mkdir();(out/'videos').mkdir()
    gt=defaultdict(list)
    for row in csv.reader((ROOT/'input/publisher_gt_original.txt').open()):r=list(map(float,row));gt[int(r[0])].append(r)
    ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
    data={}
    for selected in q['sources']:
        name=selected['source_name'];data[name]={}
        for f in selected['result_files']:assert sha(f['path'])==f['sha256']
        for variant in p['variants']:
            folder=ROOT/'results'/(name+'__'+variant);by_frame=defaultdict(list)
            for r in read(folder/'post_tracker_boxes.csv'):by_frame[int(r['frame0'])].append(r)
            data[name][variant]={'boxes':by_frame,'events':load(folder/'handoff_events_all_history.json')}
    media=[];cases=[];native=[]
    for scene,spec in q['videos'].items():
        assert sha(spec['path'])==spec['sha256'];cap=cv2.VideoCapture(spec['path']);assert cap.isOpened()
        assert [int(cap.get(3)),int(cap.get(4)),cap.get(5)]==[spec['width'],spec['height'],float(spec['fps'])]
        selected=[r for r in q['sources'] if r['scene']==scene];writers={}
        width,height=(1280,480) if scene=='toros_used_reverse' else (1080,840)
        for item in selected:
            name=item['source_name'];dest=out/'videos'/(name+'_paired.mp4');log=(out/'videos'/(name+'_encode.log')).open('wb')
            cmd=[ffmpeg,'-hide_banner','-v','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{width}x{height}','-r',str(spec['output_fps']),'-i','pipe:0',
                 '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-threads','1','-movflags','+faststart',str(dest)]
            writers[name]={'process':subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log),'log':log,'dest':dest,'frames':0}
        source_frames=0
        try:
            for frame in range(spec['end_frame0_exclusive']):
                ok,image=cap.read();assert ok,(scene,frame);source_frames+=1
                if frame<spec['start_frame0'] or (frame-spec['start_frame0'])%spec['render_stride']:continue
                is_anchor=any(frame in item['anchors'] for item in selected)
                native_path=out/'native'/f'{scene}_{frame:05d}.jpg'
                if is_anchor:
                    assert cv2.imwrite(str(native_path),image,[cv2.IMWRITE_JPEG_QUALITY,95])
                    native.append({'scene':scene,'frame0':frame,'path':native_path.relative_to(ROOT).as_posix(),'sha256':sha(native_path)})
                for item in selected:
                    name=item['source_name'];source=next(s for s in p['sources'] if s['name']==name);entry=writers[name]
                    view,counts=composite(image,source,data[name],frame,spec,gt)
                    entry['process'].stdin.write(view.tobytes());entry['frames']+=1
                    if frame in item['anchors']:
                        show_gt=scene=='toros_used_reverse';view,counts=composite(image,source,data[name],frame,spec,gt,show_gt)
                        target=out/'cases'/f'{name}_f{frame:05d}.jpg';assert cv2.imwrite(str(target),view,[cv2.IMWRITE_JPEG_QUALITY,95])
                        cases.append({'source':name,'scene':scene,'frame0':frame,'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target),
                                      'panels':2,'native_path':native_path.relative_to(ROOT).as_posix(),'native_sha256':sha(native_path),
                                      'sample_frame0':frame-frame%source['stride'],'predefined_anchor':frame in item['predefined_anchors'],
                                      'publisher_GT_drawn':show_gt,'counter_values':counts})
            cap.release()
            for name,entry in writers.items():
                proc=entry['process'];proc.stdin.close();assert proc.wait()==0;entry['log'].close()
                assert entry['frames']==len(range(spec['start_frame0'],spec['end_frame0_exclusive'],spec['render_stride']))
                assert (out/'videos'/(name+'_encode.log')).stat().st_size==0
                dest=entry['dest']
                strict=subprocess.run([ffmpeg,'-hide_banner','-v','error','-xerror','-threads','1','-i',str(dest),'-an','-f','null','-'],capture_output=True)
                assert strict.returncode==0 and not strict.stderr
                check=cv2.VideoCapture(str(dest));decoded=0
                assert int(check.get(3))==width and int(check.get(4))==height and check.get(5)==float(spec['output_fps'])
                while True:
                    ok,unused=check.read()
                    if not ok:break
                    decoded+=1
                check.release();assert decoded==entry['frames']
                media.append({'source':name,'scene':scene,'path':dest.relative_to(ROOT).as_posix(),'sha256':sha(dest),
                              'frames':decoded,'fps':spec['output_fps'],'dimensions':[width,height],
                              'strict_full_decode':'PASS','source_frames_read_in_shared_scene':source_frames,
                              'source_frame0_range_halfopen':[spec['start_frame0'],spec['end_frame0_exclusive']],
                              'held_predictions_between_sample_ticks':spec['output_fps']>5 and scene!='toros_used_reverse'})
        except BaseException:
            cap.release()
            for entry in writers.values():
                proc=entry['process']
                if proc.poll() is None:proc.terminate();proc.wait()
                if not entry['log'].closed:entry['log'].close()
            raise
        print(json.dumps({'scene':scene,'source_frames_read':source_frames,'movies_complete':len(selected)}),flush=True)
    assert len(media)==9 and sum(r['frames'] for r in media)==8444 and len(cases)==q['native_anchor_sheets']==31
    record={'status':'NINE_PAIRED_PREDICTION_MOVIES_AND_31_NATIVE_CASE_SHEETS_CREATED',
            'job_id':os.environ['SLURM_JOB_ID'],'media_protocol_sha256':sha(ROOT/'protocol/media_v1.json'),
            'movies':media,'case_sheets':cases,'native_sources':native,'all_movie_frames_decoded':8444,
            'actual_visual_review_required':True,'new_detector_forwards':0,'new_training_updates':0,'candidate_adopted':False,'whole_goal_complete':False}
    save(out/'summary.json',record)
    files=[ROOT/'protocol/media_v1.json',ROOT/'tools/render.py',*[f for f in out.rglob('*') if f.is_file()]]
    manifest=[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files]
    mp=ROOT/'media_delivery_manifest.json';save(mp,{'files':manifest});archive=ROOT/'media_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for row in manifest:tf.add(ROOT/row['file'],arcname=row['file'])
        tf.add(mp,arcname='media_delivery_manifest.json')
    print(json.dumps({'status':record['status'],'files':len(manifest)+1,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive)}),flush=True)
if __name__=='__main__':main()
