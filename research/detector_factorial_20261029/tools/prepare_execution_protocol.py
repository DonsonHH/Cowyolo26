from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=ROOT/'protocol/training_v2_lowres_plan.json';p=json.loads(plan.read_text())
p.update({'status':'FROZEN_BEFORE_NEW_PREFLIGHT_OR_15_FORMAL_TRAINING_RUNS','version':3,'created_UTC':datetime.now(timezone.utc).isoformat(),
 'planned_v2_sha256':sha(plan),'hardware_status':'RecoveredactualPYNQ3.1.1;424realnetworkforwardsreviewed;O8confirmedbyuser;192prioritizedbutall3sizesretained.',
 'fixed_lane_crop_review_sha256':sha(PROJECT/'lowres_roi_20261029/results/final_review.json'),
 'real_board_review_sha256':sha(PROJECT/'pynq_board_validation_20261029/results/final_review.json'),
 'new_training_runs_planned':15,'new_training_runs_submitted_at_freeze':0,
 'expected_initial_state_digests':{str(r['seed']):r['initial_state_digest'] for r in p['baseline_checkpoint_conditions']},
 'preflight_groups':[{'name':'plain192','imgsz':192,'right_angle':False},{'name':'rot192','imgsz':192,'right_angle':True},{'name':'rot256','imgsz':256,'right_angle':True}],
 'preflight_limit':'FullrealtrainerrunabortedbyexplicitSmokeStopafter2actualoptimizerupdates;workers0onlyforsmoke;noreusedweights.',
 'validation_definition':'PublishedclippedrotatedtorsopolygonAABB;unrotatedvalidationpertrainer,pairedCW90squarevalidationaftermultiplecheckpointfreeze.',
 'board_engine_baseline':'Userconfirmedexistingyolo26_optimization_8;192/256supportednow,320sameenginegraphsupportremainsrequired.',
 'deployment_model_selection':'Allseedsevaluated;fixedprimaryseed26inheritspriorhumanaccepteddevelopmentroute;nochoiceoncount12orToros.',
 'whole_goal_complete':False})
p.pop('new_training_runs_submitted',None)
p['new_conditions']=[{**c,'array_index':i,'execution':'frozen_not_submitted'} for i,c in enumerate(c for c in p['conditions'] if c['execution']!='historical_control_retained')]
assert len(p['new_conditions'])==15
p['implementation_sha256']={name:sha(ROOT/'tools'/name) for name in ['common.py','observed_trainer.py','rotation_training.py','preflight.py']}
file=ROOT/'protocol/training_v3.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'protocol_sha256':sha(file),'new_conditions':15,'historical320controls':3,'epochs':10,'batch':32}))
