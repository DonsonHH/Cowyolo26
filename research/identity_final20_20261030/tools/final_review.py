from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=load(ROOT/'protocol/run_v1.json');e=load(ROOT/'protocol/execution_v1.json');v=load(ROOT/'results/independent_verification.json');a=load(ROOT/'results/archive_verification.json')
assert sha(ROOT/'protocol/run_v1.json')==e['protocol_sha256']=='8d16342abc1c36fd13a85c7b42a758521158d6908b196d477b07ba34ab6a593a'
assert sha(ROOT/'protocol/execution_v1.json')=='1016d9cd9279fb0d87f5b7a9bfb2a243f99183e86b551ce4cbf2976d059db0a1'
for name,digest in e['files_sha256'].items():assert sha(ROOT/name)==sha(ROOT/'delivery'/name)==digest
assert[[x[k]for k in['known_Top1','C','W','U','unknown_FA']]for x in v['main_outcomes']]==[[22,10,2,18,3],[30,3,0,27,0]]
assert a['archive_bytes']==4413444 and a['manifest_files']==127
archive=ROOT/'final20_delivery_v1.tar.gz';assert sha(archive)==a['archive_sha256']
for row in load(ROOT/'delivery/result_manifest.json'):assert sha(ROOT/'delivery'/row['file'])==row['sha256']
visual=load(ROOT/'results/visual_review.json');assert visual['source_images_actually_viewed']==8 and visual['posthoc_retrieval_cases_actually_viewed']==23 and visual['retrieval_pages']==6
fig=load(ROOT/'results/figure_visual_review.json');assert fig['figure_PNG_actually_viewed']and fig['SVG_XML_parsed'];ET.parse(ROOT/'results/figures_v2/final20_primary.svg')
server=(ROOT/'evidence/final_server_read.txt').read_text();assert all(job+'|'in server for job in['130877','130878','130879'])and server.count('|COMPLETED|0:0|')==9 and'FINAL20_ORIGINAL_EXECUTION_CODE_WEIGHTS_AND_RESULTS_UNCHANGED_AFTER_COLLECTION'in server
report=ROOT/'保留20身份结果与自动接受限制.md';text=report.read_text();links=[]
for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)',text):
 name=unquote((match[1]or match[2]).strip());path=Path(name);path=path if path.is_absolute()else report.parent/path;assert path.exists(),name;links.append(str(path))
files=[ROOT/'计划与验收.md',ROOT/'校准冻结结果与像素状态.md',report,ROOT/'delivery/result_manifest.json',ROOT/'delivery/results/evaluation/summary.json']+[f for folder in['tools','protocol','evidence','results']for f in(ROOT/folder).rglob('*')if f.is_file()and'__pycache__'not in f.parts]
result=dict(v);result.update({'status':'FINAL20_RESERVED_ID_EVALUATION180_FORWARDS_ALL_FIXED_WORKPOINTS_ORIGINAL_ARCHIVE_AND_LOW_AUTOMATIC_COVERAGE_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),'registered_IDs':10,'unknown_IDs':10,'images':90,'actual_model_image_forwards':180,'actual_network_calls':16,'warmups':0,'new_training_updates':0,'new_board_forwards':0,
 'all8_workpoints_preserved':True,'all20_paired_ID_contrasts_preserved':True,'primary_Top1_C_W_U_FA':[[22,10,2,18,3],[30,3,0,27,0]],'new_primary_accepted_query_images':3,'new_primary_accepted_publisher_IDs':2,'old_unknown_FA_query_images':3,'old_unknown_FA_publisher_IDs':1,
 'first_final_ID_pixels_requested_only_after_code_model_and_threshold_freeze':True,'calibration_primary_fold_not_changed_by_test':True,'all_original_source_JPEGs_and127_manifest_files_verified':True,'heldout_IDs_now_seen_and_reuse_limits_disclosed':True,'same_scene_and_detection_parent_pixel_overlap_scope_disclosed':True,'full_project_or_crossfarm_unseen_pixel_claimed':False,'physical_crossyear_cow_ID_mapping_proven':False,
 'perfect_ranking_and_zero_FA_not_population_guarantees_disclosed':True,'automatic_reliable_identity_recovery_proven':False,'default_model_or_threshold_changed':False,'board_identity_final90_evaluated':False,'source_visuals_viewed':8,'explanation_cases_viewed':23,'figure_layout_only_V2_and_V1_preserved':True,'report_read_fully_and_manual_scope_review_completed':True,'assistant_self_review_not_independent_human':True,'all_new_server_jobs_terminal':True,
 'report_sha256':sha(report),'local_report_links_checked':len(links),'evidence_hashes':{f.relative_to(ROOT).as_posix():sha(f)for f in sorted(set(files))},'whole_goal_complete':False})
target=ROOT/'results/final_review.json';assert not target.exists();target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in['status','primary_Top1_C_W_U_FA','report_sha256','local_report_links_checked']}))
