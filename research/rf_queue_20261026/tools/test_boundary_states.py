import unittest
from queue_simulator import simulate
from association import Candidate

class RemainingBoundaryStates(unittest.TestCase):
    def job(self,t=5):return [{'job_id':'opaque','ready_tick':t,'snapshot_id':'snapshot'}]
    def test_unfinished_work_at_session_end_stays_pending(self):
        r=simulate(self.job(1195),'cooperative',service=20)
        j=r['jobs'][0];self.assertEqual(j['status'],'PENDING_AT_HORIZON')
        self.assertEqual(j['work_ticks'],5);self.assertIsNone(j['finished_tick']);self.assertEqual(j['remaining'],15)
    def test_nonpreemptible_late_result_keeps_consumed_work(self):
        r=simulate(self.job(),'nonpreemptive',service=60,ttl=5)
        j=r['jobs'][0];self.assertEqual(j['status'],'COMPLETED_LATE')
        self.assertEqual(j['work_ticks'],60);self.assertEqual(j['finished_tick'],65)
    def test_cooperative_partial_work_can_expire(self):
        r=simulate(self.job(),'cooperative',service=60,ttl=5)
        j=r['jobs'][0];self.assertEqual(j['status'],'EXPIRED_PARTIAL')
        self.assertEqual(j['work_ticks'],5);self.assertEqual(j['finished_tick'],10)
    def test_completion_exactly_at_deadline_is_accepted(self):
        r=simulate(self.job(),'fits_next_gap',service=5,ttl=5)
        self.assertEqual(r['jobs'][0]['status'],'COMPLETED');self.assertEqual(r['jobs'][0]['finished_tick'],10)
    def test_nonfinite_visual_score_cannot_be_accepted(self):
        self.assertFalse(Candidate('a',float('nan'),.5,'model').accepted())
        self.assertFalse(Candidate('a',.9,float('nan'),'model').accepted())

if __name__=='__main__':unittest.main(verbosity=2)
