"""Scoring and geometry regressions; all observations are generated fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

from .counter import PassageCounter
from .evaluate import evaluate_run
from .geometry import Transform
from .protocol import gate_from_config
from maintenance.counting_r1.event_metrics_v2 import evaluate_events


class EvaluationIntegrityTests(unittest.TestCase):
    def test_explicit_duplicate_ids_rejected_on_either_side(self):
        row={'event_id':'same','direction':'A->B','time_s':1.,'video_id':'v','session_id':'s'}
        for ref,pred in (([row,row],[row]),([row],[row,row]),([row,row],[row,row])):
            with self.subTest(reference=len(ref),prediction=len(pred)):
                with self.assertRaises(ValueError):evaluate_events(ref,pred)

    def test_identical_ids_in_different_scopes_are_distinct(self):
        row={'event_id':'same','direction':'A->B','time_s':1.,'video_id':'v','session_id':'s'}
        other={**row,'session_id':'another'}
        self.assertEqual(evaluate_events([row,other],[row,other])['TP'],2)

    def play_reference(self,modify):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            config={'axis':'y','perpendicular_roi':[0,1],
                    'counter':{'lower':.4,'upper':.6},'scope_start_frame0':0,'end_frame0_exclusive':21}
            s={'status':'COMPLETED_UNSCORED','run_id':'fixture-run','video_id':'v','session_id':'s',
               'video_sha256':'FIXTURE','config':config,'uncertain_records':0,'nominal_fps':5.,
               'time_source':'verified relative CFR source PTS'}
            event={'event_id':'ref1','direction':'A->B','video_id':'v','session_id':'s',
                   'entry_time_s':0.,'time_s':2.,'key_source_frames0':[0,10],
                   'completion_source_frame0':10,'status':'complete','review_status':'reviewed',
                   'passage_position_or_local_trajectory':{'x':.5,'y':.7}}
            ref={'review_status':'reviewed','reviewer':'SOFTWARE_FIXTURE','reviewed_at':'fixture',
                 'source_video_sha256':'FIXTURE','reviewed_interval':{'start_frame0':0,'end_frame0':20},
                 'review_gate':gate_from_config(config),'events':[event]}
            pred={**event,'event_id':'pred1','run_id':'fixture-run','frame0':10,'entry_frame0':0}
            modify(ref,pred)
            (p/'summary.json').write_text(json.dumps(s))
            (p/'events.jsonl').write_text(json.dumps(pred)+'\n')
            path=p/'reference.json';path.write_text(json.dumps(ref))
            return evaluate_run(p,path)

    def test_valid_frame_bound_reference(self):
        self.assertEqual(self.play_reference(lambda ref,pred:None)['metrics']['TP'],1)

    def test_reference_completion_time_not_arbitrary(self):
        def change(ref,pred):ref['events'][0]['time_s']=1e6
        with self.assertRaises(ValueError):self.play_reference(change)

    def test_reference_keyframes_must_be_within_the_window(self):
        def change(ref,pred):ref['events'][0]['key_source_frames0']=[0,99999]
        with self.assertRaises(ValueError):self.play_reference(change)

    def test_prediction_completion_time_not_arbitrary(self):
        def change(ref,pred):pred['time_s']=1e6
        with self.assertRaises(ValueError):self.play_reference(change)

    def test_prediction_frame_outside_window_is_rejected(self):
        def change(ref,pred):pred['frame0']=99999
        with self.assertRaises(ValueError):self.play_reference(change)

    def test_fractional_or_boolean_reference_frame_rejected(self):
        for frame in (True,10.5):
            def change(ref,pred):ref['events'][0]['completion_source_frame0']=frame
            with self.subTest(frame=frame),self.assertRaises(ValueError):self.play_reference(change)

    def test_crop_inverse_is_limited_to_observed_region(self):
        for rotation in (0,90,180,270):
            transform=Transform.create(1000,720,[100,200,500,600],rotation,256)
            mapped=transform.boxes([[-1000,-1000,2000,2000]],inverse=True)
            np.testing.assert_allclose(mapped,[[100,200,500,600]])

    def test_gap_starts_a_new_censor_episode(self):
        counter=PassageCounter('SOFTWARE_FIXTURE',stable_samples=1,maximum_gap_s=2)
        counter.update(0.,0,{1:.1},{},{1},{1})
        events,_=counter.update(.2,1,{1:.9},{},{1},{1})
        self.assertEqual(len(events),1)
        counter.update(3.,15,{1:.1},{},{1},{1})
        self.assertTrue(any(x['reason']=='video_end' for x in counter.finish()))
        self.assertEqual(counter.summary()['IN'],1)


if __name__=='__main__':unittest.main()
