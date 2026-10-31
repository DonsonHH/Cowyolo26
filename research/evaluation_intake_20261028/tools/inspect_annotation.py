"""Inspect a page-exported review draft without certifying independent truth."""
from pathlib import Path
import argparse, hashlib, json, sys
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT / 'phase3_diagnosis_20261026/tools'))
from validate_annotations import validate

GATE = {'axis': 'y', 'roi_x': [.34, .75], 'boundaries': [.4, .6], 'stable_samples': 3}
KNOWN_QA = PROJECT / 'phase3_diagnosis_20261026/results/qa_fixture_annotation.json'


def inspect(value, first=8912, last=10873):
    if type(first) is not int or type(last) is not int or not 0 <= first <= last <= 14007:
        raise ValueError('Invalid reliable source scope')
    structural = validate(value)
    blocks = []
    if value.get('source', {}).get('gate') != GATE:
        blocks.append('SOURCE_GATE_OR_EVENT_DEFINITION_MISMATCH')
    coverage = structural['merged_reviewed_intervals']
    complete_coverage = any(a <= first and b >= last for a, b in coverage)
    if not complete_coverage: blocks.append('REQUESTED_SCOPE_NOT_FULLY_REVIEWED')
    if structural['complete_events_outside_declared_coverage']: blocks.append('COMPLETE_EVENT_OUTSIDE_REVIEWED_COVERAGE')
    if structural['complete_events_on_unreliable_source_frame']: blocks.append('UNRELIABLE_SOURCE_FRAME_USED_AS_COMPLETE')
    qa = json.loads(KNOWN_QA.read_text(encoding='utf-8'))
    known_ids = {r['event_id'] for r in qa['events']}
    qa_ids = [r['event_id'] for r in value['events'] if r['event_id'] in known_ids]
    if value.get('qa_only') is True or value.get('reviewer') == qa['reviewer'] or qa_ids:
        blocks.append('KNOWN_QA_FIXTURE_NOT_HUMAN_REFERENCE')
    scoped = [r for r in value['events'] if first <= r['source_frame'] <= last]
    unresolved = [r['event_id'] for r in scoped if r['completion'] != 'complete']
    if unresolved: blocks.append('SCOPED_CENSORED_OR_UNCERTAIN_EVENTS_NEED_ADJUDICATION')
    warnings = []
    if value['blinding'] == 'prior_outputs_seen':
        warnings.append('REVIEWER_DECLARES_PRIOR_PREDICTIONS_SEEN_DO_NOT_CLAIM_BLIND_TEST')
    if structural['coincident_event_groups_for_review']:
        warnings.append('COINCIDENT_EVENTS_REQUIRE_VISUAL_REVIEW_NOT_AUTOMATIC_DEDUPLICATION')
    complete = [{k: r[k] for k in ['event_id', 'source_frame', 'time_s', 'direction']}
                for r in scoped if r['completion'] == 'complete']
    return {'status': 'DRAFT_INSPECTION_COMPLETE_REFERENCE_NOT_CERTIFIED',
            'structural_check': structural, 'requested_scope_inclusive': [first, last],
            'coverage_complete': complete_coverage, 'blocking_findings': blocks, 'warnings': warnings,
            'known_QA_event_ids_present': qa_ids, 'unresolved_scoped_event_ids': unresolved,
            'complete_scoped_events_for_later_matching': complete,
            'ready_for_source_frame_and_provenance_check': not blocks,
            'independent_reference_certified': False, 'model_count_accuracy_calculated': False,
            'next_required_evidence': ['Trustedhumanreview/provenance confirmation',
                'Native sourceframe verification andeventdefinition', 'Recordedresolution ofambiguities'],
            'scope': 'File structure and declaredcoverage only; declarations alone do not provehumanorigin or independence'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('annotation', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    if args.annotation.resolve() == args.output.resolve(): raise ValueError('Output must not overwrite input')
    payload = args.annotation.read_bytes()
    value = json.loads(payload.decode('utf-8-sig'))
    result = inspect(value)
    result.update(input_path=str(args.annotation.resolve()), input_sha256=hashlib.sha256(payload).hexdigest(),
                  validator_source_sha256=hashlib.sha256((PROJECT / 'phase3_diagnosis_20261026/tools/validate_annotations.py').read_bytes()).hexdigest(),
                  known_QA_fixture_sha256=hashlib.sha256(KNOWN_QA.read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ['structural_check', 'complete_scoped_events_for_later_matching']}, ensure_ascii=False))


if __name__ == '__main__': main()
