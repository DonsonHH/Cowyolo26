"""Actual global geometry plus verified local score; no neural accuracy claim."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from .birth_refinement import BirthRefinement
from .budget_runner import merge_local
from .geometry import Transform
from . import test_scheduled_realtime as fixtures
from . import realtime

class BirthGeometryTests(unittest.TestCase):
    def config(self,preserve=True):
        cfg=fixtures.ScheduledRealtimeTests().config()
        cfg['birth_refinement']['preserve_global_geometry']=preserve
        return cfg
    def test_verified_score_retains_actual_global_geometry_without_mutating_inputs(self):
        birth=BirthRefinement(self.config(),100,100)
        seed=np.array([10,10,30,30,.12,0],np.float32)
        selected=np.array([12,13,28,27,.8,0],np.float32)
        old_seed,old_local=seed.copy(),selected.copy()
        fused=birth.fuse(seed,selected)
        np.testing.assert_array_equal(fused[:4],seed[:4])
        np.testing.assert_array_equal(fused[4:],selected[4:])
        np.testing.assert_array_equal(seed,old_seed);np.testing.assert_array_equal(selected,old_local)
    def test_legacy_default_and_invalid_switch_are_explicit(self):
        cfg=self.config(False);cfg['birth_refinement'].pop('preserve_global_geometry')
        birth=BirthRefinement(cfg,100,100)
        selected=np.array([12,13,28,27,.8,0],np.float32)
        np.testing.assert_array_equal(birth.fuse([10,10,30,30,.1,0],selected),selected)
        cfg['birth_refinement']['preserve_global_geometry']='true'
        with self.assertRaisesRegex(ValueError,'must be boolean'):BirthRefinement(cfg,100,100)
    def test_budget_merge_records_selected_and_used_measurements_separately(self):
        cfg=self.config();birth=BirthRefinement(cfg,100,100)
        base=np.array([[10,10,30,30,.12,0]],np.float32)
        selected=np.array([12,13,28,27,.8,0],np.float32)
        record={'kind':'birth','proposal':{'seed_index':0}}
        local=Transform.create(100,100,[0,0,50,50],0,32)
        with patch('counting.budget_runner.decode',return_value=selected[None]), \
             patch.object(birth,'select',return_value=selected):
            merged=merge_local(record,np.zeros((1,0,6)),base,0,local,SimpleNamespace(),birth,SimpleNamespace(),cfg)
        np.testing.assert_array_equal(merged[0,:4],base[0,:4])
        np.testing.assert_array_equal(record['accepted_detection'],selected)
        np.testing.assert_array_equal(record['fused_detection'],merged[0])
        self.assertEqual(record['fusion_mode'],'global_geometry_local_score')
    def test_realtime_uses_the_same_fusion_and_updates_once_per_global_image(self):
        cfg=self.config();selected=np.array([26,26,74,74,.8,0],np.float32)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'fixture';source.write_bytes(b'SOFTWARE_ONLY')
            with patch.object(realtime,'LatestCapture',fixtures.Capture), \
                 patch.object(realtime.BirthRefinement,'proposal',side_effect=lambda pts,*_:(
                     {'roi':[0,0,100,100],'seed_index':0} if pts==0 else None)), \
                 patch.object(realtime.BirthRefinement,'select',return_value=selected):
                result=realtime.run(source,cfg,root/'run',detector_factory=lambda _:fixtures.Detector())
            rows=[json.loads(x) for x in (root/'run/frames.jsonl').read_text().splitlines()]
            self.assertEqual([r['frame0'] for r in rows],[0,2,4])
            self.assertEqual((result['base_model_forwards'],result['birth_refinement_forwards']),(3,1))
            np.testing.assert_array_equal(rows[0]['detections'][0][:4],rows[0]['base_detections'][0][:4])
            np.testing.assert_array_equal(rows[0]['birth_refinement'][0]['accepted_detection'],selected)
            self.assertTrue(result['software_fixture_only'])
if __name__=='__main__':unittest.main()
