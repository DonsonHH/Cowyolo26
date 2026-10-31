from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import os,sys,socket,json,gzip,hashlib,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path[:0]=[str(PROJECT/'pynq_frontend_port_20261029'),str(ROOT/'input'),str(ROOT/'tools')]
import frame_pipeline as pipeline_module
from cow_tracker.byte_tracker import BYTETracker
from cow_tracker import matching
from confirmation_iou import UnconfirmedIoUTracker
from event_metrics import evaluate_events
def load(p):return json.loads(Path(p).read_text())
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def savegz(p,v):
    assert not p.exists()
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(v,separators=(',',':')).encode())
def canonical(v):return json.loads(json.dumps(v))
class LoggedBase(BYTETracker):
    def _unconfirmed_association(self,unconfirmed,u_detection,detections,activated,removed):
        record=None
        if self.source_frame0 in self.focus_frames:
            remain=[detections[i] for i in u_detection]
            iou=matching.iou_distance(unconfirmed,remain);fused=matching.fuse_score(iou,remain)
            record={'frame0':self.source_frame0,'unconfirmed_IDs':[t.track_id for t in unconfirmed],
                'detection_scores':[float(t.score) for t in remain],'detection_xyxy':[t.xyxy.tolist() for t in remain],
                'pure_IoU_cost':iou.tolist(),'fused_cost':fused.tolist(),'threshold':.7}
        result=super()._unconfirmed_association(unconfirmed,u_detection,detections,activated,removed)
        if record is not None:
            record['activated_IDs_after_stage']=[t.track_id for t in activated]
            record['removed_IDs_after_stage']=[t.track_id for t in removed]
            self.stage_log.append(record)
        return result
class LoggedProbe(UnconfirmedIoUTracker):
    def _unconfirmed_association(self,unconfirmed,u_detection,detections,activated,removed):
        record=None
        if self.source_frame0 in self.focus_frames:
            remain=[detections[i] for i in u_detection]
            iou=matching.iou_distance(unconfirmed,remain);fused=matching.fuse_score(iou,remain)
            record={'frame0':self.source_frame0,'unconfirmed_IDs':[t.track_id for t in unconfirmed],
                'detection_scores':[float(t.score) for t in remain],'detection_xyxy':[t.xyxy.tolist() for t in remain],
                'pure_IoU_cost':iou.tolist(),'fused_cost':fused.tolist(),'threshold':.7}
        result=super()._unconfirmed_association(unconfirmed,u_detection,detections,activated,removed)
        if record is not None:
            record['activated_IDs_after_stage']=[t.track_id for t in activated]
            record['removed_IDs_after_stage']=[t.track_id for t in removed]
            self.stage_log.append(record)
        return result
def compare(actual,expected,board):
    actual=canonical(actual)
    maxbox=maxaxis=0.
    if not board:
        for key in ['observations','post_tracker','confirmed_only_events','handoff_events']:assert actual[key]==expected[key],key
        return {'strict_complete_core_trace_exact':True,'max_box_error':0.,'max_axis_error':0.}
    for kind in ['confirmed_only_events','handoff_events']:assert actual[kind]==expected[kind]
    assert len(actual['post_tracker'])==len(expected['post_tracker']) and len(actual['observations'])==len(expected['observations'])
    for a,b in zip(actual['post_tracker'],expected['post_tracker']):
        assert all(a[k]==b[k] for k in ['frame0','time_s','track_id','confidence'])
        delta=max(abs(x-y) for x,y in zip(a['xyxy'],b['xyxy']));assert delta<=.002;maxbox=max(maxbox,delta)
    for a,b in zip(actual['observations'],expected['observations']):
        assert all(a[k]==b[k] for k in ['frame0','time_s','confirmed_IDs'])
        for key in ['confirmed_positions','tentative_positions']:
            assert a[key].keys()==b[key].keys()
            for tid in a[key]:
                delta=abs(a[key][tid]-b[key][tid]);assert delta<=2e-6;maxaxis=max(maxaxis,delta)
        assert len(a['accepted_history'])==len(b['accepted_history'])
        for x,y in zip(a['accepted_history'],b['accepted_history']):
            assert all(x[k]==y[k] for k in ['track_id','observation_time_s','confirmation_time_s'])
            delta=abs(x['axis_position']-y['axis_position']);assert delta<=2e-6;maxaxis=max(maxaxis,delta)
    return {'strict_complete_core_trace_exact':actual==expected,'IDs_events_and_keys_exact':True,'max_box_error':maxbox,'max_axis_error':maxaxis}
def replay(c,p,cls):
    pipeline_module.BYTETracker=cls
    pipe=pipeline_module.FramePipeline(c['spec'],p['tracker_config'],p['counter_kwargs'])
    pipe.tracker.focus_frames=[9545,9550,9555,9560,9565,9570,9610] if c['id']=='new_O8_original_s5' else []
    pipe.tracker.stage_log=[]
    rows=gz(c['raw_file']);raw={r['frame0']:r['predictions'] for r in rows}
    trace={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]}
    for frame in range(0,c['spec']['decode_end_exclusive'],c['stride']):
        pipe.tracker.source_frame0=frame
        r=pipe.update(frame,raw[frame]);trace['observations'].append(r['observation'])
        for key in ['post_tracker','confirmed_only_events','handoff_events']:trace[key].extend(r[key])
        assert pipe.tracker.args.fuse_score==p['tracker_config']['fuse_score']
    return trace,pipe.tracker.stage_log
