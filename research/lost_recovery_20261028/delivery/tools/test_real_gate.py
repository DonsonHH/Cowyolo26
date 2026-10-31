"""Actual tracker sequences isolate lost eligibility after pure-IoU secondstage."""
from pathlib import Path
import argparse,io,json,sys,unittest
import numpy as np
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import STrack
from ultralytics.utils import IterableSimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'input'))
from secondstage_tracker import SecondStageIoUTracker
parser=argparse.ArgumentParser();parser.add_argument('--candidate',action='store_true');args=parser.parse_args();sys.argv=[sys.argv[0]]
if args.candidate:
    from lost_tracker import LostLowScoreTracker,verify_method_scope
    TRACKER=LostLowScoreTracker
else:TRACKER=SecondStageIoUTracker
CONFIG={'tracker_type':'bytetrack','track_high_thresh':.25,'track_low_thresh':.1,'new_track_thresh':.25,'track_buffer':30,'match_thresh':.8,'fuse_score':True}
def boxes(items):return Boxes(np.asarray(items,np.float32).reshape(-1,6),(200,200))
def det(score=.9,box=(20.,20.,60.,60.)):return [*box,score,0]
class ActualTrackerTests(unittest.TestCase):
    def tracker(self):return TRACKER(IterableSimpleNamespace(**CONFIG))
    def test_01_lost_identity_recovers_on_overlapping_low(self):
        t=self.tracker();initial=t.update(boxes([det()]));t.update(boxes([]));recovered=t.update(boxes([det(.22)]))
        self.assertEqual(len(recovered),1);self.assertEqual(recovered[0,4],initial[0,4])
    def test_02_two_lost_identities_recover_without_new_ID(self):
        t=self.tracker();initial=t.update(boxes([det(),det(.9,(100.,100.,140.,140.))]));t.update(boxes([]))
        recovered=t.update(boxes([det(.22),det(.23,(100.,100.,140.,140.))]))
        self.assertEqual(len(recovered),2);self.assertEqual(set(recovered[:,4]),set(initial[:,4]))
    def test_03_active_low_continuity_still_works(self):
        t=self.tracker();a=t.update(boxes([det()]));b=t.update(boxes([det(.22)]));self.assertEqual(a[0,4],b[0,4])
    def test_04_low_without_confirmed_origin_cannot_create_identity(self):
        t=self.tracker();self.assertEqual(len(t.update(boxes([det(.22)]))),0);self.assertEqual(len(t.update(boxes([det(.22)]))),0)
    def test_05_disjoint_low_cannot_recover_lost(self):
        t=self.tracker();t.update(boxes([det()]));t.update(boxes([]));self.assertEqual(len(t.update(boxes([det(.22,(100.,100.,140.,140.))]))),0)
    def test_06_low_IoU_below_half_cannot_recover_lost(self):
        t=self.tracker();t.update(boxes([det()]));t.update(boxes([]));self.assertEqual(len(t.update(boxes([det(.22,(40.,20.,80.,60.))]))),0)
    def test_07_expired_ID_cannot_be_revived_by_low(self):
        t=self.tracker();t.update(boxes([det()]))
        for _ in range(40):t.update(boxes([]))
        self.assertEqual(len(t.update(boxes([det(.22)]))),0)
    def test_08_firststage_score_fusion_still_enabled(self):
        t=self.tracker();a=STrack(np.array([40.,40.,40.,40.,0.],np.float32),.9,0);b=STrack(np.array([53.333333,40.,40.,40.,0.],np.float32),.3,0)
        self.assertTrue(t.args.fuse_score);self.assertGreater(float(t.get_dists([a],[b])[0,0]),.8)
    def test_09_high_firststage_precedes_samebox_low(self):
        t=self.tracker();initial=t.update(boxes([det()]));out=t.update(boxes([det(.8),det(.22)]))
        self.assertEqual(len(out),1);self.assertEqual(out[0,4],initial[0,4]);self.assertAlmostEqual(out[0,5],.8,places=6)
    def test_10_one_low_observation_cannot_recover_two_lost_IDs(self):
        t=self.tracker();t.update(boxes([det(),det(.9,(100.,100.,140.,140.))]));t.update(boxes([]));out=t.update(boxes([det(.22)]))
        self.assertLessEqual(len(out),1)
    def test_11_removed_tentative_ID_cannot_use_low(self):
        t=self.tracker();t.update(boxes([]));t.update(boxes([det()]))
        t.update(boxes([]));self.assertEqual(len(t.update(boxes([det(.22)]))),0)
    @unittest.skipUnless(args.candidate,'candidate scope assertion')
    def test_12_only_lost_eligibility_expression_changes(self):
        self.assertEqual(verify_method_scope()['eligibility_expression_changes'],1)
if __name__=='__main__':
    result_text=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(ActualTrackerTests)
    r=unittest.TextTestRunner(stream=result_text,verbosity=2).run(suite)
    expected={case.id().split('.')[-1] for case,detail in r.failures}
    red=(not args.candidate and len(r.failures)==2 and not r.errors and expected=={
        'test_01_lost_identity_recovers_on_overlapping_low','test_02_two_lost_identities_recover_without_new_ID'})
    name='candidate_green' if args.candidate else 'baseline_red'
    out={'mode':name,'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),
        'expected_two_failures_reproduced':bool(red),'gate_passed':r.wasSuccessful() if args.candidate else red,
        'synthetic_tracker_sequences_not_cattle_accuracy':True}
    log=ROOT/f'results/{name}_tests.log';path=ROOT/f'results/{name}_tests.json';assert not log.exists() and not path.exists()
    log.write_text(result_text.getvalue(),encoding='utf-8');path.write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(result_text.getvalue());print(json.dumps(out),flush=True);raise SystemExit(0 if out['gate_passed'] else 1)
