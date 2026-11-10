"""Scheduled global coverage with additional real calls; software fixtures only."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
from . import realtime
from . import test_budget_runner as fixtures

class Capture:
    width=height=100
    nominal_fps=5.
    frames=5
    last_pts=.8
    started=None
    last_take_history=False
    indices=(0,2,4)
    preferences=[]
    def __init__(self,*args):self.i=0;type(self).preferences=[]
    def start(self):self.started=time.monotonic()-2
    def take_after(self,sequence,prefer_history=False):
        self.preferences.append(prefer_history)
        if self.i==len(self.indices):return None
        frame=self.indices[self.i];self.i+=1
        return frame,frame/5,self.started+frame/5,np.full((100,100,3),frame,np.uint8)
    def snapshot(self):
        return {'captured_frames':5,'published_frames':3,'not_admitted_frames':2,
                'publication_stride_frames':2,'maximum_application_queue_frames':2,
                'capture_done':True,'capture_error':None,'capture_lateness_ms':{'maximum_ms':0}}
    def close(self):pass

class Detector:
    size=32
    pixels=[]
    def __init__(self):type(self).pixels=[]
    def infer_bgr(self,image):
        self.pixels.append(int(image[16,16,0]))
        return np.array([[[8,8,24,24,.12,0]]],np.float32)
    def close(self):pass

class ScheduledRealtimeTests(unittest.TestCase):
    def config(self):
        cfg=fixtures.BudgetRunnerTests().config()
        cfg.update(source_selection='scheduled_global',expected_capture_frames=5,
                   end_frame0_exclusive=5,preprocess_mode='resize_first_v1',
                   detector_input='native_bgr',warmup_model_forwards=1)
        cfg['capture']={'buffer_frames':2,'publication_stride_frames':2,'history_maximum_age_s':None}
        return cfg
    def execute(self,extra=False,capture=Capture):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'fixture';source.write_bytes(b'SOFTWARE_ONLY')
            with patch.object(realtime,'LatestCapture',capture), \
                 patch.object(realtime.BirthRefinement,'proposal',side_effect=lambda pts,*_:(
                    {'roi':[0,0,100,100],'seed_index':0} if extra and pts==0 else None)), \
                 patch.object(realtime.BirthRefinement,'select',return_value=None):
                result=realtime.run(source,self.config(),root/'run',detector_factory=lambda _:Detector())
            frames=[json.loads(x) for x in (root/'run/frames.jsonl').read_text().splitlines()]
            return result,frames,Detector.pixels[:]
    def test_all_scheduled_global_images_are_consumed_oldest_first(self):
        s,frames,pixels=self.execute()
        self.assertEqual([r['frame0'] for r in frames],[0,2,4])
        self.assertTrue(all(Capture.preferences))
        self.assertEqual(pixels,[114,0,2,4])
        self.assertEqual((s['base_model_forwards'],s['model_forwards']),(3,4))
        self.assertEqual((s['target_detector_hz'],s['tracker_nominal_hz']),(2.5,5.))
        self.assertTrue(s['software_fixture_only'])
    def test_local_verification_adds_a_call_without_replacing_a_global(self):
        s,frames,pixels=self.execute(True)
        self.assertEqual([r['frame0'] for r in frames],[0,2,4])
        self.assertEqual(pixels,[114,0,0,2,4])
        self.assertEqual((s['base_model_forwards'],s['birth_refinement_forwards'],s['model_forwards']),(3,1,5))
    def test_lost_global_is_failed_instead_of_silently_substituted(self):
        class Missing(Capture):indices=(0,4)
        with self.assertRaisesRegex(ValueError,'Scheduled global frame 2 unavailable'):
            self.execute(capture=Missing)
    def test_incompatible_modes_are_rejected_before_device_open(self):
        for live,age in [(True,None),(False,.3)]:
            cfg=self.config();cfg['capture']['history_maximum_age_s']=age
            with patch.object(realtime,'LatestCapture') as opened:
                with self.assertRaisesRegex(ValueError,'scheduled_global requires'):
                    realtime.run('DO_NOT_OPEN',cfg,'NOT_CREATED',source_kind='live' if live else 'paced-file')
                opened.assert_not_called()
if __name__=='__main__':unittest.main()
