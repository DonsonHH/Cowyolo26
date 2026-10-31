"""No networks: rebuild all transforms from independently generated base pixels."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,socket,os,sys
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
cv2.setNumThreads(1)
sys.path.insert(0,str(ROOT/'input'))
from frozen_input import preprocess as baseline_input
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=load(ROOT/'protocol/study_v2.json');out=ROOT/'results/study_v2'
rows=load(out/'input_hashes.json')
hashes={(r['condition'],r['role'],r.get('frame0',r.get('file_name'))):r['tensor_sha256'] for r in rows}
assert len(hashes)==12675
count=0;anchor_count=0
anchors={(r['condition'],r['scene'],r['frame0']):r for r in load(out/'pixel_controls.json')}
lut=np.array([round(255*(v/255)**.7) for v in range(256)],np.uint8)
def check(image,role,key):
    global count,anchor_count
    base=baseline_input(image)
    pixels=np.rint(base[0].transpose(1,2,0)*255).astype(np.uint8)[:,:,::-1].copy()
    h,w=image.shape[:2];scale=min(192/h,192/w);height,width=round(h*scale),round(w*scale)
    left=(192-width)//2;top=(192-height)//2
    actual_content=pixels[top:top+height,left:left+width].copy()
    for condition in ['none','gamma07','clahe_y2']:
        expected=pixels.copy()
        if condition=='gamma07':
            expected[top:top+height,left:left+width]=lut[actual_content]
        elif condition=='clahe_y2':
            color=cv2.cvtColor(actual_content,cv2.COLOR_BGR2YCrCb)
            channels=list(cv2.split(color))
            channels[0]=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(channels[0])
            expected[top:top+height,left:left+width]=cv2.cvtColor(cv2.merge(channels),cv2.COLOR_YCrCb2BGR)
        tensor=np.ascontiguousarray(expected[:,:,::-1].transpose(2,0,1)[None],dtype=np.float32)*np.float32(1/255)
        assert hashlib.sha256(tensor.tobytes()).hexdigest()==hashes[condition,role,key],(condition,role,key)
        if (condition,role,key) in anchors:
            row=anchors[condition,role,key]
            saved=cv2.imread(str(out/row['pixel_file']))
            assert saved.tobytes()==expected.tobytes(),(condition,role,key,'PNG_pixels')
            anchor_count+=1
        count+=1
for row in load(ROOT/'input/validation_images.json'):
    assert sha(row['image_alias'])==row['sha256']
    image=cv2.imread(row['image_alias']);assert image.shape==(720,1280,3)
    check(cv2.rotate(image,cv2.ROTATE_90_CLOCKWISE),'validation',row['file_name'])
for spec in p['videos']:
    assert sha(spec['path'])==spec['sha256']
    cap=cv2.VideoCapture(spec['path']);assert cap.isOpened()
    x0,y0,x1,y1=spec['detection_crop_xyxy']
    for frame in range(spec['decode_end_exclusive']):
        ok,native=cap.read();assert ok
        if frame%spec['inference_stride']:continue
        image=native[y0:y1,x0:x1].copy()
        if spec['orientation']=='clockwise90':image=cv2.rotate(image,cv2.ROTATE_90_CLOCKWISE)
        check(image,spec['name'],frame)
    cap.release()
assert count==12675 and anchor_count==30
result={'status':'ALL12675_INPUT_HASHES_REBUILT_FROM_SOURCES_WITH_SEPARATE_CONTENT_TRANSFORMS',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'input_hashes_exact':count,'anchor_pixel_arrays_exact':anchor_count,
    'gamma_implementation':'Python_round_LUT_Numpy_indexing_independent_of_cv2_LUT_call',
    'clahe_implementation':'baseline_tensor_roundtrip_content_then_split_merge_YCrCb;shared_OpenCV_CLAHE_primitive_not_independent_CLAHE_algorithm',
    'baseline_geometry':'prior_frozen_input.py_not_new_photometric_helper',
    'new_model_forwards':0,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False}
target=ROOT/'results/source_input_verification_v2.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
