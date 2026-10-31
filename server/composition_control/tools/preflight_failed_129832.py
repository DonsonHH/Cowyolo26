"""Real loader slot checks and discarded CUDA loss/gradient updates for each arm."""
from pathlib import Path
from collections import Counter
import copy,json,os,random
import numpy as np,torch
from ultralytics import YOLO
from ultralytics.cfg import get_cfg
from ultralytics.data.build import build_yolo_dataset
from ultralytics.data.utils import check_det_dataset
from ultralytics.nn.tasks import DetectionModel
from common import *


def main():
    assert torch.cuda.is_available();torch.set_num_threads(4)
    pp=ROOT/'protocol/composition_v1.json';p=json.loads(pp.read_text())
    prepared=json.loads((ROOT/'results/data_prepared.json').read_text());assert prepared['protocol_sha256']==sha(pp)
    cfg=get_cfg(overrides={**p['train_kwargs'],'imgsz':320,'batch':32,'task':'detect','mode':'train'})
    results=[];initials=[]
    for arm in ['mixed','real_repeated']:
        random.seed(26);np.random.seed(26);torch.manual_seed(26);torch.cuda.manual_seed_all(26)
        root=ROOT/'data'/arm;data=check_det_dataset(root/'data.yaml',autodownload=False)
        dataset=build_yolo_dataset(cfg,str(root/'images/train'),32,data,mode='train',stride=32)
        validation=build_yolo_dataset(cfg,str(root/'images/val'),32,data,mode='val',rect=True,stride=32)
        assert len(dataset)==5913 and len(validation)==370
        slots=json.loads((root/'slot_manifest.json').read_text())
        train_slots=[r for r in slots if r['split']=='train'];val_slots=[r for r in slots if r['split']=='val']
        assert dataset.im_files==[r['alias'] for r in train_slots]
        assert validation.im_files==[r['alias'] for r in val_slots]
        assert sum(len(r['cls']) for r in dataset.labels)==prepared['arms'][arm]['train_annotation_instances']
        exposures=Counter(Path(path).resolve().name for path in dataset.im_files)
        if arm=='mixed':assert len(exposures)==5913
        else:assert len(exposures)==2596 and Counter(exposures.values())=={2:1875,3:721}
        base=YOLO(str(PROJECT/'models/yolo26n.pt'))
        model=DetectionModel(copy.deepcopy(base.model.yaml),nc=1,ch=3,verbose=False)
        model.load(base.model,verbose=False);model=model.cuda().train()
        initials.append(state_digest(model));before={k:v.detach().clone() for k,v in model.named_parameters()}
        optimizer=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.0005)
        losses=[]
        for step in range(2):
            batch=dataset.collate_fn([dataset[i] for i in range(step*32,(step+1)*32)])
            batch['img']=batch['img'].cuda().float()/255
            optimizer.zero_grad(set_to_none=True)
            loss,items=model(batch);loss=loss.sum()
            assert torch.isfinite(loss).all();loss.backward()
            gradients=[v.grad for v in model.parameters() if v.grad is not None]
            assert gradients and all(torch.isfinite(g).all() for g in gradients)
            assert any(torch.count_nonzero(g) for g in gradients)
            optimizer.step();losses.append({'step':step+1,'loss':float(loss.detach()),'loss_items':items.detach().cpu().tolist(),'gradient_tensors':len(gradients)})
        changes=sum(not torch.equal(before[k],v.detach()) for k,v in model.named_parameters())
        assert changes>0
        results.append({'arm':arm,'loaded_train_slots':len(dataset),'loaded_val_slots':len(validation),'unique_train_filenames':len(exposures),
                        'repetition_distribution':dict(Counter(exposures.values())),'train_annotation_instances':sum(len(r['cls']) for r in dataset.labels),
                        'cuda_real_discarded_updates':losses,'parameter_tensors_changed':changes,'initial_model_digest':initials[-1]})
        del model,optimizer,dataset,validation,before;torch.cuda.empty_cache()
    assert initials[0]==initials[1]
    result={'status':'PASS_REAL_LOADER_AND_TWO_DISCARDED_UPDATES_PER_ARM','job_id':os.environ['SLURM_JOB_ID'],
            'protocol_sha256':sha(pp),'data_prepared_sha256':sha(ROOT/'results/data_prepared.json'),'conditions':results,
            'source_weights_sha256':sha(PROJECT/'models/yolo26n.pt'),'device':torch.cuda.get_device_name(0),
            'checkpoints_from_smoke_retained_for_training':False}
    save(ROOT/'results/preflight.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
