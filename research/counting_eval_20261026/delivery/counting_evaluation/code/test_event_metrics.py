import unittest
from event_metrics import evaluate_events
def event(t,d='A->B'):return {'time_s':t,'direction':d}
class MatchingTests(unittest.TestCase):
 def test_direction_not_used_to_hide_wrong_direction(self):
  r=evaluate_events([event(1)],[event(1,'B->A')]);self.assertEqual((r['temporally_matched'],r['TP'],r['FP'],r['FN'],r['wrong_direction_matches']),(1,0,1,1,1))
 def test_duplicate_prediction_is_false_positive(self):
  r=evaluate_events([event(1)],[event(1),event(1.1)]);self.assertEqual((r['TP'],r['FP'],r['FN']),(1,1,0))
 def test_maximum_cardinality_before_nearest(self):
  r=evaluate_events([event(0),event(2)],[event(1),event(3)],1.1);self.assertEqual(r['TP'],2)
 def test_no_prediction_is_missing_not_zero_risk(self):
  r=evaluate_events([event(1)],[]);self.assertEqual(r['FN'],1);self.assertIsNone(r['precision']);self.assertEqual(r['recall'],0)
 def test_empty_reference_and_predictions_na(self):
  r=evaluate_events([],[]);self.assertIsNone(r['f1']);self.assertIsNone(r['recall'])
 def test_far_event_is_fp_and_fn(self):
  r=evaluate_events([event(1)],[event(9)]);self.assertEqual((r['TP'],r['FP'],r['FN']),(0,1,1))
if __name__=='__main__':unittest.main(verbosity=2)
