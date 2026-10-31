"""Fresh CPU process: finite saved parameters and real frame prediction for all3weights."""
from pathlib import Path
import hashlib,json,os,resource
import cv2,torch
from ultralytics import YOLO

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/detector_training')
PROJECT=ROOT.parent


def main():
    torch.set_num_threads(2);cv2.setNumThreads(1)
    frozen=ROOT/'results/training/all_checkpoints_frozen_before_video.json'
    p=json.loads(frozen.read_text());rows=[]
    cap=cv2.VideoCapture(str(PROJECT/'phase2/data/mendeley_counting/extracted/Ground Truth/Toros.mp4'))
    ok,frame=cap.read();cap.release();assert ok and frame.shape==(1080,1920,3)
    for condition in p['conditions']:
        path=Path(condition['checkpoint']);digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==condition['checkpoint_sha256']
        model=YOLO(str(path));assert model.names=={0:'cow'} and model.task=='detect'
        parameters=list(model.model.parameters())
        assert parameters and all(torch.isfinite(v).all() for v in parameters)
        result=model.predict(frame,imgsz=320,conf=.2,iou=.5,device='cpu',verbose=False)[0]
        assert torch.isfinite(result.boxes.data).all() and result.orig_shape==(1080,1920)
        rows.append({'seed':condition['seed'],'checkpoint_sha256':digest,'parameters':sum(v.numel() for v in parameters),
                     'parameter_tensors':len(parameters),'all_parameters_finite':True,'real_Toros_frame0_prediction':'PASS',
                     'detections_at_conf02':len(result.boxes),'classes':model.names})
        del model
    assert len(rows)==3
    result={'status':'THREE_CHECKPOINTS_FRESH_CPU_LOAD_AND_REAL_FORWARD_PASS','job_id':os.environ['SLURM_JOB_ID'],
            'conditions':rows,'maximum_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'training_loader_exit_message_cause_resolved':False,'board_verified':False}
    dest=ROOT/'results/checkpoint_reload.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
