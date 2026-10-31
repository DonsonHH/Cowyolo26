"""Completion audit: separate finished preparation from missing external inputs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(8*1024*1024), b''): h.update(chunk)
    return h.hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

source = PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4'
source_record = {'path': str(source), 'bytes': source.stat().st_size, 'sha256': sha(source)}
assert source_record['bytes'] == 260096040
assert source_record['sha256'] == '5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1'
prior = []
for stage in ['integer_qat_20261028', 'identity_risk_diagnosis_20261028', 'activation_range_20261028']:
    path = PROJECT/stage/'results/final_review.json'
    record = load(path)
    requirements = record.get('remaining_original_goal_requirements', record.get('whole_goal_completion_audit', []))
    relevant = [r for r in requirements if 'bidirectional' in r['requirement'].lower() or 'pynq' in r['requirement'].lower()]
    assert len(relevant) == 2 and all(r['status'] in ['incomplete', 'unverified'] for r in relevant)
    assert record['whole_goal_complete'] is False
    prior.append({'path': str(path), 'sha256': sha(path), 'created_UTC': record['created_UTC'],
                  'same_missing_reference_and_board_inputs': relevant})
preparation = load(ROOT/'results/preparation_verification.json')
assert preparation['catalog_conditions'] == 17 and preparation['intake_tests'] == 16
assert preparation['new_reference_received'] is False
live = (ROOT/'results/live_compute_audit.txt').read_text(encoding='utf-8')
for job in ['129998','129999','130000','130002','130003','130004','130005']:
    assert any(line.startswith(job+'|') and '|COMPLETED|0:0|' in line for line in live.splitlines())
result = {'status': 'PREPARATION_COMPLETE_MAIN_EVALUATION_AND_BOARD_GATES_REQUIRE_USER_INPUT',
          'created_UTC': datetime.now(timezone.utc).isoformat(),
          'previous_goal_turn_classification': 'progress', 'current_goal_turn_classification': 'progress',
          'original_full_goal_achieved': False,
          'source_video': source_record,
          'current_preparation': preparation,
          'current_compute_jobs_confirmed_terminal': ['129998','129999','130000','130002','130003','130004','130005'],
          'not_a_wait_on_live_compute': True,
          'recurrence_evidence_from_three_preceding_goal_phase_audits': prior,
          'human_inputs_received_this_goal_turn': {'independent_review_JSON': False,
                                                 'PYNQ_SSH_or_image_tool_versions': False},
          'next_original_scope_requirements': [
              {'requirement': 'Independent sourceevent scoring', 'status': 'blocked_on_input',
               'needed': 'User-provided independentreviewJSON; then sourceframe/provenance/ambiguity checks before frozenmatching'},
              {'requirement': 'PYNQ-Z2 actualjointinference', 'status': 'blocked_on_input',
               'needed': 'SSHhost/user/port andPYNQimage/Vivado/HLSversion information; then read-only environmentcheck andactual modelvalidation'},
              {'requirement': 'IdentityRFID fieldcorrespondence andpaperprincipalcontribution', 'status': 'still_unverified',
               'needed': 'Evidence matching intendedclaim after independentdata andjointboard evaluation'}],
          'available_preparation_actions_completed': ['Annotationjump fix andrealbrowserregression',
            '17frozenprediction artifactcatalog', 'Draftintake checks andknownQAexclusion',
            'Originalsourcehash check', 'Existingtraining anddiagnostic jobs verifiedterminal'],
          'why_more_existing_devset_training_is_not_next_gate': 'Additional seen-data trials cannot supply independenttruth or actualboard measurements; do not substitute them for the missingoriginal requirements.',
          'reference_or_board_results_invented': False, 'whole_goal_complete': False}
target = ROOT/'results/required_input_audit.json'
assert not target.exists()
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status':result['status'], 'source_sha256':source_record['sha256'],
                  'prior_repeated_input_gap_audits':len(prior), 'research_compute_waiting':False,
                  'whole_goal_complete':False}))
