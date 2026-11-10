"""Functional paired-runner controls using scripted frames and no neural model."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np

from .budget_runner import run


class CaptureFixture:
    width=height=100
    nominal_fps=5.
    frames=7
    last_pts=1.2
    started=None
    skip=None
    def __init__(self,*args):self.index=0
    def start(self):self.started=time.monotonic()-3
    def take_after(self,sequence,prefer_history=False):
        if self.index==self.skip:self.index+=1
        if self.index>=self.frames:return None
        i=self.index;self.index+=1
        return i,i/5,self.started+i/5,np.full((100,100,3),i,np.uint8)
    def close(self):pass
    def snapshot(self):
        return {'captured_frames':self.frames,'capture_done':True,'capture_error':None,
                'maximum_application_queue_frames':2,
                'capture_lateness_ms':{'maximum_ms':0.}}


class DetectorFixture:
    size=32
    def infer_bgr(self,image):return np.zeros((1,0,6),np.float32)
    def close(self):pass


class BudgetRunnerTests(unittest.TestCase):
    def config(self):
        return {'video_id':'SOFTWARE_FIXTURE','session_id':'SOFTWARE_FIXTURE',
                'sample_hz':5,'axis':'y','perpendicular_roi':[0,1],'in_direction':'A->B',
                'scope_start_frame0':0,'end_frame0_exclusive':7,
                'detection_roi_xyxy':[0,0,100,100],'rotation_clockwise':0,
                'confidence':.01,'cow_class_ids':[0],'detector':{},
                'counter':{'lower':.4,'upper':.6,'stable_samples':1,'maximum_gap_s':2},
                'tracker':{'motion_box':'observed_velocity','prediction_axis':'y'},
                'birth_refinement':{'enabled':True},
                'endpoint_recovery':{'enabled':True,'maximum_per_frame':1,'maximum_extra_forwards':None},
                'expected_capture_size':[100,100],'expected_capture_frames':7}

    def fixture(self,policy,force_local=False,capture=CaptureFixture):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);source=p/'SOFTWARE_FIXTURE.bin';source.write_bytes(b'not a cattle video')
            proposal={'kind':'birth','proposal':{'roi':[0,0,100,100],'seed_index':0}}
            with patch('counting.budget_runner.propose_local',return_value=proposal if force_local else None), \
                 patch('counting.budget_runner.merge_local',side_effect=lambda record,raw,base,*args:base):
                result=run(source,self.config(),policy,p/'run',
                           detector_factory=lambda _:DetectorFixture(),capture_factory=capture)
            frames=[json.loads(x) for x in (p/'run/frames.jsonl').read_text().splitlines()]
            calls=[json.loads(x) for x in (p/'run/calls.jsonl').read_text().splitlines()]
            return result,frames,calls

    def test_both_policies_execute_the_same_real_call_budget(self):
        for policy,local in (('global_pair',False),('conditional_local_pair',False),('conditional_local_pair',True)):
            with self.subTest(policy=policy,local=local):
                s,frames,calls=self.fixture(policy,local)
                self.assertTrue(s['software_fixture_only'])
                self.assertEqual(s['status'],'COMPLETED_UNSCORED')
                self.assertEqual((len(calls),s['model_forwards'],s['warmup_model_forwards']),(4,5,1))
                self.assertEqual(s['budget']['executed_real_calls'],4)
                self.assertEqual(s['tracker_nominal_hz'],5.)

    def test_local_reuses_only_the_primary_image_and_updates_once(self):
        s,frames,calls=self.fixture('conditional_local_pair',True)
        self.assertEqual([r['frame0'] for r in frames],[0,4])
        self.assertEqual([r['observation_frame0'] for r in calls],[0,0,4,4])
        self.assertEqual([r['release_frame0'] for r in calls],[0,2,4,6])
        self.assertEqual(s['birth_refinement_forwards'],2)
        self.assertEqual(s['base_model_forwards'],2)

    def test_lost_scheduled_frame_is_a_failure_not_a_future_replacement(self):
        class Missing(CaptureFixture):skip=2
        with self.assertRaisesRegex(ValueError,'unavailable'):
            self.fixture('global_pair',capture=Missing)

    def test_setup_hash_failure_still_closes_capture_and_writes_terminal(self):
        class Capture(CaptureFixture):
            closed=False
            def close(self):type(self).closed=True
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            with self.assertRaises(FileNotFoundError):
                run(p/'missing-source',self.config(),'global_pair',p/'run',
                    detector_factory=lambda _:DetectorFixture(),capture_factory=Capture)
            self.assertTrue(Capture.closed)
            summary=json.loads((p/'run/summary.json').read_text())
            self.assertEqual(summary['status'],'FAILED')
            self.assertEqual(summary['model_forward_attempts'],0)

    def test_inference_exception_records_unknown_work_and_releases_resources(self):
        class Detector(DetectorFixture):
            calls=0
            closed=False
            def infer_bgr(self,image):
                self.calls+=1
                if self.calls>1:raise RuntimeError('inference fixture failure')
                return super().infer_bgr(image)
            def close(self):type(self).closed=True
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);source=p/'fixture';source.write_bytes(b'fixture')
            with self.assertRaisesRegex(RuntimeError,'inference fixture'):
                run(source,self.config(),'global_pair',p/'run',
                    detector_factory=lambda _:Detector(),capture_factory=CaptureFixture)
            s=json.loads((p/'run/summary.json').read_text())
            attempts=[json.loads(x) for x in (p/'run/attempts.jsonl').read_text().splitlines()]
            self.assertEqual((s['status'],s['model_forward_attempts'],s['model_forwards']),('FAILED',1,1))
            self.assertTrue(any(x['status']=='FAILED_OR_UNKNOWN_WORK' for x in attempts))
            self.assertTrue(Detector.closed)

    def test_capture_cleanup_failure_cannot_return_a_completed_run(self):
        class Capture(CaptureFixture):
            def close(self):raise RuntimeError('cleanup fixture')
        s,_,_=self.fixture('global_pair',capture=Capture)
        self.assertEqual(s['status'],'CLEANUP_FAILED')
        self.assertTrue(s['cleanup_errors'])

    def test_optional_memory_failure_preserves_the_original_error_and_terminal(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            with patch('counting.runner.memory_snapshot',side_effect=RuntimeError('memory fixture')):
                with self.assertRaises(FileNotFoundError):
                    run(p/'missing-source',self.config(),'global_pair',p/'run',
                        detector_factory=lambda _:DetectorFixture(),capture_factory=CaptureFixture)
            s=json.loads((p/'run/summary.json').read_text())
            self.assertEqual(s['status'],'FAILED')
            self.assertIn('FileNotFoundError',s['error'])
            self.assertIn('memory_snapshot',s['cleanup_errors'][0])

    def test_optional_memory_failure_on_success_is_explicit(self):
        with patch('counting.runner.memory_snapshot',side_effect=RuntimeError('memory fixture')):
            s,_,_=self.fixture('global_pair')
        self.assertEqual(s['status'],'CLEANUP_FAILED')
        self.assertEqual(s['budget']['executed_real_calls'],4)

    def test_returned_warmup_is_counted_before_receipt_write_failure(self):
        original=Path.open
        class ReceiptFile:
            def __init__(self,wrapped):self.wrapped=wrapped
            def write(self,text):
                row=json.loads(text)
                if row.get('kind')=='warmup' and row.get('status')=='RETURNED':
                    raise OSError('warmup receipt fixture')
                return self.wrapped.write(text)
            def flush(self):return self.wrapped.flush()
            def close(self):return self.wrapped.close()
        def open_file(path,*args,**kwargs):
            opened=original(path,*args,**kwargs)
            return ReceiptFile(opened) if path.name=='attempts.jsonl' else opened
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);source=p/'fixture';source.write_bytes(b'fixture')
            with patch.object(Path,'open',open_file):
                with self.assertRaisesRegex(OSError,'warmup receipt fixture'):
                    run(source,self.config(),'global_pair',p/'run',
                        detector_factory=lambda _:DetectorFixture(),capture_factory=CaptureFixture)
            s=json.loads((p/'run/summary.json').read_text())
            self.assertEqual((s['model_forwards'],s['warmup_model_forwards']),(1,1))
            self.assertEqual(s['status'],'FAILED')

    def test_returned_real_call_is_preserved_if_raw_storage_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);source=p/'fixture';source.write_bytes(b'fixture')
            with patch('counting.budget_runner.np.save',side_effect=OSError('raw receipt fixture')):
                with self.assertRaisesRegex(OSError,'raw receipt fixture'):
                    run(source,self.config(),'global_pair',p/'run',
                        detector_factory=lambda _:DetectorFixture(),capture_factory=CaptureFixture)
            s=json.loads((p/'run/summary.json').read_text())
            rows=[json.loads(x) for x in (p/'run/attempts.jsonl').read_text().splitlines()]
            self.assertEqual((s['model_forward_attempts'],s['model_forwards']),(1,2))
            returned=[r for r in rows if r['status']=='RETURNED' and r['kind']=='global']
            self.assertEqual(len(returned),1)
            self.assertGreaterEqual(returned[0]['attempt_to_return_ms'],returned[0]['inference_elapsed_ms'])
            self.assertEqual(s['status'],'FAILED')


class ScheduledPublicationTests(unittest.TestCase):
    def test_four_packet_queue_retains_the_declared_scheduled_burst_bound(self):
        import cv2
        from .realtime import LatestCapture
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'fixture.avi'
            writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'MJPG'),20.,(100,100))
            self.assertTrue(writer.isOpened())
            for i in range(10):writer.write(np.full((100,100,3),i,np.uint8))
            writer.release()
            capture=LatestCapture(source,'paced-file',{'buffer_frames':4,'publication_stride_frames':2})
            try:
                capture.start();capture.thread.join(timeout=5)
                self.assertFalse(capture.thread.is_alive());self.assertIsNone(capture.error)
                self.assertEqual([p[0] for p in capture.pending],[2,4,6,8])
                self.assertEqual(capture.snapshot()['maximum_application_queue_frames'],4)
                self.assertEqual(capture.snapshot()['published_frames'],5)
            finally:capture.close()

    def test_unbounded_or_noninteger_queue_is_rejected_before_device_open(self):
        from .realtime import LatestCapture
        for value in (True,0,5,2.5):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'from1 to4'):
                LatestCapture('DO_NOT_OPEN','paced-file',{'buffer_frames':value})

    def test_unscheduled_images_cannot_evict_both_scheduled_queue_slots(self):
        import cv2
        from .realtime import LatestCapture
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'fixture.avi'
            writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'MJPG'),20.,(100,100))
            self.assertTrue(writer.isOpened())
            for i in range(10):writer.write(np.full((100,100,3),i,np.uint8))
            writer.release()
            queued={}
            for stride in (1,2):
                capture=LatestCapture(source,'paced-file',{'buffer_frames':2,'publication_stride_frames':stride})
                try:
                    capture.start()
                    capture.thread.join(timeout=5)
                    self.assertFalse(capture.thread.is_alive())
                    self.assertIsNone(capture.error)
                    queued[stride]=[packet[0] for packet in capture.pending]
                    snap=capture.snapshot()
                    self.assertEqual(snap['captured_frames'],10)
                    self.assertEqual(snap['published_frames']+snap['not_admitted_frames'],10)
                    self.assertEqual(snap['maximum_application_queue_frames'],2)
                    if stride==2:
                        self.assertEqual(snap['not_admitted_frames'],5)
                        self.assertEqual(snap['last_source_time_s'],.45)
                finally:capture.close()
            self.assertEqual(queued[1],[8,9])
            self.assertEqual(queued[2],[6,8])

    def test_invalid_publication_or_live_schedule_is_rejected_before_device_open(self):
        from .realtime import LatestCapture
        for value in (True,0,3,2.0):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'publication_stride_frames'):
                LatestCapture('never-open-this-device','paced-file',{'publication_stride_frames':value})
        with self.assertRaisesRegex(ValueError,'only for paced-file'):
            LatestCapture('never-open-this-device','live',{'publication_stride_frames':2})


if __name__=='__main__':unittest.main()
