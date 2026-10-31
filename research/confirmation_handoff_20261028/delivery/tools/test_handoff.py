"""Behavioral contract. --baseline demonstrates the observed lost-entry pattern."""
from pathlib import Path
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(ROOT/'input'))
from zone_counter import ZoneCounter
BASELINE='--baseline' in sys.argv
if BASELINE:sys.argv.remove('--baseline')
else:
    from confirmation_counter import ConfirmationHandoffCounter

class Adapter:
    def __init__(self):self.counter=ZoneCounter() if BASELINE else ConfirmationHandoffCounter()
    def step(self,n,confirmed=None,tentative=None,ids=None):
        confirmed=confirmed or {};tentative=tentative or {}
        if BASELINE:return self.counter.update(n*.2,confirmed)
        return self.counter.update(n*.2,confirmed,tentative,set(confirmed) if ids is None else ids)

class HandoffBehavior(unittest.TestCase):
    def sequence(self,steps):
        c=Adapter();events=[]
        for n,a,b in steps:events+=c.step(n,a,b)
        return c,events
    def test_01_observed_two_A_after_confirmation_retains_initial_A(self):
        c,e=self.sequence([(0,{}, {9:.2}),(1,{9:.25},{}),(2,{9:.3},{}),(3,{9:.5},{}),
                           (4,{9:.7},{}),(5,{9:.75},{}),(6,{9:.8},{})])
        self.assertEqual([(x['track_id'],x['direction']) for x in e],[(9,'A->B')])
        self.assertAlmostEqual(e[0]['time_s'],1.2)
    def test_02_confirmed_only_normal_pass_counts_once(self):
        c,e=self.sequence([(i,{1:p},{}) for i,p in enumerate([.2,.2,.2,.5,.8,.8,.8,.8,.8])])
        self.assertEqual(len(e),1)
    def test_03_unconfirmed_never_publishes(self):
        c,e=self.sequence([(i,{}, {2:p}) for i,p in enumerate([.2,.2,.2,.5,.8,.8,.8])])
        self.assertEqual(e,[])
    def test_04_failed_confirmation_drops_prefix(self):
        c,e=self.sequence([(0,{}, {3:.2}),(1,{},{}),(2,{3:.2},{}),(3,{3:.2},{}),
                           (4,{3:.5},{}),(5,{3:.8},{}),(6,{3:.8},{}),(7,{3:.8},{})])
        self.assertEqual(e,[])
    def test_05_reverse_direction_is_symmetric(self):
        c,e=self.sequence([(0,{}, {4:.8}),(1,{4:.8},{}),(2,{4:.8},{}),(3,{4:.5},{}),
                           (4,{4:.2},{}),(5,{4:.2},{}),(6,{4:.2},{})])
        self.assertEqual([x['direction'] for x in e],['B->A'])
    def test_06_first_seen_in_B_is_censored(self):
        c,e=self.sequence([(i,{5:.8},{}) for i in range(7)])
        self.assertEqual(e,[])
    def test_07_long_gap_clears_previous_origin(self):
        c,e=self.sequence([(0,{6:.2},{}),(1,{6:.2},{}),(2,{6:.2},{}),
                           (15,{6:.8},{}),(16,{6:.8},{}),(17,{6:.8},{})])
        self.assertEqual(e,[])
    def test_08_missing_tick_breaks_stability(self):
        c,e=self.sequence([(0,{}, {7:.2}),(1,{7:.2},{}),(2,{},{}),(3,{7:.2},{}),(4,{7:.2},{}),
                           (5,{7:.5},{}),(6,{7:.8},{}),(7,{7:.8},{}),(8,{7:.8},{})])
        self.assertEqual(e,[])
    def test_09_two_A_without_prefix_stays_insufficient(self):
        c,e=self.sequence([(0,{8:.2},{}),(1,{8:.2},{}),(2,{8:.5},{}),
                           (3,{8:.8},{}),(4,{8:.8},{}),(5,{8:.8},{})])
        self.assertEqual(e,[])
    def test_10_multiple_unconfirmed_samples_do_not_accumulate(self):
        c,e=self.sequence([(0,{}, {10:.2}),(1,{}, {10:.2}),(2,{}, {10:.2}),
                           (3,{10:.8},{}),(4,{10:.8},{}),(5,{10:.8},{})])
        self.assertEqual(e,[])
    def test_11_outside_ROI_confirmation_breaks_run(self):
        c=Adapter();e=c.step(0,{}, {11:.2});e+=c.step(1,{}, {},{11})
        for n,p in enumerate([.2,.2,.5,.8,.8,.8],2):e+=c.step(n,{11:p})
        self.assertEqual(e,[])
    def test_12_same_tick_event_order_and_no_repeat(self):
        c,e=self.sequence([(i,{22:p,21:p},{}) for i,p in enumerate([.2,.2,.2,.5,.8,.8,.8,.8])])
        self.assertEqual([x['track_id'] for x in e],[22,21])
    @unittest.skipIf(BASELINE,'new adapter API validation')
    def test_13_duplicate_time_is_rejected(self):
        c=Adapter();c.step(0,{1:.2})
        with self.assertRaises(ValueError):c.step(0,{1:.2})
    @unittest.skipIf(BASELINE,'new adapter API validation')
    def test_14_overlapping_confirmation_states_are_rejected(self):
        c=Adapter()
        with self.assertRaises(ValueError):c.step(0,{1:.2},{1:.2})

if __name__=='__main__':unittest.main(verbosity=2)
