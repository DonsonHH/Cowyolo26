"""Real tracker objects and update path, without model inference."""
from pathlib import Path
import argparse,json,sys,unittest
import numpy as np
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker,STrack
from ultralytics.utils import IterableSimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args();sys.argv=[sys.argv[0]]
if args.baseline:TRACKER=BYTETracker
else:
    from secondstage_tracker import SecondStageIoUTracker,verify_method_scope
    TRACKER=SecondStageIoUTracker
CONFIG={'tracker_type':'bytetrack','track_high_thresh':.25,'track_low_thresh':.1,'new_track_thresh':.25,'track_buffer':30,'match_thresh':.8,'fuse_score':True}
def boxes(items):return Boxes(np.asarray(items,np.float32).reshape(-1,6),(200,200))
def det(score=.9,box=(20.,20.,60.,60.)):return [*box,score,0]
class ActualTrackerTests(unittest.TestCase):
    def tracker(self):return TRACKER(IterableSimpleNamespace(**CONFIG))
    def test_01_ideal_low_detection_preserves_active_ID(self):
        t=self.tracker();first=t.update(boxes([det()]))
        second=t.update(boxes([det(.22)]))
        self.assertEqual(len(second),1);self.assertEqual(second[0,4],first[0,4])
    def test_02_lost_track_cannot_use_low_reactivation(self):
        t=self.tracker();t.update(boxes([det()]));t.update(boxes([]))
        self.assertEqual(len(t.update(boxes([det(.22)]))),0)
    def test_03_low_detection_does_not_create_new_identity(self):
        t=self.tracker();self.assertEqual(len(t.update(boxes([det(.22)]))),0)
        self.assertEqual(len(t.update(boxes([det(.22)]))),0)
    def test_04_disjoint_low_detection_does_not_match(self):
        t=self.tracker();t.update(boxes([det()]))
        self.assertEqual(len(t.update(boxes([det(.22,(100.,100.,140.,140.))]))),0)
    def test_05_first_stage_score_fusion_remains_enabled(self):
        t=self.tracker();self.assertTrue(t.args.fuse_score)
        a=STrack(np.array([40.,40.,40.,40.,0.],np.float32),.9,0)
        b=STrack(np.array([53.333333,40.,40.,40.,0.],np.float32),.3,0)
        self.assertGreater(float(t.get_dists([a],[b])[0,0]),.8)
    def test_06_normal_high_detection_keeps_identity(self):
        t=self.tracker();a=t.update(boxes([det()]));b=t.update(boxes([det(.8)]))
        self.assertEqual(len(b),1);self.assertEqual(a[0,4],b[0,4])
    def test_07_two_low_detections_keep_two_distinct_active_IDs(self):
        t=self.tracker();a=t.update(boxes([det(),det(.9,(100.,100.,140.,140.))]))
        b=t.update(boxes([det(.22),det(.23,(100.,100.,140.,140.))]))
        self.assertEqual(len(b),2);self.assertEqual(set(a[:,4]),set(b[:,4]))
    def test_08_IoU_below_half_is_still_rejected(self):
        t=self.tracker();t.update(boxes([det()]))
        self.assertEqual(len(t.update(boxes([det(.22,(40.,20.,80.,60.))]))),0)
    @unittest.skipIf(args.baseline,'candidate scope check')
    def test_09_only_secondstage_fusion_block_is_removed(self):
        self.assertEqual(verify_method_scope()['removed_score_fusion_blocks'],1)
if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ActualTrackerTests)
    import io
    output=io.StringIO();result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    name='baseline_red' if args.baseline else 'candidate_green'
    log=ROOT/f'results/{name}_tests.log';assert not log.exists();log.write_text(output.getvalue(),encoding='utf-8')
    expected_red=args.baseline and len(result.failures)==2 and not result.errors and {case.id().split('.')[-1] for case,detail in result.failures}=={
        'test_01_ideal_low_detection_preserves_active_ID','test_07_two_low_detections_keep_two_distinct_active_IDs'}
    r={'mode':name,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
       'skipped':len(result.skipped),'expected_two_baseline_failures_observed':expected_red,
       'gate_passed':bool(expected_red if args.baseline else result.wasSuccessful()),
       'fixtures_are_synthetic_tracker_sequences_not_cattle_accuracy':True}
    p=ROOT/f'results/{name}_tests.json';assert not p.exists();p.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print(output.getvalue());print(json.dumps(r),flush=True);raise SystemExit(0 if r['gate_passed'] else 1)
