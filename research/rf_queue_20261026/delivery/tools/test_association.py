import json,unittest
from dataclasses import replace
from association import Passage,Read,Candidate,Resolver,apply_visual,score_ledger

class AssociationContract(unittest.TestCase):
    def setUp(self):self.p=Passage('opaque-event',10,20,'opaque-snapshot');self.registry={'tag-a':'a','tag-b':'b'}
    def resolve(self,reads,passages=None,now=25):
        resolver=Resolver(passages or [self.p],reads,self.registry);resolver.advance(now);return resolver
    def test_waits_until_decision_deadline(self):
        r=self.resolve([Read('r','tag-a',15,15)],now=24);self.assertEqual(r.outputs,{})
        r.advance(25);self.assertEqual(r.outputs['opaque-event']['identity_candidate'],'a')
    def test_same_code_duplicate_not_multiple_animals(self):
        r=self.resolve([Read('r1','tag-a',15,15),Read('r2','tag-a',16,16)])
        self.assertEqual(r.outputs['opaque-event']['candidate_code_count'],1)
        self.assertEqual(len(r.outputs['opaque-event']['timely_observation_ids']),2)
    def test_two_codes_stay_ambiguous(self):
        r=self.resolve([Read('r1','tag-a',15,15),Read('r2','tag-b',16,16)])
        self.assertIsNone(r.outputs['opaque-event']['identity_candidate'])
        self.assertEqual(r.outputs['opaque-event']['rf_status'],'RF_MULTI_CODE')
    def test_shared_read_not_consumed_by_two_events(self):
        other=Passage('other',14,24,'other-snapshot')
        r=self.resolve([Read('r','tag-a',16,16)],[self.p,other],now=29)
        self.assertEqual(len(r.outputs),2);self.assertTrue(all(x['identity_candidate'] is None for x in r.outputs.values()))
    def test_late_observation_never_used_as_timely(self):
        r=self.resolve([Read('r','tag-a',15,30)])
        self.assertIsNone(r.outputs['opaque-event']['identity_candidate']);self.assertEqual(r.outputs['opaque-event']['late_observation_ids'],[])
        r.advance(30);self.assertEqual(r.outputs['opaque-event']['late_observation_ids'],['r']);self.assertIsNone(r.outputs['opaque-event']['identity_candidate'])
    def test_return_passages_can_read_same_code_again(self):
        other=Passage('return',40,50,'other','B->A')
        r=self.resolve([Read('r1','tag-a',15,15),Read('r2','tag-a',45,45)],[self.p,other],55)
        self.assertEqual([x['identity_candidate'] for x in r.outputs.values()],['a','a'])
    def test_wrong_reader_or_invalid_clock_not_usable(self):
        r=self.resolve([Read('wrong-lane','tag-a',15,15,'lane2'),Read('clock','tag-a',15,14),Read('invalid','tag-a',15,15,valid=False)])
        self.assertIsNone(r.outputs['opaque-event']['identity_candidate'])
    def test_time_guard_inclusive(self):
        r=self.resolve([Read('r','tag-a',9,9)]);self.assertEqual(r.outputs['opaque-event']['identity_candidate'],'a')
        r=self.resolve([Read('r','tag-a',8,8)]);self.assertIsNone(r.outputs['opaque-event']['identity_candidate'])
    def test_unknown_code_does_not_become_identity(self):
        r=self.resolve([Read('r','not-registered',15,15)]);self.assertEqual(r.outputs['opaque-event']['rf_status'],'RF_UNREGISTERED_CODE')
    def test_unique_wrong_code_is_an_exposed_failure(self):
        r=self.resolve([Read('r','tag-b',15,15)]);out=list(r.outputs.values())
        self.assertEqual(score_ledger([{'event_id':'opaque-event','expected_identity':'a'}],out)['W'],1)
    def test_visual_candidate_uses_score_not_truth(self):
        base=self.resolve([]).outputs['opaque-event'];cache={'opaque-snapshot':Candidate('b',.9,.8,'fixed-model')}
        out=apply_visual(base,cache);self.assertEqual(out['identity_candidate'],'b')
        self.assertEqual(score_ledger([{'event_id':'opaque-event','expected_identity':'a'}],[out])['W'],1)
        self.assertEqual(score_ledger([{'event_id':'opaque-event','expected_identity':'b'}],[out])['C'],1)
    def test_visual_reject_and_missing_image_are_unresolved(self):
        base=self.resolve([]).outputs['opaque-event']
        self.assertIsNone(apply_visual(base,{'opaque-snapshot':Candidate('a',.7,.8,'model')})['identity_candidate'])
        self.assertEqual(apply_visual({**base,'snapshot_id':None},{})['reason'],'SNAPSHOT_MISSING')
    def test_no_duplicate_terminal_event_or_reference(self):
        r=self.resolve([]);self.assertEqual(r.advance(25),[])
        with self.assertRaises(ValueError):score_ledger([{'event_id':'x','expected_identity':'a'}]*2,[])
    def test_complete_accounting_and_extra_events(self):
        truth=[{'event_id':str(i),'expected_identity':'a'} for i in range(4)]
        out=[{'event_id':'0','identity_candidate':'a'},{'event_id':'1','identity_candidate':'b'},{'event_id':'2','identity_candidate':None},{'event_id':'extra','identity_candidate':'a'}]
        r=score_ledger(truth,out);self.assertEqual((r['C'],r['W'],r['U'],r['M'],r['extra_outputs']),(1,1,1,1,1))
    def test_batch_and_incremental_time_agree_on_decisions(self):
        reads=[Read('r','tag-a',15,30)];a=self.resolve(reads,now=40)
        b=Resolver([self.p],reads,self.registry)
        for t in range(41):b.advance(t)
        self.assertEqual(a.outputs,b.outputs)

if __name__=='__main__':unittest.main(verbosity=2)