def scores(c,trace,variant):
    rows=[]
    for window in c['windows']:
        for kind in ['confirmed_only_events','handoff_events']:
            events=[e for e in trace[kind] if window['start']<=e['frame0']<window['end']]
            row={'cache':c['id'],'label':c['label'],'scene':c['scene'],'stride':c['stride'],'variant':variant,'window':window['name'],
                'counter':kind,'down':sum(e['direction']=='A->B' for e in events),'up':sum(e['direction']=='B->A' for e in events),'events':events,
                'formal_event_metrics':evaluate_events(c['reference_events'],events,2.) if c['formal_event_scoring_allowed'] and c['reference_events'] else None,
                'human_total':c.get('human_total'),'reference_is_independent_new_GT':False}
            rows.append(row)
    return rows

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    p=load(ROOT/'protocol/control_v1.json');e=load(ROOT/'protocol/execution_v1.json')
    assert e['protocol_sha256']==sha(ROOT/'protocol/control_v1.json')
    for file,digest in e['files_sha256'].items():assert sha(ROOT/file)==digest,file
    for row in p['port_files']:assert sha(PROJECT/'pynq_frontend_port_20261029'/row['file'])==row['sha256']
    for c in p['caches']:assert sha(c['raw_file'])==c['raw_sha256'] and sha(c['trace_file'])==c['trace_sha256'],c['id']
    out=ROOT/'results/control';out.mkdir(parents=True,exist_ok=False);started=time.monotonic_ns();gate=[];metrics=[];ticks=0
    for i,c in enumerate(p['caches']):
        actual,log=replay(c,p,LoggedBase);expected=gz(c['trace_file']);result=compare(actual,expected,c['board_reference'])
        gate.append({'cache':c['id'],'observation_ticks':len(actual['observations']),**result})
        folder=out/c['id'];folder.mkdir();savegz(folder/'baseline_trace.json.gz',actual)
        save(folder/'baseline_focus.json',log);metrics.extend(scores(c,actual,'baseline'));ticks+=len(actual['observations'])
        if i%20==0:print(json.dumps({'baseline_complete':i+1,'caches':len(p['caches']),'probe_started':False}),flush=True)
    assert len(gate)==111
    save(out/'all_baselines_gate.json',{'status':'ALL111_BASELINE_OBSERVATIONS_IDS_EVENTS_REPRODUCED_BEFORE_PROBE','records':gate,'baseline_tracker_updates':ticks,'new_probe_updates_at_gate':0})
    for i,c in enumerate(p['caches']):
        actual,log=replay(c,p,LoggedProbe);folder=out/c['id'];savegz(folder/'unconfirmed_pure_IoU_trace.json.gz',actual)
        save(folder/'unconfirmed_pure_IoU_focus.json',log);metrics.extend(scores(c,actual,'unconfirmed_pure_IoU'));ticks+=len(actual['observations'])
        if i%20==0:print(json.dumps({'probe_complete':i+1,'caches':len(p['caches'])}),flush=True)
    save(out/'metrics.json',metrics)
    paired=[]
    for row in [r for r in metrics if r['variant']=='baseline']:
        other=next(r for r in metrics if r['variant']=='unconfirmed_pure_IoU' and all(r[k]==row[k] for k in ['cache','window','counter']))
        paired.append({'cache':row['cache'],'label':row['label'],'scene':row['scene'],'stride':row['stride'],'window':row['window'],'counter':row['counter'],
            'baseline_down':row['down'],'control_down':other['down'],'baseline_up':row['up'],'control_up':other['up'],
            'baseline_TP_FP_FN':[row['formal_event_metrics'][k] for k in ['TP','FP','FN']] if row['formal_event_metrics'] else None,
            'control_TP_FP_FN':[other['formal_event_metrics'][k] for k in ['TP','FP','FN']] if other['formal_event_metrics'] else None})
    save(out/'paired_metrics.json',paired)
    for c in p['caches']:assert sha(c['raw_file'])==c['raw_sha256'] and sha(c['trace_file'])==c['trace_sha256']
    assert 'torch' not in sys.modules and len(p['caches'])==111
    summary={'status':'ALL111_FIXED_CACHES222_TRACKER_CONDITIONS444_COUNTER_PATHS_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
        'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/control_v1.json'),'caches':111,'tracker_conditions':222,'counter_paths':444,
        'tracker_updates':ticks,'scope_metric_rows':len(metrics),'paired_metric_rows':len(paired),'all111_baseline_gate_before_control':True,
        'all_raw_and_existing_traces_unchanged':True,'new_model_forwards':0,'new_training_updates':0,'board_actions':0,
        'global_tracker_files_modified':False,'new_independent_test':False,'adopted_for_deployment':False,'whole_goal_complete':False,
        'wall_s':(time.monotonic_ns()-started)/1e9}
    save(out/'summary.json',summary)
    save(ROOT/'results/artifact_manifest.json',[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()])
    print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
