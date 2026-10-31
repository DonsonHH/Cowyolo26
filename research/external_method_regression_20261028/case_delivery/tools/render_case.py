from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,socket,tarfile
import cv2,numpy as np
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028');PROJECT=ROOT.parent
load=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2))
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
    q=load(ROOT/'protocol/case_v1.json');p=load(ROOT/'protocol/regression_v1.json');assert q['regression_protocol_sha256']==sha(ROOT/'protocol/regression_v1.json')
    assert sha(ROOT/'results/local_verification.json')==q['verification_sha256']
    source=PROJECT/'phase2/data/mendeley_counting/extracted/Ground Truth/Toros.mp4';assert sha(source)==p['source_sha256']
    out=ROOT/'results/case';out.mkdir(exist_ok=False);cap=cv2.VideoCapture(str(source));assert (cap.get(5),int(cap.get(7)),int(cap.get(3)),int(cap.get(4)))==(30.,479,1920,1080)
    originals={}
    for f in range(max(q['frames'])+1):
        ok,image=cap.read();assert ok,f
        if f in q['frames']:originals[f]=image.copy();assert cv2.imwrite(str(out/f'native_f{f}.jpg'),image)
    cap.release();gt=defaultdict(list)
    for row in csv.reader((ROOT/'input/publisher_gt_original.txt').open()):
        row=list(map(float,row));gt[int(row[0])].append(row)
    rendered=[]
    for variant in ['secondstage_iou','allow_lost_iou']:
        rows=read(ROOT/f'results/pilot_{variant}/post_tracker_boxes.csv')
        for f in q['frames']:
            view=cv2.resize(originals[f],(1280,720),interpolation=cv2.INTER_AREA)
            for row in gt[f]:
                if int(row[1])!=q['reference_ID']:continue
                x,y,w,h=row[2:6];rect=[max(0,x),max(0,y),min(1920,x+w),min(1080,y+h)];x1,y1,x2,y2=[round(v*2/3) for v in rect]
                cv2.rectangle(view,(x1,y1),(x2,y2),(0,170,255),3);cv2.putText(view,'Publisher ID1',(x1,max(40,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,.62,(0,170,255),2)
            for row in rows:
                if int(row['frame'])!=f or not row['track_id']:continue
                x1,y1,x2,y2=[round(float(row[k])*2/3) for k in ['x1','y1','x2','y2']];tid=int(row['track_id']);focus=tid==q['prediction_ID'];color=(100,235,145) if focus else (220,180,100)
                cv2.rectangle(view,(x1,y1),(x2,y2),color,3 if focus else 1);cv2.putText(view,f'pred ID{tid}',(x1,max(62,y1+20)),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2)
            cv2.rectangle(view,(0,0),(1280,48),(20,24,28),-1);cv2.putText(view,f'pilot {variant} | source frame {f} | source time {f/30:.3f}s',(16,30),cv2.FONT_HERSHEY_SIMPLEX,.7,(235,235,235),2)
            target=out/f'{variant}_f{f}.jpg';assert cv2.imwrite(str(target),view);rendered.append(target)
    record={'status':'FIVE_NATIVE_FRAMES_TEN_GT_AND_PREDICTION_PANELS_CREATED','job_id':os.environ['SLURM_JOB_ID'],
      'source_sha256':p['source_sha256'],'frames':q['frames'],'reference_ID':q['reference_ID'],'prediction_ID':q['prediction_ID'],
      'same_numeric_ID_is_not_identity_proof':True,'new_inference':False,'new_independent_test':False,
      'images':[{'path':f.name,'sha256':sha(f),'bytes':f.stat().st_size} for f in sorted(out.glob('*.jpg'))]}
    save(out/'render_record.json',record)
    files=[ROOT/'protocol/case_v1.json',ROOT/'tools/render_case.py',ROOT/'tools/render_case.slurm',*out.iterdir()]
    manifest=[{'path':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files];mp=ROOT/'results/case_manifest.json';save(mp,manifest)
    archive=ROOT/'results/case_delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as tf:
        for f in files:tf.add(f,arcname=f.relative_to(ROOT).as_posix())
        tf.add(mp,arcname='delivery_manifest.json')
    result={'manifest_files':len(files),'archive_members':len(files)+1,'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp)}
    save(ROOT/'results/case_delivery_record.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
