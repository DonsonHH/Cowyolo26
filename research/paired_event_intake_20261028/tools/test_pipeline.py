from pathlib import Path
import argparse,copy,csv,hashlib,json,tempfile,unittest
from intake_pipeline import ROOT,PROJECT,load,save,sha,catalog_check,stage_annotation,score_packet,metric_function,ledger,direction_metrics
from inspect_annotation import GATE
CAT=ROOT/'results/frozen_prediction_catalog_v2.json'
def draft(qa=True):
    return {'schema_version':'cattle-passages-v1','review_session_id':'SOFTWARE_TEST_ONLY',
      'source':{'sha256':'5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1','fps':25,'frames':14009,'gate':copy.deepcopy(GATE)},
      'annotation_status':'draft_pending_independent_review','reviewer':'SOFTWARE_FIXTURE_NOT_HUMAN',
      'blinding':'source_only_no_prior_predictions_declared','qa_only':qa,
      'reviewed_intervals':[{'start_frame':8912,'end_frame':10873}],
      'events':[{'event_id':'SOFTWARE_ONLY_A','source_frame':9001,'time_s':9001/25,'direction':'A->B','completion':'complete'}]}
def receipt(packet,folder,fixture=True):
    p=load(packet/'packet.json');log=folder/'SOFTWARE_TEST_REVIEW_LOG.md';log.write_text('Software test only. No human review or real reference exists.',encoding='utf-8')
    return {'schema_version':'cattle-reference-acceptance-v1','fixture_only':fixture,'packet_sha256':sha(packet/'packet.json'),
       'annotation_sha256':p['annotation_sha256'],'source_sha256':p['source_sha256'],
       'human_provenance_review_complete':True,'native_source_review_complete':True,'ambiguities_resolved':True,'reviewer_independence_checked':True,
       'frame_scope_inclusive':[8912,10873],'checked_native_frames':[8912,9001,10873],
       'review_log_path':str(log),'review_log_sha256':sha(log)}
class PipelineTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'qa_fixtures').mkdir(exist_ok=True);self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'qa_fixtures')
        self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name);self.annotation=self.folder/'SOFTWARE_ANNOTATION.json'
        self.value=draft();save(self.annotation,self.value)
    def stage(self):return stage_annotation(self.annotation,CAT,self.folder/'packet')
    def setup_receipt(self):
        self.stage();p=self.folder/'packet';r=receipt(p,self.folder);path=self.folder/'SOFTWARE_RECEIPT.json';save(path,r);return p,r,path
    def test_01_catalog_retains_17_and_adds_all_three_pairs(self):
        c=catalog_check(CAT);old=load(PROJECT/'evaluation_intake_20261028/results/frozen_prediction_catalog.json')
        self.assertEqual(c['conditions'][:17],old['conditions']);self.assertEqual(len(c['conditions']),23);self.assertEqual(len(c['paired_comparisons']),3)
    def test_02_same_weights_orientation_do_not_merge_distinct_counter(self):
        c=load(CAT);r={x['condition_id']:x for x in c['conditions']};p=c['paired_comparisons'][0];a=r[p['baseline_condition_id']];b=r[p['candidate_condition_id']]
        self.assertEqual((a['checkpoint_sha256'],a['orientation']),(b['checkpoint_sha256'],b['orientation']))
        self.assertNotEqual(a['condition_id'],b['condition_id']);self.assertNotEqual(a['pipeline_contract_sha256'],b['pipeline_contract_sha256'])
    def test_03_stage_preserves_bytes_and_never_certifies(self):
        self.value['qa_only']=False;save(self.annotation,self.value);before=self.annotation.read_bytes();r=self.stage()
        self.assertEqual(r['status'],'DRAFT_READY_FOR_MANUAL_SOURCE_REVIEW');self.assertFalse(r['metrics_computed']);self.assertFalse(r['independent_reference_certified_by_software'])
        self.assertEqual(before,(self.folder/'packet/annotation_original.json').read_bytes());self.assertEqual(before,self.annotation.read_bytes())
    def test_04_known_QA_remains_blocked(self):
        r=self.stage();self.assertEqual(r['status'],'DRAFT_INTAKE_BLOCKED');self.assertFalse(r['source_count_accuracy_verified'])
    def test_05_one_frame_coverage_gap_blocks(self):
        self.value['reviewed_intervals']=[{'start_frame':8912,'end_frame':9999},{'start_frame':10001,'end_frame':10873}];save(self.annotation,self.value)
        self.assertIn('REQUESTED_SCOPE_NOT_FULLY_REVIEWED',self.stage()['inspection']['blocking_findings'])
    def test_06_same_frame_distinct_cows_preserved(self):
        self.value['events'].append({**self.value['events'][0],'event_id':'SOFTWARE_ONLY_B'});save(self.annotation,self.value)
        r=self.stage();self.assertEqual(len(r['inspection']['complete_scoped_events_for_later_matching']),2)
    def test_07_changed_catalog_artifact_digest_rejected(self):
        c=load(CAT);c['conditions'][0]['events_sha256']='0'*64;path=self.folder/'bad_catalog.json';save(path,c)
        with self.assertRaises(ValueError):catalog_check(path)
    def test_08_duplicate_condition_rejected(self):
        c=load(CAT);c['conditions'].append(c['conditions'][0]);path=self.folder/'bad_catalog.json';save(path,c)
        with self.assertRaises(ValueError):catalog_check(path)
    def test_09_stage_refuses_existing_output(self):
        self.stage()
        with self.assertRaises(FileExistsError):self.stage()
    def test_10_score_rejects_missing_review_record(self):
        self.stage()
        with self.assertRaises(FileNotFoundError):score_packet(self.folder/'packet',self.folder/'missing.json',self.folder/'scores')
    def test_11_fixture_can_never_be_production_reference(self):
        p,r,path=self.setup_receipt()
        with self.assertRaisesRegex(ValueError,'fixture'):score_packet(p,path,self.folder/'scores')
    def test_12_fixture_full_23_condition_path_is_explicitly_not_accuracy(self):
        p,r,path=self.setup_receipt();out=score_packet(p,path,self.folder/'scores',fixture_mode=True)
        self.assertTrue(out['fixture_only']);self.assertFalse(out['source_count_metrics_computed_against_manual_review_record'])
        self.assertFalse(out['source_is_independent_test_dataset']);self.assertEqual(len(out['conditions']),23);self.assertEqual(len(out['paired_changes']),3)
        with (self.folder/'scores/direction_scores.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),46);self.assertEqual({r['direction'] for r in rows},{'A->B','B->A'})
    def test_13_changed_reference_packet_rejected(self):
        p,r,path=self.setup_receipt();(p/'annotation_original.json').write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'changed'):score_packet(p,path,self.folder/'scores',fixture_mode=True)
    def test_14_unchecked_event_frame_rejected(self):
        p,r,path=self.setup_receipt();r['checked_native_frames']=[8912,10873];save(path,r)
        with self.assertRaisesRegex(ValueError,'frames'):score_packet(p,path,self.folder/'scores',fixture_mode=True)
    def test_15_changed_review_log_rejected(self):
        p,r,path=self.setup_receipt();Path(r['review_log_path']).write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'log'):score_packet(p,path,self.folder/'scores',fixture_mode=True)
    def test_16_incomplete_manual_review_rejected(self):
        p,r,path=self.setup_receipt();r['native_source_review_complete']=False;save(path,r)
        with self.assertRaisesRegex(ValueError,'Incomplete'):score_packet(p,path,self.folder/'scores',fixture_mode=True)
    def test_17_ambiguous_time_candidates_are_visible(self):
        f=metric_function();ref=[{'event_id':'a','source_frame':9000,'time_s':360.,'direction':'A->B'}]
        pred=[{'source_frame':9000,'time_s':360.,'direction':'A->B'},{'source_frame':9001,'time_s':360.04,'direction':'A->B'}]
        m=f(ref,pred);rows=ledger(ref,pred,m);self.assertEqual((m['TP'],m['FP'],m['FN']),(1,1,0));self.assertTrue(rows[0]['ambiguous_temporal_candidates'])
    def test_18_wrong_direction_is_not_hidden_by_pairing(self):
        f=metric_function();m=f([{'time_s':1.,'direction':'A->B'}],[{'time_s':1.,'direction':'B->A'}])
        self.assertEqual((m['TP'],m['FP'],m['FN'],m['wrong_direction_matches']),(0,1,1,1))
    def test_19_simultaneous_opposite_directions_keep_original_tie_rule(self):
        f=metric_function();ref=[{'event_id':str(i),'source_frame':9000,'time_s':360.,'direction':d} for i,d in enumerate(['A->B','B->A'])]
        pred=[{'source_frame':9000,'time_s':360.,'direction':d} for d in ['B->A','A->B']]
        m=f(ref,pred);self.assertEqual(m['temporally_matched'],2);self.assertEqual(m['wrong_direction_matches'],2)
        self.assertTrue(all(r['ambiguous_temporal_candidates'] for r in ledger(ref,pred,m)))
    def test_20_exact_two_second_boundary_and_outside(self):
        f=metric_function();a=[{'time_s':1.,'direction':'A->B'}]
        self.assertEqual(f(a,[{'time_s':3.,'direction':'A->B'}])['TP'],1)
        self.assertEqual(f(a,[{'time_s':3.04,'direction':'A->B'}])['TP'],0)
    def test_21_directional_error_is_FP_in_predicted_and_FN_in_true_direction(self):
        f=metric_function();ref=[{'time_s':1.,'direction':'A->B'}];pred=[{'time_s':1.,'direction':'B->A'}]
        m=f(ref,pred);d=direction_metrics(ref,pred,m)
        self.assertEqual((d['A->B']['TP'],d['A->B']['FP'],d['A->B']['FN']),(0,0,1))
        self.assertEqual((d['B->A']['TP'],d['B->A']['FP'],d['B->A']['FN']),(0,1,0))
        self.assertEqual(sum(x['FP'] for x in d.values()),m['FP']);self.assertEqual(sum(x['FN'] for x in d.values()),m['FN'])
    def test_22_empty_direction_metrics_are_NA_not_perfect(self):
        d=direction_metrics([],[],metric_function()([],[]))
        self.assertTrue(all(r['f1'] is None and r['precision'] is None and r['recall'] is None for r in d.values()))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results/pipeline_test_results.json');args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PipelineTests);r=unittest.TextTestRunner(verbosity=2).run(suite)
    out={'status':'PASS' if r.wasSuccessful() else 'FAIL','tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),
         'all_reference_receipts_and_reviews_are_software_fixtures':True,'real_independent_reference_received':False}
    save(args.output,out);print(json.dumps(out));raise SystemExit(0 if r.wasSuccessful() else 1)
