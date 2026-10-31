from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


plan=load(ROOT/'protocol/run_v1.json');verified=load(ROOT/'results/independent_verification.json');summary=load(ROOT/'delivery/results/evaluation/summary.json')
assert verified['formal_updates_checked']==1800 and verified['formal_training_image_forwards']==57600
assert verified['evaluation_feature_vectors']==3780 and verified['evaluation_decisions']==7560 and verified['ID_score_cells_checked']==218160
assert summary['actual_evaluation_model_image_forwards']==3780 and summary['actual_network_calls']==318
assert len(summary['outcomes'])==42 and len(summary['models'])==6
assert load(ROOT/'results/paired_analysis.json')['contrast_conditions']==24
counts=[]
for row in summary['outcomes']:
 if row['dataset']=='Cows2021'and row['scope']in['fold0','fold1']and row['threshold_policy']=='Cows_calibrated':
  counts.append([row['metrics'][key]for key in['known_closed_top1_correct','known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts']])
assert counts==[[37,0,0,60,1],[33,1,0,59,0],[54,9,0,51,5],[51,1,0,59,0],[32,0,0,60,0],[37,0,0,60,0],[45,6,1,53,5],[52,7,0,53,0],[38,0,0,60,1],[30,0,0,60,0],[51,11,0,49,4],[50,10,0,50,0]]
primary=next(row for row in summary['models']if row['condition']['name']=='C_domain_seed26')
checkpoint=ROOT/'delivery/results/training/C_domain_seed26/last_encoder.pt'
assert sha(checkpoint)==primary['sha256']=='b435fb4599d307c0dd8bf3adccb42a466c271a3fdf23ab91d585d463b70cc912'
for name,panels in[('source_visual_review.json',12),('training_visual_review.json',24)]:
 visual=load(ROOT/'results'/name);assert visual['actually_viewed']
 for row in visual['files']:assert row['actually_viewed']and sha(Path(row['file']))==row['sha256']
assert load(ROOT/'results/source_border_observation.json')['original_file_actually_viewed']
assert load(ROOT/'results/transfer_verification.json')['bytes']==44191516
for row in load(ROOT/'delivery/result_manifest.json'):assert sha(ROOT/'delivery'/row['file'])==row['sha256']
account=(ROOT/'evidence/final_server_read.txt').read_text()
assert '130772|cow-id-domain-smoke|COMPLETED|0:0|'in account and '130837|cow-id-domain-eval|COMPLETED|0:0|'in account
for index in range(6):assert f'130777_{index}|cow-id-domain-pair|COMPLETED|0:0|'in account
assert '130835|cow-id-domain-eval|FAILED|1:0|'in account
assert 'AttributeError'in(ROOT/'delivery/logs/evaluation-130835.err').read_text()
assert load(ROOT/'evidence/evaluation_slurm_line_ending_correction.json')['new_model_forwards_from_rejection']==0
documents=[ROOT/'计划与验收.md',ROOT/'身份域适配配对训练与开发结果.md'];links=[]
for document in documents:
 content=document.read_text(encoding='utf-8');assert '\ufffd'not in content
 for target in re.findall(r'\]\(([^)]+)\)',content):
  target=target.strip('<>')
  if not target.startswith(('http:','https:')):
   path=(document.parent/unquote(target)).resolve();assert path.exists();links.append(str(path))
evidence=[path for directory in['tools','protocol','results','evidence']for path in(ROOT/directory).rglob('*')if path.is_file()and path.suffix in['.py','.slurm','.json','.jsonl','.txt','.log']]
result={'status':'SIX_DOMAIN_SOURCE_TRAINING_PAIRS1800_UPDATES3780_FEATURES_MATCHED20_ID_DEVELOPMENT_AND_LOW_COVERAGE_REVIEWED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'training_conditions':6,'formal_optimizer_updates':1800,
        'formal_training_image_forwards':57600,'discarded_smoke_updates':2,'smoke_image_forwards':64,'evaluation_model_image_forwards':3780,
        'all_new_model_image_forwards':61444,'evaluation_network_calls':318,'evaluation_warmups':0,
        'all6_same_start_encoder_last300_frozen_before_calibration':True,'all6_thresholds_joint_frozen_before_development_and_retention':True,
        'new_Cows_training_IDs':16,'new_Cows_training_images':457,'future20_ID_pixels_opened':False,'reservedMar05toMar11_pixels_opened':False,
        'source_training_images_and_ID_counts_differ_not_one_pixel_identical_factor':True,
        'outcome_conditions':42,'independently_recomputed_decisions':7560,'independently_recomputed_ID_scores':218160,
        'paired_per_ID_contrasts':24,'primary_C_domain_seed26_Top1_folds':[54,51],
        'primary_C_domain_seed26_calibrated_C_W_U_FA':[[9,0,51,5],[1,0,59,0]],'primary_fold_known_denominator':60,'unknown_query_denominator':120,
        'primary_full40_Top1':99,'primary_full40_C_W_U_FA':[10,1,109,5],
        'primary_original_source_retention_Top1_C_W_U_FA':[28,22,0,8,0],
        'primary_encoder_sha256':primary['sha256'],'primary_seed26_fixed_before_training':True,
        'all_seeds_full40_and_source_retention_results_preserved':True,'source_panels_actually_viewed':12,'actual_training_input_panels_actually_viewed':24,
        'publisher_blue_border_source_sample_rechecked_not_renderer_added':True,
        'download350_preserved107_missing_only_completed':True,'failed_eval130835_feature_forwards':0,'CRLF_submission_rejected_before_job_creation':True,
        'all_training_and_evaluation_jobs_terminal':True,'full_original175_member174_manifest_archive_verified':True,
        'new_board_forwards':0,'new_deployment_model_or_threshold_adopted':False,'reliable_automatic_ID_recovery_proven':False,
        'current12_events_permanent_ID_mapping_obtained':False,'new_independent_test':False,
        'documents':[{'path':str(path),'sha256':sha(path)}for path in documents],
        'evidence_hashes':{path.relative_to(ROOT).as_posix():sha(path)for path in evidence},'local_links_checked':len(links),
        'assistant_self_review_not_independent_human':True,'whole_goal_complete':False}
output=ROOT/'results/final_review.json';assert not output.exists();output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({key:value for key,value in result.items()if key not in['documents','evidence_hashes']}))
