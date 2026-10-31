from pathlib import Path
import hashlib,json,os,socket
import cv2,torch,numpy as np
from ultralytics import YOLO
from rotation_seam import make_restore_callback,callback_order

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    cv2.setNumThreads(1);torch.set_num_threads(2)
    ppath=ROOT/'protocol/video_rotation_v1.json';p=json.loads(ppath.read_text())
    frozen=json.loads((ROOT/'input/checkpoint_freeze.json').read_text())
    condition=frozen['conditions'][0];assert condition['seed']==26
    manifest=ROOT.parent/'cows2021_adaptation_20261027/results/labels_v1/prepared_image_label_manifest.json'
    row=next(r for r in json.loads(manifest.read_text()) if r['file_name']=='07802.jpg')
    assert row['actual_split']=='val' and row['candidate_date_role']=='validation_development_candidate'
    path=Path(row['image_alias']);assert sha(path)==row['sha256']
    image=cv2.imread(str(path));assert image is not None and image.shape==(720,1280,3)
    records=[]
    for orientation in p['orientations']:
        torch.manual_seed(26);model=YOLO(condition['checkpoint']);assert sha(Path(condition['checkpoint']))==condition['checkpoint_sha256']
        holder={'image':image,'frame_index':0};raw=[];frames=[];checks=[]
        callback=make_restore_callback(orientation,holder,1,raw,frames,checks)
        model.add_callback('on_predict_postprocess_end',callback)
        pixels=image if orientation=='original' else np.rot90(image,k=-1).copy()
        result=model.track(pixels,persist=True,tracker='bytetrack.yaml',classes=[0],imgsz=320,conf=.2,iou=.5,device=0,verbose=False)[0]
        assert len(raw)>0 and len(result.boxes)>0 and result.boxes.id is not None
        assert result.orig_shape==(720,1280) and np.array_equal(result.orig_img,image)
        records.append({'orientation':orientation,'sample_file':row['file_name'],'source_sha256':row['sha256'],
                        'pretracker_boxes':raw,'posttracker_data':result.boxes.data.cpu().tolist(),
                        'native_H':720,'native_W':1280,'callback_order':callback_order(model,callback),
                        'seam_checks':checks,'nonempty_neural_boxes_restored_in_native_camera':True})
        del model;torch.cuda.empty_cache()
    result={'status':'REAL_NONEMPTY_NEURAL_BOXES_IN_BOTH_ORIENTATIONS_RESTORE_BEFORE_BYTE_TRACK',
            'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ppath),'development_sample':'07802.jpg',
            'selection':'first pre-fixed sample from completed1571image orientation control, not a new held-out input',
            'records':records,'training_updates':0,'video_event_or_final_accuracy_claimed':False}
    target=ROOT/'results/nonempty_seam_smoke.json';assert not target.exists();target.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)


if __name__=='__main__':main()
