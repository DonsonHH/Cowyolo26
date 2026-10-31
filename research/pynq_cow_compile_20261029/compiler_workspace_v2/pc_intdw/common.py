import os
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / 'envs/yolo26_stage_b/ultralytics_config'))
os.environ['YOLO_AUTOINSTALL'] = 'False'
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('MKL_NUM_THREADS', '4')
import json
import cv2
import numpy as np
import torch
import onnxruntime as ort
from ultralytics.data.augment import LetterBox
from ultralytics.utils import nms, ops

torch.set_num_threads(4)
torch.set_num_interop_threads(1)
torch.manual_seed(0)
np.random.seed(0)
REPORT = ROOT / 'reports/stage_b'
RESULT = ROOT / 'results/stage_b'
MODEL = ROOT / 'model/stage_b'
PT = ROOT / 'model/yolo26n.pt'
CONF, IOU = 0.25, 0.7

def save(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')

def preprocess(image):
    padded = LetterBox(new_shape=(640, 640), auto=False, stride=32)(image=image)
    return np.ascontiguousarray(padded[..., ::-1].transpose(2, 0, 1)[None], dtype=np.float32) / 255.0

def session(path, profile=False):
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    options.enable_profiling = profile
    options.profile_file_prefix = str(RESULT / 'ort_profile')
    return ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])

def decode(output, image, end2end):
    boxes = nms.non_max_suppression(torch.from_numpy(output.copy()), CONF, IOU,
                                   max_det=300, nc=0, end2end=end2end)[0]
    if len(boxes):
        boxes[:, :4] = ops.scale_boxes((640,640), boxes[:, :4], image.shape[:2])
    return boxes.numpy()

def detections(boxes, names):
    return [{'class_id': int(row[5]), 'class_name': names[int(row[5])],
             'confidence': float(row[4]), 'bbox_xyxy': [float(v) for v in row[:4]]} for row in boxes]

def iou(a, b):
    lo, hi = np.maximum(a[:2],b[:2]), np.minimum(a[2:4],b[2:4])
    intersection = float(np.maximum(hi-lo,0).prod())
    area_a, area_b = float(np.maximum(a[2:4]-a[:2],0).prod()), float(np.maximum(b[2:4]-b[:2],0).prod())
    return intersection / max(area_a+area_b-intersection, 1e-9)

def compare(reference, candidate):
    reference, candidate = np.asarray(reference).reshape(-1,6), np.asarray(candidate).reshape(-1,6)
    pairs = sorted([(iou(a,b),i,j) for i,a in enumerate(reference) for j,b in enumerate(candidate)
                    if int(a[5]) == int(b[5])], reverse=True)
    used_a, used_b, matched = set(), set(), []
    for overlap,i,j in pairs:
        if overlap >= .5 and i not in used_a and j not in used_b:
            used_a.add(i); used_b.add(j)
            matched.append({'reference_index':i,'candidate_index':j,'iou':overlap,
                'confidence_difference':float(abs(reference[i,4]-candidate[j,4])),
                'bbox_max_coordinate_difference':float(np.max(np.abs(reference[i,:4]-candidate[j,:4])))})
    unmatched_a = [i for i in range(len(reference)) if i not in used_a]
    unmatched_b = [j for j in range(len(candidate)) if j not in used_b]
    cross_pairs = sorted([(iou(reference[i],candidate[j]),i,j) for i in unmatched_a for j in unmatched_b
                          if int(reference[i,5]) != int(candidate[j,5])], reverse=True)
    changed_a, changed_b = set(), set()
    for overlap,i,j in cross_pairs:
        if overlap >= .5 and i not in changed_a and j not in changed_b:
            changed_a.add(i); changed_b.add(j)
    class_changes = len(changed_a)
    return {'reference_count':len(reference),'candidate_count':len(candidate),'matched_count':len(matched),
            'missed_reference_detections':len(reference)-len(matched),'additional_candidate_detections':len(candidate)-len(matched),
            'class_changes_at_iou_0_5':class_changes,'matches':matched}

def stats(values):
    values = np.asarray(values)
    return {name:float(function(values)) for name,function in [('mean',np.mean),('median',np.median),
        ('min',np.min),('max',np.max),('p95',lambda v:np.percentile(v,95))]}
