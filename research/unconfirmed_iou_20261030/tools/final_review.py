from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');causal=load(ROOT/'results/one_frame_independent_verification.json');s=load(ROOT/'delivery/results/control_v2/summary.json')
appendix=load(ROOT/'results/native_Toros_score_appendix.json');pairs=load(ROOT/'delivery/results/control_v2/paired_metrics.json')
assert v['cache_count']==111 and v['tracker_conditions']==222 and v['counter_paths']==444 and v['counter_observation_ticks']==217078
assert v['scope_metric_rows']==476 and v['paired_scope_rows']==238 and v['changed_scope_rows']==38
assert s['all111_baseline_gate_before_control'] and s['reused_successful_failed_run_baselines']==91
assert v['hardware_Toros_shared_ID_allocator_original_order_retained'] and v['no_ID_relabeling_or_tolerance_relaxation']
def pair(name):return next(r for r in pairs if r['cache']==name and r['counter']=='handoff_events')
assert [pair('new_O8_original_s5')[k] for k in ['baseline_down','control_down']]==[10,11]
assert [pair('old_O8_original_s5')[k] for k in ['baseline_down','control_down']]==[11,11]
assert [pair('native_original_seed26')[k] for k in ['baseline_down','control_down']]==[12,12]
assert [pair('new_O8_toros_s6')[k][0] for k in ['baseline_TP_FP_FN','control_TP_FP_FN']]==[3,3]
assert [pair('new_O8_toros_s1')[k][0] for k in ['baseline_TP_FP_FN','control_TP_FP_FN']]==[4,3]
assert [pair('new_FP32_toros_s6')[k][0] for k in ['baseline_TP_FP_FN','control_TP_FP_FN']]==[3,2]
assert causal['before_count']==10 and causal['diagnostic_count']==11 and causal['all_pre9550_states_exact'] and causal['frame_rule_not_for_deployment']
assert len(appendix['rows'])==8 and appendix['original_metrics_file_unchanged']
assert [r['formal_event_metrics']['TP'] for r in appendix['rows'] if r['cache']=='native_toros_generic' and r['counter']=='handoff_events']==[6,6]
states={}
for line in (ROOT/'evidence/causal_collection.txt').read_text(encoding='utf-8').splitlines():
    if re.match(r'^1306(?:37|38|39|41)\|',line):
        parts=line.split('|');states[parts[0]]=parts[1:3]
assert states=={'130637':['FAILED','1:0'],'130638':['FAILED','1:0'],'130639':['COMPLETED','0:0'],'130641':['COMPLETED','0:0']}
documents=[];links=0
for name in ['计划与验收.md','未确认关联控制与不采用决定.md','Review与当前状态.md']:
    f=ROOT/name;text=f.read_text(encoding='utf-8');assert '\ufffd' not in text
    for m in re.finditer(r'\]\(<([^>]+)>\)',text):assert Path(unquote(m[1])).exists();links+=1
    documents.append({'path':str(f.resolve()),'sha256':sha(f),'lines_read_and_reviewed':len(text.splitlines())})
files=['protocol/control_v1.json','protocol/control_v2.json','protocol/execution_v1.json','protocol/execution_v2.json',
    'protocol/native_reference_link_v1.json','protocol/one_frame_causal_v1.json','results/transfer_verification.json','results/independent_verification.json',
    'results/native_Toros_score_appendix.json','results/one_frame_independent_verification.json','results/cpu_vs_board_baseline_diagnostic.json',
    'delivery/results/control_v2/summary.json','delivery/results/control_v2/all_baselines_gate.json','delivery/protocol/failed_baselines_preserved.json',
    'causal_delivery/results/one_frame_causal_summary.json','causal_delivery/results/one_frame_causal_trace.json.gz',
    'evidence/status01.txt','evidence/baseline_probe_status.txt','evidence/status_v2_01.txt','evidence/collection.txt','evidence/causal_collection.txt',
    'tools/confirmation_iou.py','tools/run_control.py','tools/run_control_v2.py','tools/verify_results.py','tools/append_native_scores.py','tools/probe_one_frame.py']
r={'status':'111_CACHE_UNCONFIRMED_IOU_CONTROL444_PATHS_AND_SINGLE_FRAME_CAUSAL_DIAGNOSIS_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'cache_conditions':111,'tracker_conditions':222,'counter_paths':444,
    'recorded_counter_observation_ticks':217078,'scope_metric_rows':476,'formal_existing_publisher_score_rows':272,'native_score_appendix_rows':8,
    'paired_scope_rows':238,'changed_scope_rows':38,'baseline_traces_reused_no_rerun':91,'all111_baselines_before_control':True,
    'original_hardware_Toros_sampler_order_reproduced':True,'ID_relabeling_or_event_gate_relaxation':False,
    'new_O8_cache_original_counts':[10,11],'old_O8_cache_original_counts':[11,11],'native_confirmed12_counts':[12,12],
    'new_O8_5Hz_TP_before_after':[3,3],'new_O8_30Hz_TP_before_after':[4,3],'new_FP32_5Hz_TP_before_after':[3,2],
    'single_frame_diagnostic_before_after':[10,11],'all_pre9550_states_exact_in_single_frame_diagnostic':True,
    'single_frame_special_case_is_deployment_rule':False,'frame9550_actual_pure_IoU_cost':v['focus']['pure_IoU_cost'],
    'frame9550_actual_fused_cost':v['focus']['fused_cost'],'restored_event_reference103_IoU':v['focus']['event_reference103_IoU'],
    'reference_is_independent_GT':False,'new_model_forwards':0,'new_training_updates':0,'actual_board_actions':0,
    'production_tracker_or_counter_files_changed':False,'control_adopted_for_deployment':False,'new_independent_test':False,
    'all_own_launched_jobs_terminal':True,'job_states':states,'whole_goal_complete':False,'documents':documents,'local_links_checked':links,
    'evidence_hashes':{p:sha(ROOT/p) for p in files}}
f=ROOT/'results/final_review.json';assert not f.exists();f.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ['documents','evidence_hashes']}))
