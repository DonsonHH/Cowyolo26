from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_bytes(json.dumps(v,ensure_ascii=False,indent=2).encode()+bytes([10]))
old=load(ROOT/'results/overview_review_20261030_v16.json');main=PROJECT/'研究阶段总结_20261030.md';entry=load(ROOT/'results/entrypoint_update_20261030_v17.json')
records=list(old['current_numeric_record_files'])
for row in records:assert sha(Path(row['path']))==row['sha256']
new=PROJECT/'identity_final20_arm_20261030/results/final_review.json';records.append({'path':str(new),'sha256':sha(new)})
snapshot=ROOT/'snapshots/overview_v16_before_final20_ARM/研究阶段总结_20261030.md';assert sha(snapshot)==old['document']['sha256']
links=[]
for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)',main.read_text()):
 target=unquote((match[1]or match[2]).strip())
 if target.startswith(('http://','https://','#')):continue
 p=Path(target);p=p if p.is_absolute()else main.parent/p;assert p.exists(),target;links.append(str(p))
polish={'status':'V17_REPORT_READ_PREPROCESS_ORDER_DEFAULT_MODEL_AND_HISTORICAL_WORDING_CHECKED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'changes':['Older planned board check now points to completed3.11','All90preprocessing precedes old/new network order','Two retained model files distinguished from default encoder'],
 'current_entrypoints':[{'path':row['path'],'sha256':sha(Path(row['path']))}for row in entry['current_entrypoints']]}
pp=ROOT/'results/entrypoint_polish_20261030_v17.json';save(pp,polish)
v=dict(old);v.update({'status':'CURRENT_OVERVIEW_V17_FULL_READ_SAME90_REAL_ARM184_CALLS_ORIGINAL_VECTORS480_PARITY_AND_SCOPE_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'document':{'path':str(main),'sha256':sha(main)},'entire_current_overview_read_in_full':True,
 'manual_review_topics':['Already scored90JPEGS, no new identity or late date pixels','90input hashes before native creation,180formal4warmups184calls','Each model gallery and queries encoded by itself,1200ID scores480decisions','Full10ID rank,Top1,Top5 and acceptance same as CPU','180raw and normalized vectors saved,unchanged1e-4 and1e-5 gates','Old149.29ms new150.35ms isolated network, no speed advantage/fullFPS claim','JPEG timer after prior integrity read, not cold input','No newCPU reference,training orPL forwards','24archive members23manifest files and ownPIDs absent','Defaultencoder,both models,libraries,O8,lock,local services checked','SameCPU/ARM cohort not2independent tests','3/30autoaccept remains low,0FA not population guarantee,whole objective incomplete'],
 'current_numeric_record_files':records,'local_overview_links_checked':len(links),'previous_review_preserved':'overview_review_20261030_v16.json',
 'previous_overview_snapshot':{'path':str(snapshot.resolve()),'sha256':sha(snapshot)},
 'entrypoint_update_evidence':{'path':str((ROOT/'results/entrypoint_update_20261030_v17.json').resolve()),'sha256':sha(ROOT/'results/entrypoint_update_20261030_v17.json')},
 'entrypoint_polish_evidence':{'path':str(pp.resolve()),'sha256':sha(pp)},'new_model_forwards':184,
 'new_model_forward_breakdown':{'old_C_ARM_measured':90,'old_C_ARM_warmups':2,'new_C_ARM_measured':90,'new_C_ARM_warmups':2,'CPU_PL_verification_forwards':0},
 'new_training_updates':0,'new_board_actions_performed':True,'new_periodic_counter_or_identity_run':False,
 'new_reserved20_ID_component_evaluation':False,'same90_image_hardware_consistency_only':True,'new_independent_identity_test':False,
 'current_board_carrier_live_rechecked':True,'current_board_eth0_carrier':0,'default_model_tracker_or_reject_threshold_changed':False,
 'reservedMar05toMar11_pixels_opened':False,'main_paper_contribution_verified':False,'whole_goal_complete':False})
save(ROOT/'results/overview_review_20261030_v17.json',v)
print(json.dumps({'status':v['status'],'main_local_links':len(links),'bound_numeric_records':len(records),'main_SHA256':sha(main)}))
