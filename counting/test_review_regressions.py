"""Cloud-only software regressions; fixtures are not cattle accuracy evidence."""
import io
import json
from collections import deque
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import numpy as np

from . import realtime
from .evaluate import evaluate_run
from .geometry import Transform
from .protocol import gate_from_config
from .render import render


class ScriptedCapture:
    width=height=1000
    nominal_fps=5
    frames=6
    last_pts=1.
    last_take_history=False
    packets=((0,0.),(1,.2),(5,1.))
    def __init__(self,*args):self.index=0;self.started=None
    def start(self):self.started=time.monotonic()-2.
    def take_after(self,sequence,prefer_history=False):
        if self.index==len(self.packets):return None
        frame,stamp=self.packets[self.index];self.index+=1
        return frame,stamp,self.started+stamp,np.zeros((1000,1000,3),np.uint8)
    def snapshot(self):
        return {'captured_frames':self.frames,'overwritten_before_read':self.frames-len(self.packets),'maximum_application_queue_frames':2,
                'history_frames_processed':0,'last_source_time_s':self.last_pts,'source_time_origin_s':0.,
                'capture_lateness_ms':{'maximum_ms':0.},'capture_done':True,'capture_error':None}
    def close(self):pass


class StaggeredCapture(ScriptedCapture):
    frames=7
    last_pts=1.2
    packets=((0,0.),(1,.2),(2,.4),(6,1.2))


class OverlappingDetector:
    size=1000
    def __init__(self,true_neighbor):self.calls=0;self.true_neighbor=true_neighbor
    def infer(self,tensor):
        self.calls+=1
        if self.calls in (1,2):
            delta=0 if self.calls==1 else 100
            rows=[[300,delta,500,400+delta,.9,0],[350,delta,550,400+delta,.9,0]]
        elif self.calls==3:
            x=350 if self.true_neighbor else 300
            rows=[[x,500,x+200,900,.12,0]]
        elif self.calls==4:
            local=Transform.create(1000,1000,[250,400,550,1000],0,1000)
            box=local.boxes([[300,500,500,900]])[0].tolist()
            rows=[box+[.9,0]]
        else:raise AssertionError('Unexpected additional fake model call')
        return np.asarray([rows],np.float32)
    def close(self):pass


class StaggeredDetector(OverlappingDetector):
    def infer(self,tensor):
        self.calls+=1
        if self.calls==1:
            rows=[[300,0,500,400,.9,0]]
        elif self.calls in (2,3):
            delta=0 if self.calls==2 else 100
            rows=[[300,delta,500,400+delta,.9,0],[350,delta,550,400+delta,.9,0]]
        elif self.calls==4:
            rows=[[350,500,550,900,.12,0]]
        elif self.calls==5:
            local=Transform.create(1000,1000,[250,400,550,1000],0,1000)
            rows=[local.boxes([[300,500,500,900]])[0].tolist()+[.9,0]]
        else:raise AssertionError('Unexpected additional fake model call')
        return np.asarray([rows],np.float32)


def fixture_run(root,true_neighbor=False,staggered=False):
    source=root/'SOFTWARE_FIXTURE.bin';source.write_bytes(b'fixture bytes, no real video')
    config={'detector':{},'sample_hz':5,'confidence':.01,'video_id':'SOFTWARE_VIDEO',
            'session_id':'SOFTWARE_SESSION','axis':'y','in_direction':'A->B',
            'scope_start_frame0':0,'end_frame0_exclusive':6,'expected_capture_frames':6,
            'counter':{'lower':.4,'upper':.6,'stable_samples':1,'maximum_gap_s':2},
            'tracker':{'motion_box':'observed_velocity','prediction_axis':'y','track_high_thresh':.15,
                       'track_low_thresh':.1,'new_track_thresh':.25,'match_thresh':.8,'fuse_score':False},
            'endpoint_recovery':{'enabled':True,'roi_scale':1.5,'maximum_age_s':2,
                                 'maximum_per_frame':1,'maximum_extra_forwards':None,'reacquire_missing_tracks':True},
            'birth_refinement':{'enabled':True}}
    capture=StaggeredCapture if staggered else ScriptedCapture
    detector=StaggeredDetector if staggered else OverlappingDetector
    config.update(end_frame0_exclusive=capture.frames,expected_capture_frames=capture.frames)
    with patch.object(realtime,'LatestCapture',capture):
        result=realtime.run(source,config,root/'run',detector_factory=lambda _:detector(true_neighbor))
    return result,root/'run'


