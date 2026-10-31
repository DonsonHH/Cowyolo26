from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,socket,subprocess,tarfile
import cv2
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2))
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
    q=load(ROOT/'protocol/render_v1.json');assert sha(ROOT/'results/local_verification.json')==q['local_verification_sha256']
    check=load(ROOT/'results/local_verification.json');assert check['event_paths']==12 and check['files']==71
    assert check['summary_sha256']==sha(ROOT/'results/summary.json')
    source=Path(q['source_video']);assert sha(source)==q['source_sha256'];summary=load(ROOT/'results/summary.json');states=[]
    for c in summary['conditions']:
        if c['variant']!='secondstage_iou':continue
        folder=ROOT/'results'/c['name'];assert not (folder/'view_raw.mp4').exists();rows=defaultdict(list)
        for r in read(folder/'source_warmup_tracks.csv')+read(folder/'source_tracks.csv'):rows[int(r['source_frame'])].append(r)
        writer=cv2.VideoWriter(str(folder/'view_raw.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),25.,(1280,720));assert writer.isOpened()
        states.append({'c':c,'folder':folder,'rows':rows,'events':load(folder/'handoff_events.json'),'writer':writer})
    assert len(states)==3
    cap=cv2.VideoCapture(str(source));assert (cap.get(5),int(cap.get(3)),int(cap.get(4)))==(25.,2560,1440)
    for frame in range(10874):
        ok,image=cap.read();assert ok,frame
        if frame<8912:continue
        base=cv2.resize(image,(1280,720),interpolation=cv2.INTER_AREA);sample=frame-frame%5
        for s in states:
            view=base.copy();seed=s['c']['seed'];down=sum(e['direction']=='A->B' and e['source_frame']<=frame for e in s['events']);up=sum(e['direction']=='B->A' and e['source_frame']<=frame for e in s['events'])
            for x in [.34,.75]:cv2.line(view,(round(x*1280),0),(round(x*1280),719),(0,177,255),2)
            for y in [.4,.6]:cv2.line(view,(round(.34*1280),round(y*720)),(round(.75*1280),round(y*720)),(0,177,255),2)
            for row in s['rows'][sample]:
                x1,y1,x2,y2=[round(float(row[k])/2) for k in ['x1','y1','x2','y2']]
                cv2.rectangle(view,(x1,y1),(x2,y2),(112,237,149),2)
                cv2.putText(view,f'id {row["track_id"]} {float(row["confidence"]):.2f}',(x1,max(62,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.57,(112,237,149),2)
            cv2.rectangle(view,(0,0),(1280,56),(18,24,28),-1)
            cv2.putText(view,f'Secondstage IoU only | same full640 5Hz + handoff | seed{seed}',(16,25),cv2.FONT_HERSHEY_SIMPLEX,.64,(240,242,240),2)
            cv2.putText(view,f'Source {frame} sample {sample} | predicted down {down} up {up}',(16,48),cv2.FONT_HERSHEY_SIMPLEX,.59,(220,228,225),1)
            cv2.rectangle(view,(0,690),(1280,720),(18,24,28),-1)
            cv2.putText(view,'Development control. Firststage and counter unchanged. Predicted track ID is not cow identity.',(16,710),cv2.FONT_HERSHEY_SIMPLEX,.55,(220,228,225),1)
            s['writer'].write(view)
            if frame in [9355,9365,9375,9420,10873]:assert cv2.imwrite(str(s['folder']/f'f{frame}.jpg'),view)
    cap.release();records=[];codec='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
    for s in states:
        s['writer'].release();folder=s['folder'];target=folder/'view.mp4';assert not target.exists()
        result=subprocess.run([codec,'-hide_banner','-nostdin','-n','-i',str(folder/'view_raw.mp4'),'-an','-threads','2','-c:v','libx264','-preset','veryfast','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],capture_output=True)
        log=ROOT/'logs'/f'encode_seed{s["c"]["seed"]}.log';log.write_bytes(result.stderr);assert result.returncode==0,result.stderr[-800:]
        result=subprocess.run([codec,'-v','error','-nostdin','-xerror','-i',str(target),'-f','null','-'],capture_output=True);assert result.returncode==0,result.stderr[-800:]
        cap=cv2.VideoCapture(str(target));assert (cap.get(5),int(cap.get(7)),int(cap.get(3)),int(cap.get(4)))==(25.,1962,1280,720);cap.release()
        records.append({'seed':s['c']['seed'],'path':target.relative_to(ROOT).as_posix(),'bytes':target.stat().st_size,'sha256':sha(target),'frames':1962,'fps':25,'strict_decode':'PASS'})
    record={'status':'THREE_FIXED_SCOPE_CONTROL_VIDEOS_RENDERED_AND_DECODED','job_id':os.environ['SLURM_JOB_ID'],
      'source_sha256':q['source_sha256'],'local_verification_sha256':q['local_verification_sha256'],'files':records,'new_inference':False}
    save(ROOT/'results/render_verification.json',record)
    files=[ROOT/'protocol/render_v1.json',ROOT/'results/render_verification.json',ROOT/'tools/render_media.py',ROOT/'tools/render_media.slurm']
    for s in states:files += [s['folder']/'view.mp4',*s['folder'].glob('f*.jpg')]
    files+=list((ROOT/'logs').glob('encode_seed*.log'));assert len(files)==len(set(files))
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
    mp=ROOT/'results/media_manifest.json';save(mp,manifest);archive=ROOT/'results/media_delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as tf:
        for p in files:tf.add(p,arcname=p.relative_to(ROOT).as_posix())
        tf.add(mp,arcname='delivery_manifest.json')
    out={'manifest_files':len(manifest),'archive_members':len(manifest)+1,'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp)}
    save(ROOT/'results/media_delivery_record.json',out);print(json.dumps(out),flush=True)
if __name__=='__main__':main()
