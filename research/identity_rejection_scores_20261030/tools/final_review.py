from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


plan=load(ROOT/'protocol/run_v1.json');summary=load(ROOT/'results/summary.json');verified=load(ROOT/'results/independent_verification.json')
assert len(summary['conditions'])==84 and verified['decisions']==13860 and verified['ID_score_cells']==360360
assert verified['primary_calibration_method']=='absolute_cosine'and verified['primary_not_reselected_by_development_scores']
freeze=load(ROOT/'results/all_methods_calibration_freeze.json')
assert freeze['primary']['method']=='absolute_cosine'and freeze['primary']['calibration_counts']['C']==10
assert[row['calibration_counts']['C']for row in freeze['thresholds']if row['model']=='C_domain_seed26']==[10,7,9]
for spec in plan['models']:
 assert sha(Path(spec['calibration_file']))==spec['calibration_sha256']
 for binding in spec['development_files'].values():assert sha(Path(binding['file']))==binding['sha256']
assert load(ROOT/'results/ID_intervals.json')and len(load(ROOT/'results/ID_intervals.json'))==84
assert len(load(ROOT/'results/paired_to_absolute.json'))==56
documents=[ROOT/'计划与验收.md',ROOT/'拒识分数对照与校准选择.md'];local=[]
for document in documents:
 for target in re.findall(r'\]\(([^)]+)\)',document.read_text(encoding='utf-8')):
  target=target.strip('<>')
  if not target.startswith(('http:','https:')):
   path=(document.parent/unquote(target)).resolve();assert path.exists();local.append(str(path))
evidence=[path for name in['tools','protocol','results']for path in(ROOT/name).rglob('*')if path.is_file()and path.suffix in['.py','.json']]
result={'status':'SEVEN_MODELS_THREE_REJECTION_SCORES21_CALIBRATIONS84_DEVELOPMENT_CONDITIONS_AND_NO_POSTHOC_PROMOTION_REVIEWED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'fixed_models':7,'score_methods':3,'calibrated_thresholds':21,
        'development_conditions':84,'independent_decisions':13860,'independent_ID_score_cells':360360,
        'ID_interval_sets':84,'paired_to_absolute_contrasts':56,'primary_seed26_method_by_calibration':'absolute_cosine',
        'primary_calibration_C_absolute_margin_ratio':[10,7,9],'primary_not_changed_by_development_outcomes':True,
        'primary_margin_fold_C_W_U_FA':[[13,0,47,1],[6,0,54,1]],
        'primary_ratio_fold_C_W_U_FA':[[12,0,48,0],[2,0,58,0]],
        'same_top1_ranking_for_all_score_methods':True,'distance_ratio_formula_explicit_not_claimed_full_OSNN_replication':True,
        'calibration20_ID_vs_development20_ID_matched_full40_and_retention6_are_stress':True,
        'same_unknown_queries_reused_and_bootstrap_zero_not_population_zero_disclosed':True,
        'new_model_forwards':0,'new_training_updates':0,'new_board_forwards':0,'future20_ID_pixels_opened':False,
        'new_deployment_method_or_threshold_adopted':False,'reliable_automatic_recovery_proven':False,
        'documents':[{'path':str(path),'sha256':sha(path)}for path in documents],
        'evidence_hashes':{path.relative_to(ROOT).as_posix():sha(path)for path in evidence},'local_links_checked':len(local),
        'assistant_self_review_not_independent_human':True,'whole_goal_complete':False}
p=ROOT/'results/final_review.json';assert not p.exists();p.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps({key:value for key,value in result.items()if key not in['documents','evidence_hashes']}))