class ReviewRegressions(unittest.TestCase):
    def capture_fixture(self,condition=None):
        capture=realtime.LatestCapture.__new__(realtime.LatestCapture)
        capture.kind='paced-file';capture.condition=condition or threading.Condition()
        capture.stop_event=threading.Event();capture.frames=0;capture.error=None;capture.done=False
        capture.nominal_fps=5;capture.first_input_pts=None;capture.last_pts=None
        capture.buffer_frames=2;capture.pending=deque(maxlen=2);capture.latest=None
        capture.overwritten=0;capture.history_reads=0
        capture.lateness=realtime.Timing();capture.read_latency=realtime.Timing()
        capture.enqueue_wait=realtime.Timing()
        return capture

    def test_capture_lateness_includes_wait_until_actual_locked_enqueue(self):
        class Clock:
            value=0.
        clock=Clock()
        class DelayLock:
            def __enter__(self):clock.value+=.25;return self
            def __exit__(self,*args):pass
            def notify_all(self):pass
        class Codec:
            calls=0
            def read(self):
                self.calls+=1
                if self.calls==1:
                    clock.value+=.1
                    return True,np.zeros((1,1,3),np.uint8)
                return False,None
            def get(self,*args):return 0.
        capture=self.capture_fixture(DelayLock());capture.cap=Codec()
        with patch.object(realtime.time,'monotonic',lambda:clock.value):capture._produce()
        self.assertIsNone(capture.error)
        self.assertAlmostEqual(capture.lateness.maximum,350.)

    def test_capture_snapshot_does_not_hold_publish_lock_during_percentiles(self):
        capture=self.capture_fixture();original=realtime.Timing.summary;workers=[]
        def checked_summary(timer):
            acquired=threading.Event()
            def try_lock():
                with capture.condition:acquired.set()
            worker=threading.Thread(target=try_lock,daemon=True);workers.append(worker);worker.start()
            self.assertTrue(acquired.wait(1.),'Percentile calculation blocks frame publication')
            return original(timer)
        try:
            with patch.object(realtime.Timing,'summary',checked_summary):capture.snapshot()
        finally:
            for worker in workers:worker.join(2.)

    def test_stale_history_request_uses_the_latest_arrived_frame(self):
        capture=self.capture_fixture();capture.history_maximum_age_s=.3
        capture.pending.extend([(0,0.,.6,None),(1,.2,.8,None)]);capture.latest=capture.pending[-1]
        with patch.object(realtime.time,'monotonic',lambda:1.):
            packet=capture.take_after(-1,prefer_history=True)
        self.assertEqual(packet[0],1)
        self.assertFalse(capture.last_take_history)
        self.assertEqual(capture.overwritten,1)
        self.assertEqual(getattr(capture,'history_age_guard_overrides',0),1)

    def test_fresh_history_is_retained_under_the_predeclared_age_limit(self):
        capture=self.capture_fixture();capture.history_maximum_age_s=.3
        capture.pending.extend([(0,0.,.75,None),(1,.2,.95,None)]);capture.latest=capture.pending[-1]
        with patch.object(realtime.time,'monotonic',lambda:1.):
            packet=capture.take_after(-1,prefer_history=True)
        self.assertEqual(packet[0],0)
        self.assertTrue(capture.last_take_history)
        self.assertEqual(getattr(capture,'history_age_guard_overrides',0),0)

    def reference(self,root,result):
        value={'review_status':'reviewed','reviewer':'SOFTWARE_FIXTURE_ONLY','reviewed_at':'fixture',
               'source_video_sha256':result['video_sha256'],'reviewed_interval':{'start_frame0':0,'end_frame0':5},
               'review_gate':gate_from_config(result['config']),'matching_tolerance_s':.01,
               'events':[{'event_id':'fixture-reference-1','video_id':result['video_id'],
                          'session_id':result['session_id'],'direction':'A->B','entry_time_s':0.,'time_s':1.,
                          'status':'complete','review_status':'reviewed','key_source_frames0':[0,5],
                          'completion_source_frame0':5,'passage_position_or_local_trajectory':{'x':400,'y':700}}]}
        path=root/'SOFTWARE_REFERENCE.json';path.write_text(json.dumps(value));return path

    def test_local_recovery_does_not_reuse_the_same_weak_global_box_for_neighbor(self):
        with tempfile.TemporaryDirectory() as folder:
            result,run=fixture_run(Path(folder))
            self.assertEqual(result['counts']['IN'],1)
            frame=json.loads((run/'frames.jsonl').read_text().splitlines()[-1])
            self.assertEqual(len(frame['detections']),1)

    def test_local_recovery_preserves_a_genuine_overlapping_weak_neighbor(self):
        with tempfile.TemporaryDirectory() as folder:
            result,run=fixture_run(Path(folder),True)
            self.assertEqual(result['counts']['IN'],2)
            frame=json.loads((run/'frames.jsonl').read_text().splitlines()[-1])
            self.assertEqual(len(frame['detections']),2)

    def test_local_recovery_preserves_neighbor_just_confirmed_after_tentative_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            result,run=fixture_run(Path(folder),True,staggered=True)
            self.assertEqual(result['counts']['IN'],2)
            frame=json.loads((run/'frames.jsonl').read_text().splitlines()[-1])
            self.assertEqual(len(frame['detections']),2)

    def test_combined_recovery_rejects_unqualified_motion_before_capture_or_model(self):
        config={'detector':{},'tracker':{'motion_box':'kalman'},
                'birth_refinement':{'enabled':True},'endpoint_recovery':{'enabled':True}}
        with tempfile.TemporaryDirectory() as folder,patch.object(realtime,'LatestCapture') as capture:
            with self.assertRaisesRegex(ValueError,'requires observed_velocity'):
                realtime.run(Path(folder)/'UNOPENED.bin',config,Path(folder)/'run')
            capture.assert_not_called()

    def test_realtime_events_have_full_video_session_run_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            result,run=fixture_run(Path(folder))
            events=[json.loads(x) for x in (run/'events.jsonl').read_text().splitlines()]
            for event in events:
                self.assertEqual(event.get('video_id'),result['video_id'])
                self.assertEqual(event['session_id'],result['session_id'])
                self.assertEqual(event['run_id'],result['run_id'])

    def test_live_read_failure_is_an_error_not_a_clean_eof(self):
        class FailedCamera:
            def read(self):return False,None
        capture=realtime.LatestCapture.__new__(realtime.LatestCapture)
        capture.kind='live';capture.cap=FailedCamera();capture.condition=threading.Condition()
        capture.stop_event=threading.Event();capture.frames=0;capture.error=None;capture.done=False
        capture.read_latency=realtime.Timing()
        capture._produce()
        self.assertIsNotNone(capture.error)
        self.assertIn('Live capture read failed',capture.error)
        self.assertTrue(capture.done)

    def test_realtime_output_matches_a_valid_scoped_fixture_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);result,run=fixture_run(root)
            score=evaluate_run(run,self.reference(root,result))
            self.assertEqual((score['metrics']['TP'],score['metrics']['FP'],score['metrics']['FN']),(1,0,0))
            self.assertFalse(score['normalization_used'])

    def test_legacy_scope_is_explicit_hash_bound_and_raw_events_stay_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);result,run=fixture_run(root);reference=self.reference(root,result)
            path=run/'events.jsonl';rows=[json.loads(x) for x in path.read_text().splitlines()]
            for row in rows:row.pop('video_id')
            path.write_text(''.join(json.dumps(x)+'\n' for x in rows));original=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'scope is missing'):evaluate_run(run,reference)
            score=evaluate_run(run,reference,normalize_legacy_scope=True)
            self.assertEqual(score['metrics']['TP'],1)
            self.assertTrue(score['normalization_used'])
            self.assertIn('video_id',score['prediction_scope_normalizations'][0]['added_fields'])
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(len(score['input_file_sha256']['events.jsonl']),64)

    def test_scope_normalization_never_accepts_conflicts_or_missing_run_identity(self):
        for field,value in [('video_id','OTHER_VIDEO'),('session_id','OTHER_SESSION'),('run_id',None)]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);result,run=fixture_run(root);reference=self.reference(root,result)
                path=run/'events.jsonl';rows=[json.loads(x) for x in path.read_text().splitlines()]
                rows[0][field]=value;path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
                with self.assertRaises(ValueError):evaluate_run(run,reference,normalize_legacy_scope=True)

    def test_review_renderer_rejects_a_different_source_before_starting_encoder(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);result,run=fixture_run(root)
            wrong=root/'OTHER_SOURCE.bin';wrong.write_bytes(b'different fixture')
            with patch('counting.render.subprocess.Popen') as encoder:
                with self.assertRaisesRegex(ValueError,'SHA256'):render(wrong,run,root/'review.mp4')
                encoder.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
