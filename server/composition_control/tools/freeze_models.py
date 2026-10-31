"""Verify same-seed control equivalence before admitting any video comparison."""
from pathlib import Path
import json,os,time,torch,yaml
from ultralytics import YOLO
from common import *


def main():
    torch.set_num_threads(2)
    pp=ROOT/'protocol/composition_v1.json';p=json.loads(pp.read_text())
    conditions=[]
    for c in p['conditions']:
        directory=ROOT/'results/training'/c['name']
        row=json.loads((directory/'condition_complete.json').read_text())
        assert row['status']=='ONE_COMPOSITION_CONDITION_COMPLETE' and row['condition']==c
        assert row['protocol_sha256']==sha(pp) and row['epochs']==10 and row['training_batches']==1850
        path=Path(row['checkpoint']);assert sha(path)==row['checkpoint_sha256']
        model=YOLO(str(path));assert model.names=={0:'cow'}
        assert all(torch.isfinite(v).all() for v in model.model.parameters())
        row['fresh_cpu_load_finite_parameters']=True;row['checkpoint_parameter_count']=sum(v.numel() for v in model.model.parameters())
        conditions.append(row);del model
    controls=[]
    for seed in [26,27,28]:
        a=next(r for r in conditions if r['condition']['arm']=='mixed' and r['condition']['seed']==seed)
        b=next(r for r in conditions if r['condition']['arm']=='real_repeated' and r['condition']['seed']==seed)
        assert a['initial_model_digest']==b['initial_model_digest']
        assert a['training_batches']==b['training_batches'] and a['optimizer_steps']==b['optimizer_steps']
        schedules=[]
        for row in [a,b]:
            path=Path(row['checkpoint']).parents[1]/'optimizer_step_batch_indices.json'
            assert sha(path)==row['optimizer_step_schedule_sha256'];schedules.append(json.loads(path.read_text()))
        assert schedules[0]==schedules[1] and len(schedules[0])==a['optimizer_steps']
        args=[]
        for row in [a,b]:
            path=Path(row['checkpoint']).parents[1]/'args.yaml';assert sha(path)==row['args_sha256']
            args.append(yaml.safe_load(path.read_text()))
        for key in ['epochs','imgsz','batch','workers','optimizer','lr0','lrf','momentum','weight_decay','seed','deterministic','amp','close_mosaic','patience']:
            assert args[0][key]==args[1][key],key
        controls.append({'seed':seed,'training_batches_each':a['training_batches'],'optimizer_steps_each':a['optimizer_steps'],
                         'optimizer_step_batch_schedule_equal':True,'initial_model_digest_equal':True,'fixed_training_args_equal':True})
    failed_checkpoint=ROOT/'results/failed_training/mixed_seed26_129841_0/weights/last.pt'
    retry_control=None
    if failed_checkpoint.is_file():
        frozen=next(r for r in conditions if r['condition']['name']=='mixed_seed26')
        old_model=YOLO(str(failed_checkpoint));new_model=YOLO(frozen['checkpoint'])
        old_state=old_model.model.state_dict();new_state=new_model.model.state_dict()
        assert old_state.keys()==new_state.keys()
        mismatched=[name for name in old_state if not torch.equal(old_state[name],new_state[name])]
        retry_control={'failed_record_job':'129841_0','recording_fixed_job':'129842_0',
                       'state_tensors_compared':len(old_state),'mismatched_state_tensors':mismatched,
                       'all_checkpoint_state_tensors_bitwise_equal':not mismatched,
                       'scope':'Reproducibility check of retained10epoch run, not a method/seed selection gate'}
        del old_model,new_model
    freeze={'status':'SIX_MODELS_AND_PAIRED_STEP_GATES_FROZEN','job_id':os.environ['SLURM_JOB_ID'],'frozen_at_unix':time.time(),
            'protocol_sha256':sha(pp),'preflight_sha256':sha(ROOT/'results/preflight.json'),
            'conditions':conditions,'paired_controls':controls,'source_or_Toros_inference_enabled_before_this_file':False,
            'selection':'All6 final epoch10 models retained; no arm/seed selection','scope':p['scope'],
            'recording_only_retry_reproducibility':retry_control}
    target=ROOT/'results/all_models_frozen.json';assert not target.exists();save(target,freeze)
    print(json.dumps({'status':freeze['status'],'paired_controls':controls}),flush=True)


if __name__=='__main__':main()
