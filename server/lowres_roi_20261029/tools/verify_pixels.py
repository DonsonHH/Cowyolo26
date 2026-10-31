"""CPU-only independent raw-frame/crop and actual NN-input checks."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,hashlib,os
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/roi'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protocol=load(ROOT/'protocol/roi_v1.json');gate=load(ROOT/'protocol/media_and_pixel_v1.json')
summary=load(OUT/'summary.json');assert summary['protocol_sha256']==sha(ROOT/'protocol/roi_v1.json')
assert os.environ.get('SLURM_JOB_ID');cv2.setNumThreads(1)
controls=load(OUT/'pixel_controls.json');assert len(controls)==8
source_checks=[];images={}
for spec in protocol['videos']:
    assert sha(Path(spec['path']))==spec['sha256']
    rows={r['frame0']:r for r in controls if r['scene']==spec['name']};assert set(rows)==set(spec['pixel_control_frames'])
    cap=cv2.VideoCapture(spec['path']);assert cap.isOpened();checked=0
    for frame in range(max(rows)+1):
        ok,native=cap.read();assert ok
        if frame not in rows:continue
        row=rows[frame];assert hashlib.sha256(native[:,:,::-1].copy().tobytes()).hexdigest()==row['source_decoded_RGB_pixel_sha256']
        x0,y0,x1,y1=spec['detection_crop_xyxy']
        # Fancy row/column selection is independent from the inference-time slice.
        crop=native[np.ix_(np.arange(y0,y1),np.arange(x0,x1),np.arange(3))]
        path=ROOT/row['crop_native_file'];assert sha(path)==row['crop_native_file_SHA256']
        image=cv2.imread(str(path));assert np.array_equal(crop,image)
        assert hashlib.sha256(crop[:,:,::-1].copy().tobytes()).hexdigest()==row['crop_native_RGB_pixel_sha256']
        oriented=np.ascontiguousarray(crop.transpose(1,0,2)[:,::-1,:]) if spec['orientation']=='clockwise90' else crop
        assert hashlib.sha256(oriented[:,:,::-1].copy().tobytes()).hexdigest()==row['crop_oriented_RGB_pixel_sha256']
        encoded_ok,encoded=cv2.imencode('.jpg',cv2.resize(native,(1280,720),interpolation=cv2.INTER_AREA),[cv2.IMWRITE_JPEG_QUALITY,95])
        assert encoded_ok and hashlib.sha256(encoded.tobytes()).hexdigest()==row['context_file_SHA256']
        images[(spec['name'],frame)]=oriented
        source_checks.append({'scene':spec['name'],'frame0':frame,'crop_file_SHA256':sha(path),'native_source_decoded_RGB_exact':True,
        'fancy_index_crop_exact':True,'transpose_orientation_exact':True,'source_context_JPEG_exact':True});checked+=1
    cap.release();assert checked==4
tensorrows=load(OUT/'input_tensor_controls.json');assert len(tensorrows)==96
bykey=defaultdict(list)
for row in tensorrows:bykey[(row['scene'],row['frame0'],row['input_size'])].append(row)
assert len(bykey)==24
checked=[];maximum=0.
for (scene,frame,size),rows in bykey.items():
    assert len(rows)==4 and len({r['tensor_sha256'] for r in rows})==1
    image=images[(scene,frame)];height,width=image.shape[:2];gain=min(size/height,size/width)
    nw,nh=round(width*gain),round(height*gain);small=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_LINEAR)
    dx,dy=(size-nw)/2,(size-nh)/2
    canvas=np.full((size,size,3),114,np.uint8)
    left,top=round(dx-.1),round(dy-.1);canvas[top:top+nh,left:left+nw]=small
    expected=np.ascontiguousarray(canvas[:,:,::-1].transpose(2,0,1))
    file=OUT/'pixel_controls'/(scene+'_f'+str(frame)+'_s'+str(size)+'_NN.npz')
    with np.load(file) as archive:actual=archive['actual_input']
    assert actual.shape==expected.shape==(3,size,size) and actual.dtype==np.float32 and np.isfinite(actual).all()
    assert hashlib.sha256(actual.tobytes()).hexdigest()==rows[0]['tensor_sha256']
    recovered=np.rint(actual.astype(np.float64)*255).astype(np.uint8);assert np.array_equal(expected,recovered)
    expected_float=expected.astype(np.float32)/np.float32(255)
    difference=float(np.max(np.abs(actual-expected_float)));assert difference<=gate['pixel_preprocess_gate']['maximum_float32_absolute_delta'];maximum=max(maximum,difference)
    checked.append({'scene':scene,'frame0':frame,'size':size,'actual_input_SHA256':rows[0]['tensor_sha256'],
        'uint8_RGB_CHW_exact_after_recovery':True,'maximum_float32_absolute_difference':difference,
        'network_array_file':file.relative_to(ROOT).as_posix(),'network_array_file_SHA256':sha(file)})
result={'status':'8_INDEPENDENT_NATIVE_CROPS24_ACTUAL_NN_INPUT_ARRAYS96_MODEL_TENSOR_HASHES_EXACT',
'created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],
'protocol_sha256':sha(ROOT/'protocol/roi_v1.json'),'media_gate_sha256':sha(ROOT/'protocol/media_and_pixel_v1.json'),
'raw_frame_crops_verified':8,'actual_unique_NN_arrays_verified':24,'actual_model_anchor_hash_rows_verified':96,
'maximum_float32_absolute_difference':maximum,'crop_source_checks':source_checks,'network_inputs':checked,
'new_network_forwards':0,'new_training_updates':0,'board_actions':0,'whole_goal_complete':False}
file=ROOT/'results/pixel_independent_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['crop_source_checks','network_inputs']}))
