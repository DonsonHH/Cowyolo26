from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,socket
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
p=json.loads((ROOT/'protocol/workload_v1.json').read_text());source=PROJECT/'data/multicam_samples/camera1/2023-08-14T12-54-48.mp4'
assert sha(source)=='5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1'
out=ROOT/'results/camera_replay';out.mkdir(parents=True,exist_ok=False);folder=out/'highres';folder.mkdir()
rows=[];capture=cv2.VideoCapture(str(source));assert capture.isOpened()
for frame in range(10874):
 ok,native=capture.read();assert ok and native.shape==(1440,2560,3)
 if frame not in range(8915,10874,5):continue
 crop=native[:,870:1920].copy();assert crop.shape==(1440,1050,3)
 file=folder/('f'+str(frame).zfill(5)+'.jpg');assert cv2.imwrite(str(file),crop,[cv2.IMWRITE_JPEG_QUALITY,95])
 image=cv2.imread(str(file));assert image.shape==crop.shape
 rows.append({'frame0':frame,'time_s':frame/25,'file':file.relative_to(out).as_posix(),'bytes':file.stat().st_size,'sha256':sha(file),
  'native_crop_original_source_RGB_sha256':hashlib.sha256(crop[:,:,::-1].copy().tobytes()).hexdigest(),
  'decoded_JPEG_RGB_sha256':hashlib.sha256(image[:,:,::-1].copy().tobytes()).hexdigest(),
  'crop_original_native_xyxy':[870,0,1920,1440],'dimensions_WH':[1050,1440],'JPEG_quality':95,'lossy_reencoded':True})
capture.release();assert len(rows)==392
(out/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
result={'status':'ALL392_SOURCE_SLOTS_HIGHRES_PHYSICAL_ROI_PREPARED_WITHOUT_MODEL_BOX_SELECTION',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/workload_v1.json'),
 'source_sha256':sha(source),'source_decoded_frames':10874,'output_images':392,'total_image_bytes':sum(r['bytes'] for r in rows),
 'model_forwards':0,'box_or_ID_selection':False,'pixel_resized':False,'JPEG_lossy_quality':95,'whole_goal_complete':False}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
