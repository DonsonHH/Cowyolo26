"""Two real train-only CUDA updates, discarded; no validation/query forward."""
import copy,json,os,socket,random
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.cfg import get_cfg
from ultralytics.data.build import build_yolo_dataset
from ultralytics.data.utils import check_det_dataset
from ultralytics.nn.tasks import DetectionModel
from common import ROOT,PROJECT,sha,save,state_digest,verify_similarity_review


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    assert torch.cuda.is_available() and ultralytics.__version__=='8.4.63'
    torch.set_num_threads(4)
    pp=ROOT/'protocol/detector_v1.json';p=json.loads(pp.read_text())
    label_path=ROOT/'results/labels_v1/summary.json';labels=json.loads(label_path.read_text())
    assert labels['status']=='DERIVED_LABELS_AND_REAL_ULTRALYTICS_LOADER_PASS'
    similarity=verify_similarity_review(labels)
    data_path=ROOT/'data_v1/data.yaml';assert sha(data_path)==labels['data_yaml_sha256']
    prepared=ROOT/'results/labels_v1/prepared_image_label_manifest.json'
    assert sha(prepared)==labels['prepared_manifest_sha256']
    manifest=json.loads(prepared.read_text())
    source=PROJECT/'models/yolo26n.pt';assert sha(source)==p['source_weights_sha256']
    random.seed(26);np.random.seed(26);torch.manual_seed(26);torch.cuda.manual_seed_all(26)
    cfg=get_cfg(overrides={**p['train_kwargs'],'task':'detect','mode':'train'})
    data=check_det_dataset(data_path,autodownload=False)
    dataset=build_yolo_dataset(cfg,str(ROOT/'data_v1/images/train'),32,data,mode='train',stride=32)
    expected={r['image_alias'] for r in manifest if r['actual_split']=='train'}
    assert set(dataset.im_files)==expected and len(dataset)==len(expected)
    base=YOLO(str(source))
    model=DetectionModel(copy.deepcopy(base.model.yaml),nc=1,ch=3,verbose=False)
    model.load(base.model,verbose=False);model.args=cfg;model.nc=1;model.names=data['names']
    initial=state_digest(model);model=model.cuda().train()
    before={k:v.detach().clone() for k,v in model.named_parameters()}
    optimizer=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.0005)
    history=[]
    for step in range(2):
        batch=dataset.collate_fn([dataset[i] for i in range(step*32,(step+1)*32)])
        batch['img']=batch['img'].cuda().float()/255
        optimizer.zero_grad(set_to_none=True)
        loss,items=model(batch);loss=loss.sum();assert torch.isfinite(loss).all()
        loss.backward()
        gradients=[v.grad for v in model.parameters() if v.grad is not None]
        assert gradients and all(torch.isfinite(v).all() for v in gradients)
        assert any(torch.count_nonzero(v) for v in gradients)
        optimizer.step()
        history.append({'step':step+1,'loss':float(loss.detach()),'loss_items':items.detach().cpu().tolist(),
                        'gradient_tensors':len(gradients)})
    changed=sum(not torch.equal(before[k],v.detach()) for k,v in model.named_parameters())
    assert changed>0
    result={'status':'PASS_ACTUAL_TRAIN_LOADER_AND_TWO_DISCARDED_CUDA_UPDATES',
            'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(pp),
            'label_loader_summary_sha256':sha(label_path),'prepared_manifest_sha256':sha(prepared),
            'initial_model_state_digest':initial,'source_weights_sha256':sha(source),
            'train_images':len(dataset),'loss_and_gradient_history':history,'changed_parameter_tensors':changed,
            'device':torch.cuda.get_device_name(0),'torch':torch.__version__,'ultralytics':ultralytics.__version__,
            'validation_or_candidate_final_query_forward':False,'source_or_Toros_forward':False,
            'smoke_weights_saved_or_used_for_formal_training':False,'formal_training_updates':0}
    result['similarity_review']=similarity
    target=ROOT/'results/preflight.json';assert not target.exists();save(target,result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
