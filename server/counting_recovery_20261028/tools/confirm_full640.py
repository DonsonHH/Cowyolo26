from pathlib import Path
import json,os,torch,cv2
from replay_v2 import run,sha,save,ROOT
def main():
    assert os.environ.get('SLURM_JOB_ID') and torch.cuda.is_available() and __import__('socket').gethostname()!='mu01'
    torch.set_num_threads(2);cv2.setNumThreads(1)
    p=json.loads((ROOT/'protocol/recovery_v2.json').read_text())
    pilot=json.loads((ROOT/'results/replay_v2/full640_5hz_seed26/summary.json').read_text())
    assert pilot['predicted_down']==11 and pilot['arm']['name']=='full640_5hz'
    out=ROOT/'results/full640_confirmation';out.mkdir(exist_ok=False)
    save(out/'fixed_extension.json',{'protocol_sha256':sha(ROOT/'protocol/recovery_v2.json'),
        'reason':'Confirm single-variable resolution arm afterpilot, rawcoverage-only arm not adoptedascountquality metric.',
        'seeds':[27,28],'new_hyperparameters_or_target_count':False})
    results=[run(p,pilot['arm'],weight,out) for weight in p['weights'] if weight['seed']!=26]
    save(out/'summary.json',{'status':'FULL640_TWO_MORE_SEEDS_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
        'protocol_sha256':sha(ROOT/'protocol/recovery_v2.json'),'conditions':results,'new_training':False,
        'independent_source_accuracy':None,'board_execution':False})
if __name__=='__main__':main()
