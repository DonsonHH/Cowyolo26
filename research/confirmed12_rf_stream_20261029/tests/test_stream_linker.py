from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'input'))
from association import Read
from stream_linker import OnlineLinker

class StreamAssociation(unittest.TestCase):
    def make(self):return OnlineLinker({'code-a':'SIM-A','code-b':'SIM-B'},wait_frames=2,orphan_gap_frames=5,horizon_frame0=100)
    def event(self,e='opaque-a',track=1,snapshot='photo-a',direction='A->B'):
        return {'event_id':e,'track_id':track,'direction':direction,'snapshot_id':snapshot}
    def test_unique_code_waits_for_cutoff(self):
        x=self.make();x.step(0,{1:.3},[],[]);x.step(2,{1:.7},[self.event()],[Read('r','code-a',1,1)])
        self.assertEqual(x.step(3,{},[],[]),[]);out=x.step(4,{},[],[])[0]
        self.assertEqual(out['identity_candidate'],'SIM-A');self.assertFalse(out['verified_identity'])
    def test_incomplete_neighbour_reservation_blocks_unique_code(self):
        x=self.make();x.step(0,{1:.3},[],[]);x.step(1,{1:.4,2:.3},[],[])
        x.step(2,{1:.7,2:.4},[self.event()],[Read('r','code-a',1,1)])
        out=x.step(4,{2:.5},[],[])[0]
        self.assertEqual(out['rf_status'],'RF_SHARED_WINDOW');self.assertIsNone(out['identity_candidate'])
        self.assertEqual(len(x.events),1)
    def test_future_neighbour_is_not_used_or_needed(self):
        x=self.make();x.step(0,{1:.3},[],[]);x.step(2,{1:.7},[self.event()],[Read('r','code-a',1,1)])
        self.assertEqual(x.step(4,{},[],[])[0]['identity_candidate'],'SIM-A')
        x.step(5,{2:.3},[],[]);self.assertEqual(x.outputs['opaque-a']['identity_candidate'],'SIM-A')
    def test_late_read_is_evidence_without_rebinding(self):
        x=self.make();x.step(0,{1:.3},[],[]);x.step(2,{1:.7},[self.event()],[])
        self.assertIsNone(x.step(4,{},[],[])[0]['identity_candidate'])
        x.step(6,{},[],[Read('late','code-a',1,6)])
        self.assertEqual(x.outputs['opaque-a']['late_observation_ids'],['late']);self.assertIsNone(x.outputs['opaque-a']['identity_candidate'])
    def test_same_code_retransmissions_do_not_make_more_events(self):
        x=self.make();x.step(0,{1:.3},[],[])
        r=Read('r1','code-a',1,1);x.step(2,{1:.7},[self.event()],[r,r,Read('r2','code-a',1,2)])
        out=x.step(4,{},[],[])[0]
        self.assertEqual(out['candidate_code_count'],1);self.assertEqual(out['timely_observation_ids'],['r1','r2']);self.assertEqual(len(x.outputs),1)
    def test_multi_code_stays_unresolved(self):
        x=self.make();x.step(0,{1:.3},[],[])
        x.step(2,{1:.7},[self.event()],[Read('a','code-a',1,1),Read('b','code-b',1,1)])
        self.assertEqual(x.step(4,{},[],[])[0]['rf_status'],'RF_MULTI_CODE')
    def test_unregistered_or_invalid_inputs_are_not_identities(self):
        for reads,status in [([Read('r','unregistered',1,1)],'RF_UNREGISTERED_CODE'),
                             ([Read('r','code-a',1,1,reader='lane2')],'RF_NO_TIMELY_READ'),
                             ([Read('r','code-a',2,1)],'RF_NO_TIMELY_READ'),
                             ([Read('r','code-a',1,1,valid=False)],'RF_NO_TIMELY_READ')]:
            x=self.make();x.step(0,{1:.3},[],[]);x.step(2,{1:.7},[self.event()],reads)
            self.assertEqual(x.step(4,{},[],[])[0]['rf_status'],status)
    def test_future_receipt_cannot_leak_into_runtime(self):
        with self.assertRaises(ValueError):self.make().step(0,{},[],[Read('r','code-a',0,1)])
    def test_duplicate_closing_event_is_idempotent(self):
        x=self.make();x.step(0,{1:.3},[],[]);x.step(2,{1:.7},[self.event(),self.event()],[])
        self.assertEqual(len(x.step(4,{},[],[])),1);self.assertEqual(x.step(4,{},[],[]),[])
    def test_same_code_can_return_with_new_opposite_passage(self):
        x=self.make();x.step(0,{1:.3},[],[]);x.step(2,{1:.7},[self.event()],[Read('r1','code-a',1,1)])
        x.step(4,{1:.8},[],[]);x.step(6,{1:.5},[],[])
        x.step(8,{1:.2},[self.event('return',snapshot='photo-b',direction='B->A')],[Read('r2','code-a',7,7)])
        out=x.step(10,{},[],[])[0];self.assertEqual(out['identity_candidate'],'SIM-A');self.assertEqual(out['direction'],'B->A')
    def test_missing_provisional_window_cannot_backdate_read_eligibility(self):
        x=self.make();x.step(2,{},[self.event()],[Read('r','code-a',1,1)])
        self.assertIsNone(x.step(4,{},[],[])[0]['identity_candidate'])
    def test_missing_snapshot_remains_explicit_in_resolved_event(self):
        x=self.make();x.step(0,{1:.3},[],[]);x.step(2,{1:.7},[self.event(snapshot=None)],[])
        self.assertIsNone(x.step(4,{},[],[])[0]['snapshot_id'])
    def test_conflicting_duplicate_and_truth_fields_are_rejected(self):
        x=self.make();x.step(0,{},[],[Read('r','code-a',0,0)])
        with self.assertRaises(ValueError):x.step(1,{},[],[Read('r','code-b',0,0)])
        with self.assertRaises(ValueError):self.make().step(1,{},[{**self.event(),'expected_identity':'leak'}],[])
    def test_sole_registered_wrong_code_is_visible_limitation(self):
        x=self.make();x.step(0,{1:.3},[],[]);x.step(2,{1:.7},[self.event()],[Read('r','code-b',1,1)])
        self.assertEqual(x.step(4,{},[],[])[0]['identity_candidate'],'SIM-B')

if __name__=='__main__':unittest.main(verbosity=2)
