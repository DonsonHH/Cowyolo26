"""Paced-file two-call budget experiment; local measurements replace a global call."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time
import traceback
import uuid

import numpy as np

from .backends import O8Detector, decode
from .birth_refinement import BirthRefinement
from .budget_schedule import PairBudgetPlan, CallLedger
from .endpoint_recovery import EndpointRecovery
from .geometry import Transform
from .tracking import TrackingSession


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def propose_local(pts,detections,tracking,birth,recovery):
    existing=detections[detections[:,4]>=birth.high_threshold]
    endpoint=recovery.proposals(pts,existing,tracking.counter.states,tracking.counter.stable_samples)
    if endpoint:
        if len(endpoint)!=1:raise ValueError('At most one local slot exists in a block')
        return {'kind':'endpoint','proposal':endpoint[0]}
    proposal=birth.proposal(pts,detections,tracking.tracker.tracked_stracks)
    return None if proposal is None else {'kind':'birth','proposal':proposal}


def merge_local(record,raw,base,pts,local,tracking,birth,recovery,config):
    """Same selectors as the qualified runtime; no second tracker update per image."""
    p=record['proposal']
    candidates=decode(raw,local,config['confidence'],config['cow_class_ids'])
    selected=None
    used=None
    merged=base.copy()
    if record['kind']=='endpoint':
        candidates=candidates[candidates[:,4]>=birth.low_threshold]
        existing=base[base[:,4]>=birth.high_threshold]
        selected=recovery.select(p,candidates,existing)
        if selected is not None:
            used=selected
            competitors={}
            for track in tracking.tracker.tracked_stracks+tracking.tracker.lost_stracks:
                observed=getattr(track,'observations',())
                if observed and 0 < pts-observed[-1][0] <= recovery.max_age:
                    competitors[f'{tracking.epoch}:{track.track_id}']=track.box_at(pts)
            removed=recovery.superseded_global_indices(p,selected,base,pts,birth.high_threshold,competitors)
            keep=np.ones(len(base),dtype=bool);keep[removed]=False
            merged=np.concatenate((base[keep],selected[None]))
            record['superseded_global_detections']=base[removed].tolist()
    else:
        selected=birth.select(p,candidates,base)
        if selected is not None:
            used=birth.fuse(base[p['seed_index']],selected)
            merged[p['seed_index']]=used
    record.update(transform=asdict(local),candidates=candidates.tolist(),
                  accepted_detection=None if selected is None else selected.tolist(),
                  fused_detection=None if used is None else used.tolist(),
                  fusion_mode='global_geometry_local_score' if record['kind']=='birth' and birth.preserve_global_geometry else 'local_geometry')
    return merged


def _execute(source,config,policy,output,detector_factory,capture_factory,summary,resources):
    from .realtime import LatestCapture
    from .runner import Timing,validate_config
    import cv2
    validate_config(config)
    if policy not in ('global_pair','conditional_local_pair'):
        raise ValueError('Choose a declared pair-budget policy')
    if config.get('decode_start_frame0',0) or config.get('scope_start_frame0',0):
        raise ValueError('Input must be a complete prepared CFR interval')
    output=Path(output)
    started=time.monotonic()
    cv2.setNumThreads(1)
    capture_config={**config.get('capture',{}),'history_maximum_age_s':None,'buffer_frames':2,
                    'publication_stride_frames':2}
    capture=(capture_factory or LatestCapture)(source,'paced-file',capture_config)
    resources['capture']=capture
    if [capture.width,capture.height]!=config['expected_capture_size'] or abs(capture.nominal_fps-5)>1e-8:
        raise ValueError('This experiment requires the frozen full-view 5Hz input')
    plan=PairBudgetPlan(config['expected_capture_frames'],source_fps=capture.nominal_fps)
    ledger=CallLedger(plan)
    session_id=config['session_id'];run_id=str(uuid.uuid4())
    # Nominal tracker clock stays at 5Hz in BOTH policies; actual PTS supplies dt.
    tracking=TrackingSession(config,capture.width,capture.height,5.,session_id)
    birth=BirthRefinement(config,capture.width,capture.height)
    recovery=EndpointRecovery(config,capture.width,capture.height)
    files={}
    resources['files']=files
    for n in ('frames.jsonl','events.jsonl','uncertain.jsonl','calls.jsonl','attempts.jsonl','raw_outputs.npyseq'):
        files[n]=(output/n).open('wb' if n=='raw_outputs.npyseq' else 'w')
    scope={'run_id':run_id,'session_id':session_id,'video_id':config['video_id']}
    summary.update({**scope,'status':'STARTING','config':config,'policy':policy,'source_kind':'paced-file',
             'video_sha256':sha(source),'source':str(source),'source_size':[capture.width,capture.height],
             'nominal_fps':capture.nominal_fps,'time_source':'verified relative CFR source PTS',
             'planned_real_calls':plan.real_call_budget,'tracker_nominal_hz':5.,
             'counts':{'IN':0,'OUT':0,'NET':0},'warmup_model_forwards':0,'model_forwards':0,
             'base_model_forwards':0,'endpoint_recovery_forwards':0,'birth_refinement_forwards':0,
             'processed_frames':0,'uncertain_records':0,'software_fixture_only':detector_factory is not None,
             'accuracy_verified':False,'future_frame_violations':0,'schedule_discarded_frames':0,
             'latency_boundary':'Scheduled observation-frame arrival through tracking and event flush; observation_age additionally includes frame-ledger flush and progress save. Frame observation_age_ms is pre-ledger-write. Terminal cleanup excluded.',
             'inference_timing_boundary':'inference_elapsed_ms surrounds infer_bgr only; attempt_to_return_ms additionally includes STARTED receipt flush.',
             'startup_scope':'Source open/hash, model initialization and warmup; Python imports excluded.',
             'budget_definition':'Each primary slot global; second slot same-block global or causal first-image local. Tail has no extra local call.'})
    summary['queue_admission']='Read every source frame; publish only even frame0 values admitted by the frozen call schedule. Same two-packet queue for both policies.'
    event_timing=Timing();observation_timing=Timing()
    detector=None;sequence=-1
    def save():
        (output/'progress.json').write_text(json.dumps(summary,indent=2)+'\n')
    def write(name,row):
        files[name].write(json.dumps(row,allow_nan=False)+'\n');files[name].flush()
    def next_frame(expected):
        nonlocal sequence
        while True:
            packet=capture.take_after(sequence,prefer_history=True)
            if packet is None:raise ValueError(f'EOF before planned frame {expected}')
            sequence=packet[0]
            if sequence<expected:
                summary['schedule_discarded_frames']+=1
                continue
            if sequence>expected:raise ValueError(f'Planned frame {expected} unavailable; observed {sequence}')
            if abs(packet[1]-sequence/capture.nominal_fps)>1e-6:
                raise ValueError('A source timestamp differs from the admitted CFR frame')
            if time.monotonic()+1e-6<packet[2]:
                summary['future_frame_violations']+=1
                raise ValueError('A frame was used before its known arrival')
            return packet
    def infer(block,slot,kind,observation_packet,transform,local_kind=None):
        frame,pts,due,image=observation_packet
        canvas=transform.prepare_bgr_resize_first(image)
        summary['model_forward_attempts']+=1
        call_start=time.monotonic()
        release=block.first_frame0 if slot==0 else block.second_frame0
        attempt={**scope,'block':block.index,'slot':slot,'kind':kind,'observation_frame0':frame,
                 'release_frame0':release,'release_source_time_s':release/capture.nominal_fps,
                 'call_start_since_stream_s':call_start-capture.started,
                 'attempt':summary['model_forward_attempts'],'status':'STARTED'}
        write('attempts.jsonl',attempt)
        try:
            inference_start=time.monotonic()
            raw=detector.infer_bgr(canvas)
            inference_end=time.monotonic()
        except BaseException:
            write('attempts.jsonl',{**attempt,'status':'FAILED_OR_UNKNOWN_WORK'})
            raise
        summary['model_forwards']+=1
        if kind=='global':summary['base_model_forwards']+=1
        else:
            key='endpoint_recovery_forwards' if local_kind=='endpoint' else 'birth_refinement_forwards'
            summary[key]+=1
        call_end=time.monotonic()
        returned={**attempt,'status':'RETURNED','call_end_since_stream_s':call_end-capture.started,
                  'inference_elapsed_ms':(inference_end-inference_start)*1000,
                  'attempt_to_return_ms':(call_end-call_start)*1000}
        write('attempts.jsonl',returned)
        ledger.record(block.index,slot,kind,frame,
                      hashlib.sha256(canvas.tobytes()).hexdigest(),
                      hashlib.sha256(np.asarray(raw).tobytes()).hexdigest())
        np.save(files['raw_outputs.npyseq'],raw,allow_pickle=False)
        write('calls.jsonl',{**returned,**ledger.records[-1],'source_time_s':pts,
                            'wall_since_stream_start_s':time.monotonic()-capture.started,
                            'output_shape':list(np.asarray(raw).shape),'output_dtype':str(np.asarray(raw).dtype)})
        return raw
    def observe(packet,base,measurements,local_record=None):
        frame,pts,due,image=packet
        tracks,events,uncertain=tracking.update(frame,pts,measurements)
        if recovery.enabled:recovery.record(pts,tracks,tracking.counter.states)
        birth.record(pts,base)
        for event in events:
            age=(time.monotonic()-due)*1000
            write('events.jsonl',{**event,**scope,'decision_age_ms':age,
                                  'wall_decision_s':time.monotonic()-capture.started})
            event_timing.add((time.monotonic()-due)*1000)
            summary['counts'][event['kind']]+=1
        for row in uncertain:
            write('uncertain.jsonl',{**row,**scope});summary['uncertain_records']+=1
        summary['counts']['NET']=summary['counts']['IN']-summary['counts']['OUT']
        age=(time.monotonic()-due)*1000
        write('frames.jsonl',{**scope,'frame0':frame,'time_s':pts,'base_detections':base.tolist(),
                              'detections':measurements.tolist(),'local_record':local_record,
                              'tracks':tracks,'counts':summary['counts'].copy(),'observation_age_ms':age})
        summary['processed_frames']+=1
        summary.update(last_frame0=frame,last_source_time_s=pts)
        save()
        observation_timing.add((time.monotonic()-due)*1000)
    try:
        model=config['detector']
        if detector_factory:detector=detector_factory(model)
        else:
            if model.get('backend')!='o8':
                raise ValueError('The real pair-budget runner is qualified only for O8')
            detector=O8Detector(**{k:model[k] for k in ('root','program','plan','size')})
        resources['detector']=detector
        if detector_factory is None:
            summary.update(model_sha256=sha(Path(model['program'])/'graph.bin'),
                           resident_plan_sha256=sha(model['plan']),device_initialization=detector.initialization)
        summary['warmup_model_forward_attempts']=1
        write('attempts.jsonl',{**scope,'kind':'warmup','status':'STARTED'})
        try:raw=detector.infer_bgr(np.full((detector.size,detector.size,3),114,np.uint8))
        except BaseException:
            write('attempts.jsonl',{**scope,'kind':'warmup','status':'FAILED_OR_UNKNOWN_WORK'})
            raise
        summary['warmup_model_forwards']=1;summary['model_forwards']=1
        write('attempts.jsonl',{**scope,'kind':'warmup','status':'RETURNED'})
        transform=Transform.create(capture.width,capture.height,config['detection_roi_xyxy'],
                                   config['rotation_clockwise'],detector.size)
        summary.update(status='RUNNING',startup_s=time.monotonic()-started)
        save();capture.start()
        for block in plan.blocks:
            primary=next_frame(block.first_frame0)
            raw=infer(block,0,'global',primary,transform)
            base=decode(raw,transform,config['confidence'],config['cow_class_ids'])
            proposal=(propose_local(primary[1],base,tracking,birth,recovery)
                      if policy=='conditional_local_pair' and block.second_frame0 is not None else None)
            decision=plan.decision(block,policy,proposal is not None)
            if not proposal:observe(primary,base,base)
            if decision is None:continue
            # Both policies wait for the identical next scheduled source packet.
            # Eligibility uses the primary image and past state, and is fixed
            # before consuming the secondary packet even if it has arrived.
            secondary=next_frame(block.second_frame0)
            if proposal:
                local=Transform.create(capture.width,capture.height,proposal['proposal']['roi'],
                                       transform.rotation,detector.size)
                raw=infer(block,1,'local',primary,local,proposal['kind'])
                merged=merge_local(proposal,raw,base,primary[1],local,tracking,birth,recovery,config)
                observe(primary,base,merged,proposal)
            else:
                raw=infer(block,1,'global',secondary,transform)
                secondary_base=decode(raw,transform,config['confidence'],config['cow_class_ids'])
                observe(secondary,secondary_base,secondary_base)
        while True:
            packet=capture.take_after(sequence,prefer_history=True)
            if packet is None:break
            sequence=packet[0];summary['schedule_discarded_frames']+=1
        if capture.frames!=config['expected_capture_frames']:
            raise ValueError('Capture did not cover the full admitted source')
        summary['budget']=ledger.finish()
        for row in tracking.finish():
            write('uncertain.jsonl',{**row,**scope});summary['uncertain_records']+=1
        summary['status']='COMPLETED_UNSCORED'
    except BaseException as e:
        summary.update(status='FAILED',error=repr(e))
        raise
    finally:
        resources['event_timing']=event_timing
        resources['observation_timing']=observation_timing
    return summary


def run(source,config,policy,output,detector_factory=None,capture_factory=None):
    """Persist setup/inference failures without allowing cleanup to hide their cause."""
    from .runner import memory_snapshot
    output=Path(output);output.mkdir(exist_ok=False,parents=True)
    started=time.monotonic()
    summary={'status':'STARTING','run_id':str(uuid.uuid4()),'policy':policy,'source':str(source),'config':config,
             'software_fixture_only':detector_factory is not None,
             'model_forward_attempts':0,'warmup_model_forward_attempts':0,'model_forwards':0}
    resources={}
    primary_error=None
    try:
        return _execute(source,config,policy,output,detector_factory,capture_factory,summary,resources)
    except BaseException as error:
        primary_error=error
        summary.update(status='FAILED',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        cleanup=[]
        capture=resources.get('capture')
        owned=[capture,*resources.get('files',{}).values(),resources.get('detector')]
        for resource in owned:
            if resource is not None:
                try:resource.close()
                except Exception as error:cleanup.append(repr(error))
        for resource_key,key in (('event_timing','event_publication'),('observation_timing','observation_age')):
            if resource_key in resources:
                try:summary[key]=resources[resource_key].summary()
                except Exception as error:cleanup.append(repr(error))
        if capture is not None:
            try:summary['capture']=capture.snapshot()
            except Exception as error:cleanup.append(repr(error))
            if capture.started is not None and capture.last_pts is not None:
                summary.update(stream_wall_elapsed_s=time.monotonic()-capture.started,
                               source_duration_s=capture.last_pts,
                               drain_after_last_source_frame_s=time.monotonic()-capture.started-capture.last_pts)
        summary['elapsed_s']=time.monotonic()-started
        try:summary['memory']=memory_snapshot()
        except Exception as error:cleanup.append('memory_snapshot: '+repr(error))
        if cleanup:
            summary['cleanup_errors']=cleanup
            if primary_error is None:summary['status']='CLEANUP_FAILED'
        try:
            temporary=output/'summary.writing'
            temporary.write_text(json.dumps(summary,indent=2)+'\n')
            temporary.replace(output/'summary.json')
        except Exception as write_error:
            import sys
            print('FAILED_TO_WRITE_BUDGET_TERMINAL '+repr(write_error),file=sys.stderr,flush=True)
            if primary_error is None:raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--policy',required=True,choices=('global_pair','conditional_local_pair'))
    parser.add_argument('--output',required=True,type=Path)
    a=parser.parse_args()
    s=run(a.source,json.loads(a.config.read_bytes()),a.policy,a.output)
    if s['status']!='COMPLETED_UNSCORED':raise SystemExit(1)
