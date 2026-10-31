"""Slurm-only fixed focused clips and still grids, no detector or tracker."""
from pathlib import Path
import hashlib,json,os,socket,subprocess
import cv2
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_positive_reference_20261028')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(2)
    proto=ROOT/'protocol/focused_review_v1.json';p=json.loads(proto.read_text());src=ROOT/'input/2023-08-17T13-25-38.mp4';assert sha(src)==p['source_sha256']
    out=ROOT/'results/focused';out.mkdir(parents=True,exist_ok=False);ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
    cap=cv2.VideoCapture(str(src));assert cap.isOpened();frame=0;records=[];encoders={};logs={};samples={w['name']:[] for w in p['windows']};contacts={w['name']:[] for w in p['windows']}
    for w in p['windows']:
        folder=out/w['name'];folder.mkdir();movie=folder/'native_ROI_5hz.mp4';log=(folder/'encode.log').open('wb');logs[w['name']]=log
        cmd=[ffmpeg,'-hide_banner','-v','warning','-f','rawvideo','-pix_fmt','bgr24','-s','480x700','-r','5','-i','pipe:0',
             '-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(movie)]
        encoders[w['name']]=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
    try:
        last=max(w['end_frame0_exclusive'] for w in p['windows'])
        while frame<last:
            ok,image=cap.read();assert ok,(frame,last)
            for w in p['windows']:
                if not w['start_frame0']<=frame<w['end_frame0_exclusive'] or (frame-w['start_frame0'])%5:continue
                folder=out/w['name'];x1,y1,x2,y2=p['ROI_native_xyxy'];native=image[y1:y2,x1:x2].copy()
                dest=folder/f'ROI_{frame:05d}.jpg';assert cv2.imwrite(str(dest),native,[cv2.IMWRITE_JPEG_QUALITY,95])
                row={'frame0':frame,'time_s_nominal':frame/25,'file':dest.relative_to(ROOT).as_posix(),'sha256':sha(dest),'native_crop_size':[x2-x1,y2-y1]};samples[w['name']].append(row)
                small=cv2.resize(native,(480,658),interpolation=cv2.INTER_AREA);canvas=__import__('numpy').zeros((700,480,3),dtype='uint8');canvas[:]=[39,24,17];canvas[42:]=small
                cv2.putText(canvas,f"Native ROI | frame0 {frame} | {frame/25:.2f}s",(8,16),cv2.FONT_HERSHEY_SIMPLEX,.46,(240,240,240),1)
                cv2.putText(canvas,'No predictions | Draft reference review',(8,35),cv2.FONT_HERSHEY_SIMPLEX,.43,(80,220,250),1)
                encoders[w['name']].stdin.write(canvas.tobytes())
                if (frame-w['start_frame0'])%25==0:contacts[w['name']].append(row)
            frame+=1
        cap.release()
        for name,encoder in encoders.items():encoder.stdin.close();assert encoder.wait()==0;logs[name].close()
    except BaseException:
        cap.release()
        for encoder in encoders.values():
            if encoder.poll() is None:encoder.terminate();encoder.wait()
        for log in logs.values():log.close()
        raise
    font=ImageFont.load_default(size=20)
    for w in p['windows']:
        name=w['name'];folder=out/name;panels=contacts[name];assert len(panels)==w['contact_frames'] and len(samples[name])==w['sample_frames'];pages=[]
        for page,start in enumerate(range(0,len(panels),12)):
            chosen=panels[start:start+12];sheet=Image.new('RGB',(1600,1710),'#111827');d=ImageDraw.Draw(sheet)
            d.text((10,5),f"Native {name}: 1Hz overview for reference; no predictions; cyan gates are fixed y=.4/.6",font=font,fill='white')
            for i,row in enumerate(chosen):
                x=(i%4)*400;y=40+(i//4)*555
                with Image.open(ROOT/row['file']) as im:small=im.convert('RGB').resize((390,535))
                draw=ImageDraw.Draw(small)
                for gate in [576,864]:draw.line([(0,gate*535/1440),(389,gate*535/1440)],fill='#20d6cd',width=2)
                d.text((x+3,y-20),f"f{row['frame0']} | {row['time_s_nominal']:.2f}s",font=font,fill='white');sheet.paste(small,(x,y))
            dest=folder/f'contact_{page+1:02d}.jpg';sheet.save(dest,quality=94);pages.append({'file':dest.relative_to(ROOT).as_posix(),'sha256':sha(dest),'source_frames0':[r['frame0'] for r in chosen]})
        movie=folder/'native_ROI_5hz.mp4';cap=cv2.VideoCapture(str(movie));decoded=0
        while True:
            ok,im=cap.read()
            if not ok:break
            assert im.shape==(700,480,3);decoded+=1
        cap.release();assert decoded==len(samples[name])
        record={**w,'samples':samples[name],'contact_pages':pages,'movie':movie.relative_to(ROOT).as_posix(),'movie_sha256':sha(movie),'movie_full_decoded_frames':decoded}
        (folder/'manifest.json').write_text(json.dumps(record,indent=2));records.append(record)
    result={'status':'THREE_NATIVE_FOCUSED_WINDOWS_READY_WITHOUT_PREDICTIONS','job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(proto),
            'source_sha256':p['source_sha256'],'source_frames_read':frame,'windows':records,'sample_images':sum(len(r['samples']) for r in records),
            'contact_images':sum(r['contact_frames'] for r in records),'models_used':False,'reference_available':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    import tarfile
    archive=ROOT/'focused_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as t:
        for f in out.rglob('*'):
            if f.is_file():t.add(f,arcname=f.relative_to(ROOT))
    print(json.dumps({k:v for k,v in result.items() if k!='windows'}),flush=True)
    print(json.dumps({'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive)}),flush=True)
if __name__=='__main__':main()
