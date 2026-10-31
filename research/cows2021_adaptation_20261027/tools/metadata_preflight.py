"""Early Slurm check of the actual new modules and every label geometry."""
from pathlib import Path
import hashlib,json,os,socket
import torch,ultralytics,PIL,cv2
from common import ROOT,sha
from prepare_labels import independent_envelope
from observed_trainer import ObservedTrainer
import preflight,train_detector


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    p=ROOT/'protocol/detector_v1.json';protocol=json.loads(p.read_text())
    assert ultralytics.__version__==protocol['library']['ultralytics']
    assert torch.__version__==protocol['library']['torch']
    catalog=ROOT/'input/derived_box_catalog.json';rows=json.loads(catalog.read_text())
    assert len(rows)==13165
    maximum=0.
    for row in rows:
        box=independent_envelope(row['bbox_xywh_angle_radians'],1280,720)
        error=max(abs(a-b) for a,b in zip(box,row['axis_box_xyxy']))
        maximum=max(maximum,error);assert error<1e-8
    source=ROOT.parent/'models/yolo26n.pt'
    assert sha(source)==protocol['source_weights_sha256']
    result={'status':'ACTUAL_NEW_MODULE_IMPORTS_AND_ALL_METADATA_GEOMETRIES_PASS',
            'job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),
            'protocol_sha256':sha(p),'catalog_sha256':sha(catalog),'rows_checked':len(rows),
            'maximum_envelope_difference_pixels':maximum,'source_weights_sha256':sha(source),
            'torch':torch.__version__,'ultralytics':ultralytics.__version__,'Pillow':PIL.__version__,'OpenCV':cv2.__version__,
            'candidate_final_image_pixels_opened':False,'new_Cows_image_pixels_opened':False,
            'actual_dataset_loader_executed':False,'CUDA_or_model_forward_performed':False,
            'formal_training_updates':0,'whole_goal_complete':False}
    target=ROOT/'results/metadata_preflight.json';assert not target.exists()
    target.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)


if __name__=='__main__':main()
