"""Compare cleaned-source rows with real cached loader rows, no model forward."""
from pathlib import Path
import json,os
import numpy as np
from ultralytics.cfg import get_cfg
from ultralytics.data.build import build_yolo_dataset
from ultralytics.data.utils import check_det_dataset
from common import *


def main():
    p=json.loads((ROOT/'protocol/composition_v1.json').read_text())
    cfg=get_cfg(overrides={**p['train_kwargs'],'task':'detect','mode':'train'})
    summary=[]
    for arm in ['mixed','real_repeated']:
        data=check_det_dataset(ROOT/'data'/arm/'data.yaml',autodownload=False)
        dataset=build_yolo_dataset(cfg,str(ROOT/'data'/arm/'images/train'),32,data,mode='train',stride=32)
        slots=json.loads((ROOT/'data'/arm/'slot_manifest.json').read_text())
        expected={r['alias']:r for r in slots if r['split']=='train'}
        differences=[];raw_total=unique_total=loaded_total=0
        for value in dataset.labels:
            slot=expected[value['im_file']]
            rows=[list(map(float,line.split())) for line in Path(slot['original_label']).read_text().splitlines() if line.strip()]
            original=np.array(rows,dtype=np.float32).reshape(-1,5)
            unique=np.unique(original,axis=0)
            actual=np.concatenate([value['cls'],value['bboxes']],axis=1)
            raw_total+=len(original);unique_total+=len(unique);loaded_total+=len(actual)
            def canonical(a):return sorted(tuple(float(v) for v in r) for r in a)
            assert canonical(actual)==canonical(unique),(arm,slot['alias'],original.tolist(),actual.tolist())
            if len(original)!=len(actual):differences.append({'alias':slot['alias'],'original_image':slot['original_image'],
                    'original_label_sha256':slot['label_sha256'],'original_rows':len(original),'loaded_rows':len(actual),
                    'duplicate_rows_removed':len(original)-len(actual)})
        summary.append({'arm':arm,'loaded_images':len(dataset),'original_label_rows':raw_total,'unique_float32_rows':unique_total,
                        'actual_loader_rows':loaded_total,'slots_with_removed_duplicate_rows':len(differences),
                        'all_actual_rows_equal_unique_source_float32_rows':True,'differences':differences})
    result={'status':'EXACT_DUPLICATE_LABEL_NORMALISATION_EXPLAINS_ALL_COUNT_DIFFERENCES','job_id':os.environ['SLURM_JOB_ID'],
            'conditions':summary,'source_files_changed':False,'model_forward_or_training_performed':False}
    target=ROOT/'results/loader_label_diagnosis.json';assert not target.exists();save(target,result)
    print(json.dumps({'status':result['status'],'conditions':[{k:v for k,v in r.items() if k!='differences'} for r in summary]}),flush=True)


if __name__=='__main__':main()
