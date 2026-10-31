"""Slurm-only full decode, fixed native snapshots and exact pixel-overlap screen."""
from pathlib import Path
import hashlib,json,os,socket,struct,subprocess
from collections import defaultdict
import cv2
from PIL import Image,ImageDraw,ImageFont

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_session_validation_20261028');PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(n):return ImageFont.load_default(size=n)

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(2)
    protocol=ROOT/'protocol/sessions_v1.json';p=json.loads(protocol.read_text());manifest=json.loads((ROOT/'evidence/fetch_manifest.json').read_text())
    assert manifest['successful']==4 and manifest['protocol_sha256']==sha(protocol)
    labels=PROJECT/'cows2021_adaptation_20261027/results/labels_v1/prepared_image_label_manifest.json'
    assert sha(labels)==p['actual_prepared_image_label_manifest_sha256']
    known=defaultdict(list)
    for r in json.loads(labels.read_text()):known[r['RGB_dimensions_prefixed_sha256']].append(r['file_name'])
    out=ROOT/'results/admission';out.mkdir(parents=True,exist_ok=False);rows=[];all_overlaps=[]
    ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
    for entry in manifest['files']:
        src=Path(entry['path']);assert sha(src)==entry['sha256']
        folder=out/entry['sequence'];folder.mkdir();cap=cv2.VideoCapture(str(src));assert cap.isOpened()
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));fps=cap.get(cv2.CAP_PROP_FPS);declared=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        assert width==1280 and height==720 and abs(fps-30)<1e-9 and declared>0
        targets=sorted(set([0,declared//4,declared//2,3*declared//4,declared-1]));snaps=[];fingerprints=[];count=0
        while True:
            ret,frame=cap.read()
            if not ret:break
            assert frame.shape==(height,width,3)
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB);digest=hashlib.sha256(struct.pack('>II',width,height)+rgb.tobytes()).hexdigest()
            fingerprints.append({'frame0':count,'RGB_dimensions_prefixed_sha256':digest})
            if digest in known:all_overlaps.append({'sequence':entry['sequence'],'frame0':count,'matching_development_image_files':known[digest]})
            if count in targets:
                image=Image.fromarray(rgb);dest=folder/f'native_{count:04d}.jpg';image.save(dest,quality=96)
                snaps.append({'frame0':count,'time_s':count/fps,'path':dest.relative_to(ROOT).as_posix(),'sha256':sha(dest)})
            count+=1
        cap.release();assert count==declared and len(snaps)==5
        sheet=Image.new('RGB',(1280,1220),'#111827');d=ImageDraw.Draw(sheet)
        d.text((15,8),f"Native unlabelled overhead video: {entry['sequence']}",font=font(25),fill='white')
        for i,s in enumerate(snaps):
            im=Image.open(ROOT/s['path']).convert('RGB').resize((640,360));x=(i%2)*640;y=55+(i//2)*385
            sheet.paste(im,(x,y));d.text((x+7,y+361),f"Frame0 {s['frame0']} | {s['time_s']:.3f}s",font=font(19),fill='white')
        sheet.save(folder/'native_contact.jpg',quality=94)
        proxy=folder/'native_video.mp4'
        command=[ffmpeg,'-hide_banner','-v','warning','-threads','2','-i',str(src),'-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(proxy)]
        proc=subprocess.run(command,capture_output=True,check=True);(folder/'encode.log').write_bytes(proc.stderr)
        # A successful encoder exit alone is insufficient: decode every output frame.
        vc=cv2.VideoCapture(str(proxy));proxy_count=0
        while True:
            ok,f=vc.read()
            if not ok:break
            assert f.shape==(height,width,3);proxy_count+=1
        vc.release();assert proxy_count==count
        (folder/'frame_pixel_fingerprints.json').write_text(json.dumps(fingerprints,indent=2))
        r={'sequence':entry['sequence'],'source_path':str(src),'source_sha256':sha(src),'width':width,'height':height,'fps':fps,
           'frames':count,'duration_s':count/fps,'snapshots':snaps,'native_contact':(folder/'native_contact.jpg').relative_to(ROOT).as_posix(),
           'native_proxy':proxy.relative_to(ROOT).as_posix(),'native_proxy_sha256':sha(proxy),'native_proxy_full_decode_frames':proxy_count,
           'visual_camera_and_clipping_review':'PENDING','timestamps_disjoint_screen_is_not_full_duplicate_proof':True}
        (folder/'summary.json').write_text(json.dumps(r,indent=2));rows.append(r);print(json.dumps({k:r[k] for k in ['sequence','frames','fps','duration_s']}),flush=True)
    result={'status':'FOUR_NEW_SESSIONS_DECODED_NATIVE_CONTACTS_AND_PROXIES_PREPARED','job_id':os.environ['SLURM_JOB_ID'],
            'protocol_sha256':sha(protocol),'frames_total':sum(r['frames'] for r in rows),'videos':rows,
            'development_image_exact_pixel_overlaps':all_overlaps,'pixel_overlap_screen_compared_to_images':sum(map(len,known.values())),
            'absence_of_exact_matches_does_not_prove_no_near_duplicates':True,'models_run':False,'full_event_GT_available':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    # Deliver only reproducible admission evidence, not the large original AVI copies.
    import tarfile
    archive=ROOT/'admission_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for f in out.rglob('*'):
            if f.is_file():tar.add(f,arcname=f.relative_to(ROOT))
    print(json.dumps({'status':result['status'],'frames_total':result['frames_total'],'exact_pixel_overlaps':len(all_overlaps),
                      'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive)}),flush=True)

if __name__=='__main__':main()
