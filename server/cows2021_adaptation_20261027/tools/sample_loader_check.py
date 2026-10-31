"""Early real-loader check on fixed first64 train rows; full batch audit remains required."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,os,socket
import numpy as np
from PIL import Image
import cv2,ultralytics
from ultralytics.cfg import get_cfg
from ultralytics.data.build import build_yolo_dataset
from ultralytics.data.utils import check_det_dataset
from common import ROOT,sha
from audit_images import fingerprint


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    assert ultralytics.__version__=='8.4.63';cv2.setNumThreads(1)
    fetch_path=ROOT/'input/image_fetch_manifest.json'
    items=json.loads(fetch_path.read_text())['items']
    sample=sorted([r for r in items if r['development_role']=='train'],key=lambda r:r['file_name'])[:64]
    assert [r['file_name'] for r in sample]==[f'{i:05d}.jpg' for i in range(64)]
    labels=defaultdict(list)
    for row in json.loads((ROOT/'input/derived_box_catalog.json').read_text()):
        labels[row['file_name']].append(row)
    out=ROOT/'results/sample_loader_64';out.mkdir(exist_ok=False)
    data=out/'data';images=data/'images/train';annotations=data/'labels/train'
    images.mkdir(parents=True);annotations.mkdir(parents=True)
    records=[]
    for row in sample:
        source=ROOT/row['relative_image_path'];assert source.is_file()
        before=sha(source)
        with Image.open(source) as im:
            im.load();assert im.size==(1280,720)
            pixel,dh=fingerprint(im.convert('RGB'))
        bgr=cv2.imread(str(source));assert bgr is not None and bgr.shape==(720,1280,3)
        image=images/row['file_name'];image.symlink_to(source)
        expected=[]
        for label in sorted(labels[row['file_name']],key=lambda r:r['annotation_id']):
            assert label['valid'] and label['role']=='train'
            expected.append('0 '+' '.join(f'{v:.9f}' for v in label['yolo_class_cxcywh'][1:]))
        label=annotations/(Path(row['file_name']).stem+'.txt')
        label.write_text('\n'.join(expected)+'\n')
        records.append({'file_name':row['file_name'],'image_alias':str(image),'source_sha256':before,
                        'RGB_sha256':pixel,'dHash64':dh,'labels':len(expected),
                        'expected_float32_rows':np.asarray([list(map(float,s.split())) for s in expected],dtype=np.float32).tolist()})
        assert sha(source)==before
    yaml=data/'data.yaml';yaml.write_text(f'path: {data}\ntrain: images/train\nval: images/train\nnames:\n  0: cow\n')
    # The validation path is only schema filler in this isolated loader test;
    # no validation dataset, model inference, metric or training is executed.
    cfg=get_cfg(overrides={'task':'detect','mode':'train','imgsz':320,'batch':32,'cache':False,'workers':2})
    checked=check_det_dataset(yaml,autodownload=False)
    dataset=build_yolo_dataset(cfg,str(images),32,checked,mode='train',stride=32)
    expected={r['image_alias']:r for r in records}
    assert len(dataset)==64 and set(dataset.im_files)==set(expected)
    for row in dataset.labels:
        record=expected[row['im_file']]
        actual=np.concatenate([row['cls'],row['bboxes']],axis=1)
        wanted=np.asarray(record['expected_float32_rows'],dtype=np.float32)
        assert np.array_equal(actual,wanted)
    result={'status':'FIXED_64_TRAIN_IMAGES_DECODE_AND_ACTUAL_LABEL_LOADER_PASS',
            'job_id':os.environ['SLURM_JOB_ID'],'source_fetch_manifest_sha256':sha(fetch_path),
            'selection':'first64 train basenames in fixed fetch manifest; no prediction selection',
            'images':64,'loaded_labels':sum(r['labels'] for r in records),'records':records,
            'candidate_final_or_validation_pixels_opened':False,
            'full_8380_image_admission_certified':False,'new_model_forward_or_training':False,
            'source_native_files_modified':False,'full_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)


if __name__=='__main__':main()
