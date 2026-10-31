"""Freeze reviewed reports only after actual computation and visual inspection."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/'delivery/results/study_v2';s=load(out/'summary.json');v=load(ROOT/'results/independent_verification.json')
source=load(ROOT/'delivery/results/source_input_verification_v2.json')
visual=load(ROOT/'results/visual_review.json');media=load(ROOT/'results/media_verification.json')
case=load(ROOT/'results/reference94_photometric_audit.json');execution=load(ROOT/'protocol/execution_v2.json')
assert s['protocol_sha256']==execution['protocol_sha256']==sha(ROOT/'protocol/study_v2.json')
for name,digest in execution['files_sha256'].items():assert sha(ROOT/name)==digest,name
assert [r['TP'] for r in s['validation_metrics']]==[1819,1814,1830,1823,1824,1810]
assert [r['unmatched_prediction'] for r in s['validation_metrics']]==[587,563,571,522,777,756]
original=[r for r in s['video_metrics'] if r['scene']=='original' and r['counter']=='handoff_events']
assert [r['down'] for r in original]==[10,11,8,10,8,8] and all(r['up']==0 and r['formal_event_metrics'] is None for r in original)
toros5=[r['formal_event_metrics']['TP'] for r in s['video_metrics'] if r['scene']=='toros' and r['stride']==6 and r['counter']=='handoff_events']
toros30=[r['formal_event_metrics']['TP'] for r in s['video_metrics'] if r['scene']=='toros' and r['stride']==1 and r['counter']=='handoff_events']
assert toros5==[1,1,1,1,0,0] and toros30==[1,1,1,2,0,0]
assert all(r['formal_event_metrics']['FP']==0 for r in s['video_metrics'] if r['scene']=='toros' and r['counter']=='handoff_events')
assert s['actual_total_forwards']==25350 and s['counter_paths']==v['counter_paths']==36
assert v['baseline_raw_arrays_byte_exact']==8450 and v['failed_v1_preserved_arrays_byte_exact_to_v2']==7492
assert source['input_hashes_exact']==12675 and source['anchor_pixel_arrays_exact']==30
assert visual['figures_actually_viewed']==3 and visual['panels_actually_viewed']==34
for row in visual['files']:assert row['actually_viewed'] and sha(Path(row['path']))==row['sha256']
assert media['SVG_bars']==30 and media['input_panels']==30 and len(case['rows'])==90
assert not case['reference_is_independent_GT'] and not s['adopted_for_deployment'] and not s['new_independent_test']
states={}
for line in (ROOT/'evidence/final_job_read.txt').read_text(encoding='utf-8').splitlines():
    if re.match(r'^13061[1-6]\|',line):
        parts=line.split('|');states[parts[0]]=parts[1:3]
assert states=={'130611':['FAILED','1:0'],'130612':['COMPLETED','0:0'],'130613':['COMPLETED','0:0'],
    '130614':['FAILED','1:0'],'130615':['COMPLETED','0:0'],'130616':['COMPLETED','0:0']}
documents=[];links=0
for name in ['计划与验收.md','输入亮度对照结果与训练决策.md','Review与当前状态.md']:
    file=ROOT/name;text=file.read_text(encoding='utf-8');assert '\ufffd' not in text
    for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
        target=unquote(match[1] or match[2])
        if re.match(r'^[A-Za-z]:[/\\]',target):assert Path(target).exists(),target;links+=1
    documents.append({'path':str(file.resolve()),'sha256':sha(file),'lines_read_and_reviewed':len(text.splitlines())})
paths=['protocol/study_v1.json','protocol/execution_v1.json','protocol/study_v2.json','protocol/execution_v2.json',
    'results/transfer_verification.json','results/independent_verification.json','results/media_verification.json','results/visual_review.json',
    'results/reference94_photometric_audit.json','delivery/results/source_input_verification_v2.json','delivery/results/baseline_trace_probe.json',
    'delivery/results/study_v2/summary.json','delivery/results/study_v2/baseline_gate.json','delivery/results/failed_v1_artifact_manifest.json',
    'evidence/final_job_read.txt','evidence/status02.txt','evidence/status_v2_06.txt','evidence/collection_v2.txt',
    'tools/run_study.py','tools/run_study_v2.py','tools/photometric.py','tools/verify_source_inputs.py','tools/verify_source_inputs_v2.py',
    'tools/verify_independent.py','tools/case_audit.py','tools/render_media.py','tools/verify_media.py']
result={'status':'THREE_FIXED_INPUT_CONDITIONS25350_ORT_FORWARDS36_EVENT_PATHS_AND34_PANELS_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_successful_study_forwards':25350,'failed_v1_completed_arrays_preserved':7492,
    'baseline_raw_arrays_byte_exact':8450,'baseline_video_input_hashes_exact':2654,'all_input_hashes_rebuilt_from_source':12675,
    'validation_matching_problems':9426,'raw_video_rows':15924,'counter_observation_ticks':16404,'counter_paths':36,'publisher_matching_paths':24,
    'original_FP32_QDQ_counts_by_none_gamma_CLAHE':[10,11,8,10,8,8],
    'validation_TP_by_none_gamma_CLAHE':[1819,1814,1830,1823,1824,1810],
    'Toros5Hz_TP_by_none_gamma_CLAHE':toros5,'Toros30Hz_TP_by_none_gamma_CLAHE':toros30,
    'head_arrays_in_remaining_case_diagnosis':90,'development_reference_is_independent_GT':False,
    'actual_SVG_bars_checked':30,'input_panels_checked':30,'figures_actually_viewed':3,'panels_actually_viewed':34,
    'new_training_updates':0,'actual_board_actions':0,'new_independent_test':False,'new_identity_accuracy_proven':False,
    'photometric_candidates_adopted_for_deployment':False,'whole_goal_complete':False,
    'all_own_launched_jobs_terminal':True,'job_states':states,'local_links_checked':links,
    'review_scope':'assistant_full_self_review_plus_separate_numeric_and_source_pixel_recomputation_not_independent_human_GT',
    'evidence_hashes':{name:sha(ROOT/name) for name in paths},'documents':documents}
target=ROOT/'results/final_review.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','documents']}))
