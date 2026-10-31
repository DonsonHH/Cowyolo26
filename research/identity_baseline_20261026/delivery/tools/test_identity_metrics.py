import unittest
from identity_metrics import calibrate_threshold,summarise,cluster_intervals

class IdentityMetricsContract(unittest.TestCase):
    def test_unknown_calibration_false_accept_target(self):
        r=calibrate_threshold([.9,.7,.8,.6],['a','b','a','a'],['a','b','x','y'],[True,True,False,False],0)
        self.assertGreater(r['threshold'],.8);self.assertEqual(r['calibration_unknown_false_accepts'],0)
    def test_reject_all_is_a_valid_solution(self):
        r=calibrate_threshold([.2,.95],['b','a'],['a','x'],[True,False],0)
        self.assertGreater(r['threshold'],.95);self.assertEqual(r['calibration_known_correct_accepted'],0)
    def test_calibration_requires_unknown(self):
        with self.assertRaises(ValueError):calibrate_threshold([.9],['a'],['a'],[True])
    def test_known_wrong_and_unknown_false_accept_are_separate(self):
        rows=[{'identity':'a','predicted_id':'a','is_known':True,'accepted':True},
              {'identity':'b','predicted_id':'a','is_known':True,'accepted':True},
              {'identity':'c','predicted_id':'a','is_known':True,'accepted':False},
              {'identity':'x','predicted_id':'a','is_known':False,'accepted':True}]
        r=summarise(rows);self.assertEqual((r['known_correct_accepted_C'],r['known_wrong_accepted_W'],r['known_rejected_U']),(1,1,1))
        self.assertEqual(r['unknown_false_accepts'],1);self.assertAlmostEqual(r['all_accepted_wrong_fraction'],2/3)
    def test_empty_acceptance_is_na(self):
        r=summarise([{'identity':'a','predicted_id':'a','is_known':True,'accepted':False}])
        self.assertIsNone(r['all_accepted_wrong_fraction']);self.assertIsNone(r['unknown_false_acceptance_rate'])
    def test_bootstrap_resamples_identities(self):
        r=cluster_intervals([{'is_known':True,'closed_top1_accuracy':.5,'correct_accepted_rate':.2},
                             {'is_known':False,'false_accept_rate':.1}],draws=10)
        self.assertEqual(r['closed_top1_accuracy']['identity_clusters'],1)
        self.assertEqual(r['closed_top1_accuracy']['percentile_95_interval'],[.5,.5])
    def test_threshold_does_not_accept_nearly_equal_but_lower_score(self):
        r=calibrate_threshold([.9000001,.9],['a','a'],['a','x'],[True,False],0)
        self.assertGreater(r['threshold'],.9);self.assertLessEqual(r['threshold'],.9000001)

if __name__=='__main__':unittest.main(verbosity=2)
