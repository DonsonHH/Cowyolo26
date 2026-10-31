from pathlib import Path
from datetime import datetime,timezone
import os,sys,socket,json,gzip
ROOT=Path(__file__).resolve().parents[1]
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
sys.path.insert(0,str(ROOT/'tools'))
import run_control_v2 as execution
p=execution.load(ROOT/'protocol/control_v2.json');c=next(r for r in p['caches'] if r['id']=='new_O8_original_s5')
baseline=execution.gz(ROOT/'results/control_v2/new_O8_original_s5/baseline_trace.json.gz')
class OneFrameTracker(execution.LoggedBase):
    def _unconfirmed_association(self,*args,**kwargs):
        prior=self.args.fuse_score
        try:
            if self.source_frame0==9550:self.args.fuse_score=False
            return super()._unconfirmed_association(*args,**kwargs)
        finally:self.args.fuse_score=prior
trace,log=execution.replay(c,p,OneFrameTracker);trace=execution.canonical(trace)
for key in ['observations','post_tracker','confirmed_only_events','handoff_events']:
    assert [r for r in trace[key] if r['frame0']<9550]==[r for r in baseline[key] if r['frame0']<9550],key
events=[r for r in trace['handoff_events'] if 8912<=r['frame0']<=10873]
before=[r for r in baseline['handoff_events'] if 8912<=r['frame0']<=10873]
assert len(events)==11 and len(before)==10 and all(r['direction']=='A->B' for r in events+before)
assert any(r['frame0']==9605 for r in events) and not any(r['frame0']==9605 for r in before)
f=ROOT/'results/one_frame_causal_trace.json.gz';assert not f.exists()
with gzip.GzipFile(filename=str(f),mode='wb',mtime=0) as archive:archive.write(json.dumps(trace,separators=(',',':')).encode())
result={'status':'ONLY9550_UNCONFIRMED_COST_CHANGED_ALL_EARLIER_STATES_EXACT_AND_10_TO11_RESTORED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'intervention_source_frame0':9550,
    'all_earlier_observations_boxes_and_events_exact':True,'original_count':10,'one_frame_diagnostic_count':11,'diagnostic_events':events,
    'focus_log':log,'frame_specific_intervention_is_diagnostic_not_a_deployment_rule':True,
    'new_model_forwards':0,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False}
f=ROOT/'results/one_frame_causal_summary.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
