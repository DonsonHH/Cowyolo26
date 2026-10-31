"""Recover completed weights after a JSON newline-only post-training guard."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,hashlib,csv,os,sys,math,subprocess
import torch,yaml
from common import ROOT,sha,save_new
def load(p):return json.loads(Path(p).read_text())
def main():
    assert os.environ.get('SLURM_JOB_ID')
    p=load(ROOT/'protocol/training_v4.json');execution=load(ROOT/'protocol/formal_execution_v1.json')
    assert sha(ROOT/'tools/train_condition.py')==execution['training_script_sha256']
    assert sha(ROOT/'tools/rotation_training.py')==p['implementation_sha256']['rotation_training.py']
    summary=[]
    for condition in p['new_conditions']:
        cid=condition['condition_id'];index=condition['array_index'];folder=ROOT/'results/training'/cid
        state=subprocess.check_output(['sacct','-j','130518_'+str(index),'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
        assert state.startswith('FAILED|1:0'),(cid,state)
        error=(ROOT/'logs'/('train-130518_'+str(index)+'.err')).read_text(errors='replace')
        assert "assert sha(folder/'optimizer_step_batch_indices.json')==expected['optimizer_step_schedule_sha256']" in error and 'AssertionError' in error
        initial=load(folder/'initial_state.json');assert initial['condition']==condition and initial['initial_state_digest']==p['expected_initial_state_digests'][str(condition['seed'])]
        history=load(folder/'observed_history.json');assert len(history)==10 and [r['epoch'] for r in history]==list(range(1,11))
        assert [r['training_batches'] for r in history]==list(range(213,2131,213)) and history[-1]['optimizer_steps']==1225
        rows=list(csv.DictReader((folder/'results.csv').open()));assert len(rows)==10 and [int(r['epoch']) for r in rows]==list(range(1,11))
        assert all(math.isfinite(float(v)) for row in rows for v in row.values())
        indices=load(folder/'optimizer_step_batch_indices.json');assert len(indices)==1225
        old=ROOT.parent/'cows2021_adaptation_20261027/results/training'/('seed'+str(condition['seed']))/'optimizer_step_batch_indices.json'
        assert indices==load(old) and sha(old)==next(r['optimizer_step_schedule_sha256'] for r in p['baseline_checkpoint_conditions'] if r['seed']==condition['seed'])
        assert (folder/'optimizer_step_batch_indices.json').read_bytes()==old.read_bytes()+b'\n'
        for row in rows:
            saved=history[int(row['epoch'])-1]['validation']
            for k,v in row.items():
                if k.startswith('metrics/') and k in saved:assert abs(float(v)-float(saved[k]))<.0001
        args=yaml.safe_load((folder/'args.yaml').read_text());assert args['imgsz']==condition['imgsz'] and args['seed']==condition['seed'] and args['epochs']==10 and args['batch']==32 and args['workers']==2
        assert args['optimizer']=='AdamW' and args['amp'] is False and args['rect'] is False and args['degrees']==0 and args['close_mosaic']==0
        for key,value in p['train_kwargs_common'].items():assert args[key]==value,(cid,key,args[key],value)
        last=folder/'weights/last.pt';best=folder/'weights/best.pt';assert last.is_file() and best.is_file() and last.stat().st_size>1_000_000
        checkpoint=torch.load(last,map_location='cpu',weights_only=False);model=checkpoint['model'];assert model.names=={0:'cow'} and all(torch.isfinite(t).all() for t in model.state_dict().values())
        # This is a deterministic reconstruction, not an observed/saved log.
        generator=torch.Generator(device='cpu');generator.manual_seed(710026+condition['seed']);rotation=[];counts=Counter()
        if condition['right_angle']:
            for batch in range(2130):
                n=25 if batch%213==212 else 32;turns=torch.randint(0,4,(n,),generator=generator).tolist();counts.update(turns)
                rotation.append({'training_batch':batch+1,'turns':turns})
            assert sum(counts.values())==68090
        reconstructed=folder/'reconstructed_rotation_schedule.json';assert not reconstructed.exists();save_new(reconstructed,rotation)
        r={'status':'FIXED10_EPOCH_WEIGHTS_RECOVERED_AFTER_NEWLINE_ONLY_POSTTRAIN_ASSERTION','condition':condition,
           'original_slurm_task':'130518_'+str(index),'original_task_state':state,'original_error_file_sha256':sha(ROOT/'logs'/('train-130518_'+str(index)+'.err')),
           'protocol_sha256':sha(ROOT/'protocol/training_v4.json'),'initial_state_digest':initial['initial_state_digest'],
           'epochs_from_training_CSV_and_observed_history':10,'training_batches_from_observed_history':2130,'optimizer_steps_from_saved_schedule':1225,
           'optimizer_schedule_parsed_exact_to_historical':True,'only_raw_byte_difference_from_historical_schedule':'one_trailing_LF',
           'finite_gradient_guard_in_executed_code':True,'per_update_gradient_audit_array_recovered':False,
           'rotation_schedule_status':'RECONSTRUCTED_FROM_FROZEN_SEPARATE_CPU_GENERATOR_AND_OBSERVED_BATCH_COUNTS_NOT_OBSERVED_FILE',
           'reconstructed_rotation_counts':dict(counts),'reconstructed_rotation_schedule_sha256':sha(reconstructed),
           'actual_rotation_label_row_count_recovered':False,'preprocessed_image_presentations_from_loader_and_batches':68090,
           'last_checkpoint':str(last),'last_checkpoint_sha256':sha(last),'archived_best_sha256':sha(best),'all_checkpoint_tensors_finite':True,
           'last_epoch_validation':{k:float(v) for k,v in rows[-1].items() if k.startswith('metrics/')},
           'effective_args_sha256':sha(folder/'args.yaml'),'training_csv_sha256':sha(folder/'results.csv'),
           'observed_history_sha256':sha(folder/'observed_history.json'),'optimizer_schedule_file_sha256':sha(folder/'optimizer_step_batch_indices.json'),
           'new_training_updates_in_recovery':0,'source_Toros_or_final_pixels_used_in_recovery':False,'whole_goal_complete':False}
        save_new(folder/'completion_recovered.json',r);summary.append(r);del checkpoint,model
    assert len(summary)==15
    oldcontrols=[]
    for old in p['baseline_checkpoint_conditions']:
        assert sha(old['checkpoint'])==old['checkpoint_sha256']
        oldcontrols.append({'condition_id':'S320_plain_seed'+str(old['seed']),'historical_control':True,'checkpoint':old['checkpoint'],'checkpoint_sha256':old['checkpoint_sha256']})
    result={'status':'ALL15_LAST_EPOCH_WEIGHTS_AND3_HISTORICAL_CONTROLS_FROZEN_BEFORE_NEW_VIDEO_INFERENCE',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'recovery_slurm_job':os.environ['SLURM_JOB_ID'],
        'base_protocol_sha256':sha(ROOT/'protocol/training_v4.json'),'formal_execution_protocol_sha256':sha(ROOT/'protocol/formal_execution_v1.json'),
        'conditions':summary,'historical_controls':oldcontrols,'formal_training_updates_per_condition':1225,
        'total_formal_optimizer_updates':1225*15,'total_training_batches':2130*15,'total_image_presentations':68090*15,
        'discarded_smoke_updates':12,'source_video_Toros_or_final_candidate_inference_before_freeze':False,
        'all_original_failed_posttraining_statuses_preserved':True,'per_update_gradient_records_lost_after_assertion':True,
        'rotation_schedules_explicitly_reconstructed_not_observed':True,'whole_goal_complete':False}
    save_new(ROOT/'results/all_checkpoints_frozen.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['conditions','historical_controls']}),flush=True)
if __name__=='__main__':main()
