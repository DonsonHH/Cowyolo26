import copy,unittest
from validate_annotations import validate,SOURCE_SHA

class AnnotationContract(unittest.TestCase):
    def fixture(self):
        return {'schema_version':'cattle-passages-v1','annotation_status':'draft_pending_independent_review',
                'reviewer':'QA-fixture-not-human-truth','blinding':'prior_outputs_seen',
                'source':{'sha256':SOURCE_SHA,'fps':25,'frames':14009},
                'reviewed_intervals':[{'start_frame':0,'end_frame':50}],
                'events':[{'event_id':'first','source_frame':25,'time_s':1.,'direction':'A->B','completion':'complete'}]}
    def test_two_cows_can_complete_in_same_frame(self):
        x=self.fixture();x['events'].append({**x['events'][0],'event_id':'second'})
        r=validate(x);self.assertEqual(r['events'],2);self.assertEqual(r['coincident_event_groups_for_review'][0]['events'],2)
    def test_timing_must_map_to_source_frame(self):
        x=self.fixture();x['events'][0]['time_s']=4.
        with self.assertRaises(ValueError):validate(x)
    def test_wrong_source_rejected(self):
        x=self.fixture();x['source']['sha256']='wrong'
        with self.assertRaises(ValueError):validate(x)
    def test_duplicate_uuid_rejected(self):
        x=self.fixture();x['events'].append(copy.deepcopy(x['events'][0]))
        with self.assertRaises(ValueError):validate(x)
    def test_partial_coverage_does_not_become_full_video(self):
        r=validate(self.fixture());self.assertFalse(r['full_video_coverage_declared'])
    def test_event_in_unreviewed_gap_flagged(self):
        x=self.fixture();x['reviewed_intervals']=[{'start_frame':0,'end_frame':20},{'start_frame':30,'end_frame':50}]
        self.assertEqual(validate(x)['complete_events_outside_declared_coverage'],['first'])
    def test_censored_not_counted_as_complete(self):
        x=self.fixture();x['events'][0]['completion']='censored'
        self.assertEqual(validate(x)['event_status_counts'],{'censored':1})
    def test_declaration_does_not_auto_certify_truth(self):
        x=self.fixture();x['reviewed_intervals']=[{'start_frame':0,'end_frame':14008}]
        r=validate(x);self.assertTrue(r['full_video_coverage_declared']);self.assertTrue(r['frozen_reference_status'].startswith('PENDING'))
    def test_cannot_import_self_certified_status(self):
        x=self.fixture();x['annotation_status']='frozen'
        with self.assertRaises(ValueError):validate(x)
    def test_terminal_decode_issue_stays_flagged(self):
        x=self.fixture();x['events'][0].update(source_frame=14008,time_s=14008/25)
        self.assertEqual(validate(x)['complete_events_on_unreliable_source_frame'],['first'])

if __name__=='__main__':unittest.main(verbosity=2)
