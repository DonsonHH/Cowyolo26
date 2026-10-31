"""Slurm-only original long-video decode and prediction-free overview/ROI media."""
from pathlib import Path
import hashlib,json,os,socket,subprocess
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_positive_reference_20261028')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(2)
    p=json.loads((ROOT/'protocol/selection_v1.json').read_text());manifest=json.loads((ROOT/'input/video_manifest.json').read_text())
    src=ROOT/'input'/p['selected']['filename'];assert sha(src)==manifest['source_sha256'] and src.stat().st_size==manifest['source_bytes']
    out=ROOT/'results/native_review';out.mkdir(parents=True,exist_ok=False)
    ffprobe='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffprobe'
    # ffprobe may be absent in the old Conda environment; OpenCV and ffmpeg
    # full decoding are the primary integrity checks and media metadata sources.
    cap=cv2.VideoCapture(str(src));assert cap.isOpened()
    width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));fps=cap.get(cv2.CAP_PROP_FPS);declared=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    assert (width,height)==(2560,1440) and abs(fps-25)<1e-9 and declared>0
    stride=round(fps/p['native_focused_review_hz']);interval=round(fps*p['native_overview_interval_seconds'])
    assert fps/stride==5
    ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
    movie=out/'native_ROI_5hz.mp4';shape=(480,658);roi=(round(.34*width),0,round(.75*width),height)
    cmd=[ffmpeg,'-hide_banner','-v','warning','-f','rawvideo','-pix_fmt','bgr24','-s','480x700','-r','5','-i','pipe:0',
         '-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(movie)]
    snapshots=[];native_anchors=[];ROI_statistics=[];full_statistics=[];frame=0;review_frames=0;previous_roi=None;reference_roi=None
    with (out/'ROI_encode.log').open('wb') as log:
        writer=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
        try:
            while True:
                ok,image=cap.read()
                if not ok:break
                assert image.shape==(height,width,3)
                if frame%stride==0:
                    cut=image[roi[1]:roi[3],roi[0]:roi[2]];small=cv2.resize(cut,shape,interpolation=cv2.INTER_AREA)
                    gray=cv2.cvtColor(cv2.resize(cut,(96,132)),cv2.COLOR_BGR2GRAY)
                    if reference_roi is None:reference_roi=gray.copy()
                    delta=None if previous_roi is None else float(np.mean(np.abs(gray.astype(np.int16)-previous_roi.astype(np.int16))))
                    ROI_statistics.append({'frame0':frame,'time_s':frame/fps,'mean_abs_ROI_change_from_previous_5hz':delta,
                                           'mean_abs_ROI_change_from_frame0':float(np.mean(np.abs(gray.astype(np.int16)-reference_roi.astype(np.int16))))})
                    previous_roi=gray
                    canvas=np.zeros((700,480,3),dtype=np.uint8);canvas[:]=[39,24,17];canvas[42:]=small
                    cv2.putText(canvas,f'RAW ROI | frame0 {frame} | {frame/fps:.2f}s',(8,17),cv2.FONT_HERSHEY_SIMPLEX,.49,(240,240,240),1)
                    cv2.putText(canvas,'No detector, tracks or event predictions',(8,35),cv2.FONT_HERSHEY_SIMPLEX,.43,(90,220,250),1)
                    writer.stdin.write(canvas.tobytes());review_frames+=1
                if frame%interval==0 or frame==declared-1:
                    view=cv2.resize(image,(1280,720),interpolation=cv2.INTER_AREA);dest=out/f'overview_{frame:05d}.jpg'
                    assert cv2.imwrite(str(dest),view,[cv2.IMWRITE_JPEG_QUALITY,95])
                    snapshots.append({'frame0':frame,'time_s':frame/fps,'file':dest.name,'sha256':sha(dest),'image_size':[1280,720],
                                      'source_native_size':[width,height],'resized_display_only':True})
                    if frame%(round(fps*30))==0 or frame==declared-1:
                        dest2=out/f'native_{frame:05d}.jpg';assert cv2.imwrite(str(dest2),image,[cv2.IMWRITE_JPEG_QUALITY,96])
                        native_anchors.append({'frame0':frame,'time_s':frame/fps,'file':dest2.name,'sha256':sha(dest2),'image_size':[width,height]})
                frame+=1
            cap.release();writer.stdin.close();assert writer.wait()==0
        except BaseException:
            cap.release()
            if writer.poll() is None:writer.terminate();writer.wait()
            raise
    assert frame==declared and review_frames==len(range(0,frame,stride))
    decoder=cv2.VideoCapture(str(movie));decoded=0
    while True:
        ok,im=decoder.read()
        if not ok:break
        assert im.shape==(700,480,3);decoded+=1
    decoder.release();assert decoded==review_frames
    # Fixed 12-panel overview pages; source time and frame0 are printed beside every panel.
    pages=[];font=ImageFont.load_default(size=22)
    for page,at in enumerate(range(0,len(snapshots),12)):
        subset=snapshots[at:at+12];sheet=Image.new('RGB',(1920,1620),'#111827');d=ImageDraw.Draw(sheet)
        d.text((15,10),f"Ordinary overhead long video | camera1 {p['selected']['filename']} | page {page+1} | No predictions",font=font,fill='white')
        for i,row in enumerate(subset):
            x=(i%3)*640;y=50+(i//3)*390
            with Image.open(out/row['file']) as im:sheet.paste(im.resize((640,360)),(x,y))
            d.text((x+8,y+362),f"frame0 {row['frame0']} | {row['time_s']:.2f}s",font=font,fill='white')
        dest=out/f'overview_page_{page+1:02d}.jpg';sheet.save(dest,quality=94);pages.append({'file':dest.name,'sha256':sha(dest),'snapshot_indices':[at,at+len(subset)-1]})
    (out/'ROI_change_statistics.json').write_text(json.dumps(ROI_statistics,indent=2))
    result={'status':'LONG_ORDINARY_OVERHEAD_SOURCE_FULL_DECODE_AND_PREDICTION_FREE_REVIEW_READY','job_id':os.environ['SLURM_JOB_ID'],
            'source_sha256':sha(src),'source_bytes':src.stat().st_size,'source_frames':frame,'source_fps':fps,'native_size':[width,height],
            'duration_s':frame/fps,'protocol_sha256':sha(ROOT/'protocol/selection_v1.json'),
            'overview_interval_s':5,'overview_snapshots':snapshots,'native_30s_anchors':native_anchors,'overview_pages':pages,
            'review_ROI_native_xyxy':roi,'ROI_geometric_basis':'Same camera1 framing as the prior12-count source; must be visually verified before scoring.',
            'review_movie':movie.name,'review_movie_sha256':sha(movie),'review_movie_fps':5,'review_movie_frames':review_frames,
            'review_movie_complete_decode_frames':decoded,'review_movie_duration_s':review_frames/5,
            'change_statistics_are_not_cow_labels':True,'source_visual_QA':'PENDING','new_model_predictions':0,
            'event_reference_available':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    import tarfile
    archive=ROOT/'native_review_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for f in out.rglob('*'):
            if f.is_file():tar.add(f,arcname=f.relative_to(ROOT))
    print(json.dumps({k:v for k,v in result.items() if k not in ['overview_snapshots','native_30s_anchors','overview_pages']}),flush=True)
    print(json.dumps({'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'pages':len(pages)}),flush=True)

if __name__=='__main__':main()
