from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((ROOT/'delivery/results/study/summary.json').read_text());v=json.loads((ROOT/'results/independent_verification.json').read_text())
assert len(s['all_rule_selected_choices'])==5 and v['selected_actual_candidate_events']==1
result={'status':'NO_GLOBAL_CROP_OR_THRESHOLD_REPLACEMENT_AFTER_VALIDATION_FROZEN_DEVELOPMENT_CHECK',
'created_UTC':datetime.now(timezone.utc).isoformat(),'frozen_selection_sha256':s['frozen_selection_sha256'],'summary_sha256':sha(ROOT/'delivery/results/study/summary.json'),
'primary_observations':['C28 P1+validationcalibration19C0W11U0FvsP0original21C0W9U0F.',
'C28factorialcontrol:P1original21C0F;P0newcalibration14C0F;P1newcalibration19C0F. Cropandthresholdjointcomparisonnotcropalonecausalclaim.',
'C26P0newcalibration26C3FvsP0original27C5F;3/30unknown10%exceeds5%validationtarget.',
'A P0newcalibration19C3FvsP0original12C0F.',
'ValidationselectedactualqueryoutputsoneE010anonymous009candidate,notverifiedidentity.'],
'validation_selected_recipes_preserved':s['all_rule_selected_choices'],
'deployed_counting_or_identity_pipeline_changed':False,'all_original_checkpoints_thresholds_photos_and_user12_preserved':True,
'per_scene_seed_override_added':False,'current_actual_passage_identity_accuracy_available':False,'new_training_updates':0,
'next_gate':'Stopblindcentreringcropsandruntime180reversal;nextactualdetector-to-torsosupervisionandindependentpassageidentityreference,thennewvalidationcalibrationandPYNQjointtest.',
'FPGA_execution_verified':False,'whole_goal_complete':False}
p=ROOT/'results/adoption_decision.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'baseline_regressions':s['baseline_regressions'],'all_actual_candidate_config_pairs':sum(r['real_event_passed_threshold'] for r in s['evaluation_conditions'])}))
