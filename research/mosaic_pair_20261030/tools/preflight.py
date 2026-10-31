"""Two genuine optimizer updates per mosaic arm; discard all smoke weights."""
from pathlib import Path
from datetime import datetime,timezone
import os,socket,json,gc
import torch,ultralytics
from ultralytics import YOLO
from common import ROOT,sha,state_digest,save_new
from rotation_training import RightAngleTrainer
class SmokeStop(Exception):pass

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    p=json.loads((ROOT/'protocol/training_v1.json').read_text());e=json.loads((ROOT/'protocol/preflight_execution_v1.json').read_text())
    assert e['protocol_sha256']==sha(ROOT/'protocol/training_v1.json')
    for name,digest in e['files_sha256'].items():assert sha(ROOT/name)==digest,name
    assert torch.__version__==p['library']['torch'] and ultralytics.__version__==p['library']['ultralytics']
    assert sha(p['source_weights'])==p['source_weights_sha256']
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    records=[]
    for arm in ['mosaic100','mosaic050']:
        probability=1. if arm=='mosaic100' else .5
        model=YOLO(p['source_weights']);losses=[];gradients=[];start=None
        def on_start(t):
            nonlocal start
            assert t.initial_model_digest==p['expected_initial_state_digests']['26']
            assert len(t.train_loader.dataset)==6809 and len(t.test_loader.dataset)==1571 and len(t.train_loader)==213
            assert sum(len(r['cls']) for r in t.train_loader.dataset.labels)==8888 and sum(len(r['cls']) for r in t.test_loader.dataset.labels)==1864
            assert type(t.optimizer).__name__=='AdamW' and float(t.args.mosaic)==probability
            start=state_digest(t.model);original=t.optimizer_step
            def checked_step():
                values=[v.grad for v in t.model.parameters() if v.grad is not None]
                assert values and all(torch.isfinite(v).all() for v in values)
                nonzero=sum(bool(torch.count_nonzero(v)) for v in values);assert nonzero>0
                gradients.append({'optimizer_update':len(gradients)+1,'finite_tensors':len(values),'nonzero_tensors':nonzero})
                original()
            t.optimizer_step=checked_step
        def before(t):t.observed_batches+=1
        def after(t):
            assert torch.isfinite(t.loss).all()
            losses.append({'batch':t.observed_batches,'optimizer_steps':t.observed_optimizer_steps,'loss':t.loss.detach().cpu().tolist()})
            if t.observed_optimizer_steps>=2:raise SmokeStop('Expected controlled two-update stop; discard weights')
        model.add_callback('on_train_start',on_start);model.add_callback('on_train_batch_start',before);model.add_callback('on_train_batch_end',after)
        kwargs={**p['train_kwargs_common'],'mosaic':probability,'workers':0,'save':False,'val':False}
        stopped=False
        try:
            model.train(trainer=RightAngleTrainer,data=p['source_data_yaml'],epochs=10,imgsz=192,seed=26,device=0,
                project=str(ROOT/'results/preflight_discarded'),name=arm,exist_ok=False,**kwargs)
        except SmokeStop:stopped=True
        t=model.trainer
        assert stopped and t.observed_batches==t.observed_optimizer_steps==len(gradients)==2 and len(losses)==2
        assert start and state_digest(t.model)!=start and t.preprocess_image_count==64 and sum(t.rotation_counts.values())==64
        assert len(t.rotation_schedule)==2 and t.rotation_label_rows>0
        records.append({'arm':arm,'mosaic':probability,'seed':26,'initial_state_digest':t.initial_model_digest,'training_batches':2,
            'discarded_optimizer_updates':2,'loss_history':losses,'gradient_checks':gradients,'actual_rotation_schedule':t.rotation_schedule,
            'actual_image_presentations':64,'actual_rotation_label_rows':t.rotation_label_rows,'workers_smoke_override':0,'formal_workers':2,
            'weights_saved_for_reuse':False,'full_source_video_or_Toros_forward':False})
        del t,model;gc.collect();torch.cuda.empty_cache()
    assert records[0]['actual_rotation_schedule']==records[1]['actual_rotation_schedule']
    result={'status':'BOTH_MOSAIC_ARMS_REAL_CUDA_LOSS_GRADIENT_AND_TWO_OPTIMIZER_UPDATES_PASS','created_UTC':datetime.now(timezone.utc).isoformat(),
        'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/training_v1.json'),'records':records,'discarded_optimizer_updates':4,
        'formal_training_updates':0,'full_source_video_or_Toros_forward':False,'new_independent_test':False,'whole_goal_complete':False,
        'network_scope':'four32-image training batches plus framework internal model-shape initialization probes;not final model evaluation'}
    save_new(ROOT/'results/preflight.json',result);print(json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)
if __name__=='__main__':main()
