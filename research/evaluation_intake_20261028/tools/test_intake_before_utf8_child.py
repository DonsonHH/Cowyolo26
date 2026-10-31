from pathlib import Path
import copy, hashlib, json, subprocess, sys, unittest
from inspect_annotation import inspect, GATE, KNOWN_QA
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def draft():
    return {'schema_version': 'cattle-passages-v1', 'review_session_id': 'structural-test-only',
            'source': {'sha256': '5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1',
                       'fps': 25, 'frames': 14009, 'gate': copy.deepcopy(GATE)},
            'annotation_status': 'draft_pending_independent_review', 'reviewer': 'structural-test-only',
            'blinding': 'source_only_no_prior_predictions_declared',
            'reviewed_intervals': [{'start_frame': 8912, 'end_frame': 10873}], 'events': []}


def event(identity='test-event', frame=9345, completion='complete'):
    return {'event_id': identity, 'source_frame': frame, 'time_s': frame/25,
            'direction': 'A->B', 'completion': completion}


class IntakeTests(unittest.TestCase):
    def test_valid_structure_remains_uncertified(self):
        value = draft(); value['events'] = [event()]
        result = inspect(value)
        self.assertTrue(result['ready_for_source_frame_and_provenance_check'])
        self.assertFalse(result['independent_reference_certified'])
        self.assertFalse(result['model_count_accuracy_calculated'])

    def test_zero_event_is_not_auto_truth(self):
        result = inspect(draft())
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(result['complete_scoped_events_for_later_matching'], [])
        self.assertFalse(result['independent_reference_certified'])

    def test_same_frame_two_cows_preserved(self):
        value = draft(); value['events'] = [event('a'), event('b')]
        result = inspect(value)
        self.assertEqual(len(result['complete_scoped_events_for_later_matching']), 2)
        self.assertEqual(result['blocking_findings'], [])
        self.assertTrue(any('NOT_AUTOMATIC_DEDUPLICATION' in row for row in result['warnings']))

    def test_coverage_one_frame_gap_blocks(self):
        value = draft(); value['reviewed_intervals'] = [{'start_frame': 8912, 'end_frame': 9899}, {'start_frame': 9901, 'end_frame': 10873}]
        self.assertIn('REQUESTED_SCOPE_NOT_FULLY_REVIEWED', inspect(value)['blocking_findings'])

    def test_wrong_source_rejected(self):
        value = draft(); value['source']['sha256'] = '0'*64
        with self.assertRaises(ValueError): inspect(value)

    def test_wrong_gate_blocks(self):
        value = draft(); value['source']['gate']['axis'] = 'x'
        self.assertIn('SOURCE_GATE_OR_EVENT_DEFINITION_MISMATCH', inspect(value)['blocking_findings'])

    def test_uncertain_event_needs_resolution(self):
        value = draft(); value['events'] = [event(completion='uncertain')]
        self.assertIn('SCOPED_CENSORED_OR_UNCERTAIN_EVENTS_NEED_ADJUDICATION', inspect(value)['blocking_findings'])

    def test_censored_event_needs_resolution(self):
        value = draft(); value['events'] = [event(completion='censored')]
        self.assertIn('SCOPED_CENSORED_OR_UNCERTAIN_EVENTS_NEED_ADJUDICATION', inspect(value)['blocking_findings'])

    def test_unreliable_frame_not_accepted(self):
        value = draft(); value['reviewed_intervals'] = [{'start_frame': 0, 'end_frame': 14008}]; value['events'] = [event(frame=14008)]
        self.assertIn('UNRELIABLE_SOURCE_FRAME_USED_AS_COMPLETE', inspect(value)['blocking_findings'])

    def test_known_QA_blocks_even_reviewer_changed(self):
        value = json.loads(KNOWN_QA.read_text(encoding='utf-8'))
        value['reviewer'] = 'renamed-reviewer'
        self.assertIn('KNOWN_QA_FIXTURE_NOT_HUMAN_REFERENCE', inspect(value)['blocking_findings'])

    def test_bad_timestamp_rejected(self):
        value = draft(); value['events'] = [event()]; value['events'][0]['time_s'] += .04
        with self.assertRaises(ValueError): inspect(value)

    def test_nan_timestamp_rejected(self):
        value = draft(); value['events'] = [event()]; value['events'][0]['time_s'] = float('nan')
        with self.assertRaises(ValueError): inspect(value)

    def test_unsupported_status_cannot_self_freeze(self):
        value = draft(); value['annotation_status'] = 'frozen'
        with self.assertRaises(ValueError): inspect(value)

    def test_input_structure_not_mutated(self):
        value = draft(); value['events'] = [event()]
        before = json.dumps(value, sort_keys=True)
        inspect(value)
        self.assertEqual(before, json.dumps(value, sort_keys=True))

    def test_nonblind_declaration_not_promoted(self):
        value = draft(); value['blinding'] = 'prior_outputs_seen'
        result = inspect(value)
        self.assertTrue(any('DO_NOT_CLAIM_BLIND_TEST' in row for row in result['warnings']))
        self.assertFalse(result['independent_reference_certified'])

    def test_cli_does_not_overwrite_input(self):
        before = hashlib.sha256(KNOWN_QA.read_bytes()).hexdigest()
        result = subprocess.run([sys.executable, str(ROOT/'tools/inspect_annotation.py'), str(KNOWN_QA), '--output', str(KNOWN_QA)],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FileExistsError', result.stderr)
        self.assertEqual(before, hashlib.sha256(KNOWN_QA.read_bytes()).hexdigest())


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IntakeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'all_data_are_structural_tests_not_human_truth': True}
    output = ROOT/'results/intake_test_results.json'
    assert not output.exists()
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
    raise SystemExit(0 if result.wasSuccessful() else 1)
