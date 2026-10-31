"""Native Results/ByteTrack seam controls before full diagnostic replay."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,socket
import numpy as np,cv2,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from rotation_seam import geometry_controls,clockwise_boxes,make_restore_callback,callback_order

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    assert torch.cuda.is_available() and ultralytics.__version__=='8.4.63'
    torch.set_num_threads(2);cv2.setNumThreads(1)
    ppath=ROOT/'protocol/video_rotation_v1.json';p=json.loads(ppath.read_text())
    for row in json.loads((ROOT/'input/staging_manifest.json').read_text()):assert sha(ROOT/row['path'])==row['sha256']
    controls=geometry_controls()
    # Explicitly labelled synthetic metadata, never mixed into real video traces.
    native=np.zeros((720,1280,3),np.uint8);turned=np.rot90(native,k=-1).copy()
    source_boxes=np.array([[100.5,20.25,300.75,680.5],[0.,0.,1280.,720.]],dtype=np.float32)
    boxes=clockwise_boxes(source_boxes,720).astype(np.float32)
    data=np.concatenate([boxes,np.array([[.9,0],[.8,0]],np.float32)],axis=1)
    holder={'image':native,'frame_index':0};raw=[];frames=[];seam=[]
    callback=make_restore_callback('clockwise90',holder,25,raw,frames,seam)
    fake=SimpleNamespace(results=[Results(orig_img=turned,path='synthetic_metadata_only',names={0:'cow'},boxes=torch.from_numpy(data))])
    callback(fake)
    assert fake.results[0].orig_shape==(720,1280) and np.array_equal(fake.results[0].boxes.xyxy.numpy(),source_boxes)
    assert fake.results[0].orig_img is native and fake.results[0].boxes.id is None
    fake.results=[Results(orig_img=turned,path='empty_synthetic_metadata_only',names={0:'cow'},boxes=torch.empty((0,6)))]
    callback(fake);assert fake.results[0].boxes.data.shape==(0,6)
    path=PROJECT/'phase2/data/mendeley_counting/extracted/Ground Truth/Toros.mp4'
    assert sha(path)=='1172810976a09e1a75a8b0a69edf21038393aa6f6b1c1273b8d7c34f62146a6c'
    frozen=json.loads((ROOT/'input/checkpoint_freeze.json').read_text())
    condition=frozen['conditions'][0];assert condition['seed']==26 and sha(Path(condition['checkpoint']))==condition['checkpoint_sha256']
    actual=[]
    for orientation in p['orientations']:
        torch.manual_seed(26);model=YOLO(condition['checkpoint']);assert model.names=={0:'cow'}
        state={'image':None,'frame_index':None};raw=[];frames=[];seam=[]
        restore=make_restore_callback(orientation,state,30,raw,frames,seam)
        model.add_callback('on_predict_postprocess_end',restore)
        video=cv2.VideoCapture(str(path));assert (video.get(5),int(video.get(7)))==(30.,479)
        post_boxes=0
        for frame in range(64):
            ok,image=video.read();assert ok
            state.update(image=image,frame_index=frame)
            input_image=image if orientation=='original' else np.rot90(image,k=-1).copy()
            result=model.track(input_image,persist=True,tracker='bytetrack.yaml',classes=[0],imgsz=320,conf=.2,iou=.5,device=0,verbose=False)[0]
            assert result.orig_shape==(1080,1920) and result.orig_img.shape[:2]==(1080,1920)
            post_boxes+=len(result.boxes)
        video.release();assert frames==list(range(64))
        order=callback_order(model,restore)
        actual.append({'orientation':orientation,'native_frames':64,'pretracker_boxes':len(raw),
                       'posttracker_boxes':post_boxes,'maximum_inverse_float32_difference':max(r['max_float32_inverse_difference'] for r in seam),
                       'callback_order':order,'original_tracker_coordinates_verified':True})
        del model;torch.cuda.empty_cache()
    result={'status':'SYNTHETIC_NONEMPTY_EMPTY_RESULTS_AND_REAL_BYTE_TRACK_SEAM_CONTROLS_PASS',
            'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ppath),'geometry_controls':controls,
            'actual64frame_conditions':actual,'new_training_updates':0,'full_replay_completed':False,
            'source_final_test_or_identity_accuracy_verified':False,'whole_goal_complete':False}
    target=ROOT/'results/smoke.json';assert not target.exists();target.write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
