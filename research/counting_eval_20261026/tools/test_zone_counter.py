import unittest
from zone_counter import ZoneCounter

class CounterContractTests(unittest.TestCase):
    def simulate(self, seq):
        c=ZoneCounter();out=[]
        for t,pos in seq:out.extend(c.update(t,pos))
        return out
    def test_forward_and_return_are_distinct_events(self):
        values=[.2]*3+[.5]*2+[.8]*3+[.5]*2+[.2]*3
        events=self.simulate([(i*.1,{1:x}) for i,x in enumerate(values)])
        self.assertEqual([x['direction'] for x in events],['A->B','B->A'])
    def test_reverse_first_is_real_reverse_contract(self):
        events=self.simulate([(i*.1,{1:x}) for i,x in enumerate([.8]*3+[.5]+[.2]*3)])
        self.assertEqual([x['direction'] for x in events],['B->A'])
    def test_middle_initialization_is_not_complete_passage(self):
        self.assertEqual(self.simulate([(i*.1,{1:x}) for i,x in enumerate([.5,.5,.8,.8,.8])]),[])
    def test_approach_and_retreat_do_not_count(self):
        self.assertEqual(self.simulate([(i*.1,{1:x}) for i,x in enumerate([.2]*3+[.5]*2+[.2]*3)]),[])
    def test_jitter_never_stabilizes_destination(self):
        self.assertEqual(self.simulate([(i*.1,{1:x}) for i,x in enumerate([.2]*3+[.61,.59,.61,.59,.61,.59])]),[])
    def test_long_gap_censors_old_origin(self):
        self.assertEqual(self.simulate([(0,{1:.2}),(.1,{1:.2}),(.2,{1:.2}),(4,{1:.8}),(4.1,{1:.8}),(4.2,{1:.8})]),[])
    def test_new_id_does_not_inherit_old_origin(self):
        self.assertEqual(self.simulate([(i*.1,{1:.2} if i<3 else {2:.8}) for i in range(6)]),[])
    def test_missing_frame_breaks_stability(self):
        self.assertEqual(self.simulate([(0,{1:.2}),(.1,{1:.2}),(.2,{}),(.3,{1:.2}),(.4,{1:.8}),(.5,{1:.8}),(.6,{1:.8})]),[])
    def test_separate_animals_do_not_share_count(self):
        c=ZoneCounter();events=[]
        for i in range(3):events+=c.update(i*.1,{1:.2,2:.8})
        for i in range(3,6):events+=c.update(i*.1,{1:.8,2:.2})
        self.assertCountEqual([e['direction'] for e in events],['A->B','B->A'])
    def test_backward_time_rejected(self):
        c=ZoneCounter();c.update(2,{})
        with self.assertRaises(ValueError):c.update(1,{})

if __name__=='__main__':unittest.main(verbosity=2)
