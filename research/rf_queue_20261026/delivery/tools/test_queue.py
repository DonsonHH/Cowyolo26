import unittest
from queue_simulator import simulate

class QueueContract(unittest.TestCase):
    def arrivals(self,n=20,spacing=50):return [{'job_id':str(i),'ready_tick':5+i*spacing,'snapshot_id':'opaque'} for i in range(n)]
    def test_nonpreemptible_long_job_disrupts_foreground(self):
        r=simulate(self.arrivals(),policy='nonpreemptive',service=20)
        self.assertGreater(r['foreground_deadline_misses'],0)
    def test_cooperative_slices_preserve_foreground_budget(self):
        r=simulate(self.arrivals(),policy='cooperative',service=20)
        self.assertEqual(r['foreground_deadline_misses'],0);self.assertEqual(r['jobs_on_time'],20)
    def test_whole_job_must_fit_idle_gap(self):
        r=simulate(self.arrivals(),policy='fits_next_gap',service=20)
        self.assertEqual(r['jobs_on_time'],0);self.assertEqual(r['foreground_deadline_misses'],0)
    def test_short_job_fits_gap_positive_control(self):
        r=simulate(self.arrivals(90,10),policy='fits_next_gap',service=5)
        self.assertEqual(r['jobs_on_time'],90);self.assertEqual(r['foreground_deadline_misses'],0)
    def test_burst_rejections_retained(self):
        arrivals=[{'job_id':str(i),'ready_tick':5,'snapshot_id':'opaque'} for i in range(10)]
        r=simulate(arrivals,policy='cooperative',service=20)
        self.assertGreater(r['background_status_counts'].get('REJECTED_CAPACITY',0),0);self.assertEqual(len(r['jobs']),10)
    def test_overload_does_not_get_free_end_drain(self):
        r=simulate(self.arrivals(90,10),policy='cooperative',service=60)
        self.assertLess(r['jobs_on_time'],90);self.assertTrue(all(j['finished_tick'] is None or j['finished_tick']<=1200 for j in r['jobs']))
    def test_resource_and_completion_conservation(self):
        r=simulate(self.arrivals(),policy='nonpreemptive',service=20)
        self.assertEqual(sum(r['resource_ticks'].values()),1200)
        self.assertEqual(sum(j['work_ticks'] for j in r['jobs']),r['resource_ticks'].get('background',0))
        self.assertEqual(sum(r['background_status_counts'].values()),len(r['jobs']))
    def test_disabled_does_not_run_identity(self):
        r=simulate(self.arrivals(),policy='disabled');self.assertEqual(r['resource_ticks'].get('background',0),0)
        self.assertEqual(r['background_status_counts']['DISABLED'],20)
    def test_deterministic_timeline(self):
        self.assertEqual(simulate(self.arrivals(),policy='cooperative'),simulate(self.arrivals(),policy='cooperative'))

if __name__=='__main__':unittest.main(verbosity=2)
