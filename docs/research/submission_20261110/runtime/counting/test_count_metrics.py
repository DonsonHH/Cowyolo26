"""Generated fixtures only; they do not supply human references for real videos."""
from copy import deepcopy
import unittest

from .count_metrics import aggregate_totals, score_totals


class CountTotalTests(unittest.TestCase):
    def setUp(self):
        config={'axis':'y','perpendicular_roi':[0,1],'in_direction':'B->A',
                'scope_start_frame0':0,'end_frame0_exclusive':21,
                'counter':{'lower':.4,'upper':.6}}
        self.summary={'status':'COMPLETED_UNSCORED','video_id':'fixture-video','run_id':'fixture-run',
                      'session_id':'fixture-session','video_sha256':'a'*64,'config':config,
                      'counts':{'IN':1,'OUT':0,'NET':1}}
        self.reference={'reference_type':'REVIEWED_VIDEO_DIRECTIONAL_TOTALS','review_status':'reviewed',
                        'video_id':'fixture-video','source_video_sha256':'a'*64,
                        'reviewed_interval':{'start_frame0':0,'end_frame0':20},
                        'review_gate':{'axis':'y','perpendicular_roi':[0,1],'lower':.4,'upper':.6},
                        'directional_totals':{'A->B':None,'B->A':2},
                        'review':{'reviewer':'SOFTWARE_FIXTURE','statement':'synthetic expected total',
                                  'evidence':'generated test case, not real annotations','view':'source_only'}}
        self.pred=[{'video_id':'fixture-video','run_id':'fixture-run','session_id':'fixture-session',
                    'event_id':'fixture-1','frame0':10,'direction':'B->A','kind':'IN'}]

    def test_counts_only_and_unknown_direction_stays_unknown(self):
        row=score_totals(self.summary,self.pred,self.reference)
        self.assertEqual(row['absolute_error_over_reviewed_directions'],1)
        self.assertEqual(row['unreviewed_directions'],['A->B'])
        self.assertIsNone(row['event_f1'])
        self.assertFalse(row['count_agreement_proves_no_misses_or_duplicates'])

    def test_reference_not_bound_to_run_session(self):
        other=deepcopy(self.summary);other['session_id']='repeat'
        pred=deepcopy(self.pred);pred[0]['session_id']='repeat'
        self.assertEqual(score_totals(other,pred,self.reference)['absolute_error_over_reviewed_directions'],1)

    def test_missing_review_cannot_score(self):
        for field in ('reviewer','statement','evidence'):
            ref=deepcopy(self.reference);ref['review'][field]=''
            with self.assertRaises(ValueError):score_totals(self.summary,self.pred,ref)

    def test_reference_scope_must_match(self):
        for field in ('video_id','source_video_sha256'):
            ref=deepcopy(self.reference);ref[field]='wrong'
            with self.assertRaises(ValueError):score_totals(self.summary,self.pred,ref)
        ref=deepcopy(self.reference);ref['reviewed_interval']['end_frame0']=19
        with self.assertRaises(ValueError):score_totals(self.summary,self.pred,ref)
        ref=deepcopy(self.reference);ref['review_gate']['upper']=.8
        with self.assertRaises(ValueError):score_totals(self.summary,self.pred,ref)

    def test_invalid_total_is_not_a_count(self):
        for value in (True,-1,1.5,'2'):
            ref=deepcopy(self.reference);ref['directional_totals']['B->A']=value
            with self.assertRaises(ValueError):score_totals(self.summary,self.pred,ref)

    def test_duplicate_or_wrong_scope_predictions_rejected(self):
        with self.assertRaises(ValueError):score_totals(self.summary,self.pred*2,self.reference)
        for key in ('run_id','session_id','video_id'):
            pred=deepcopy(self.pred);pred[0][key]='different'
            with self.assertRaises(ValueError):score_totals(self.summary,pred,self.reference)

    def test_out_of_window_and_wrong_kind_rejected(self):
        for key,value in (('frame0',22),('frame0',True),('kind','OUT'),('direction','invalid')):
            pred=deepcopy(self.pred);pred[0][key]=value
            with self.assertRaises(ValueError):score_totals(self.summary,pred,self.reference)

    def test_summary_must_match_ledger(self):
        s=deepcopy(self.summary);s['counts']={'IN':2,'OUT':0,'NET':2}
        with self.assertRaises(ValueError):score_totals(s,self.pred,self.reference)

    def test_empty_video_zero_reference_is_count_agreement_not_f1(self):
        s=deepcopy(self.summary);s['counts']={'IN':0,'OUT':0,'NET':0}
        ref=deepcopy(self.reference);ref['directional_totals']['B->A']=0
        row=score_totals(s,[],ref)
        self.assertTrue(row['all_reviewed_totals_agree']);self.assertIsNone(row['event_f1'])

    def test_aggregate_does_not_count_repeats_as_new_videos(self):
        row=score_totals(self.summary,self.pred,self.reference)
        other=deepcopy(row);other['run_id']='another-run'
        with self.assertRaises(ValueError):aggregate_totals([row,other])
        other['source_video_sha256']='b'*64
        result=aggregate_totals([row,other])
        self.assertEqual(result['video_units'],2)
        self.assertEqual(result['mean_absolute_error_over_reviewed_directions_per_video'],1.)
        self.assertFalse(result['source_session_independence_verified'])


if __name__=='__main__':unittest.main()
