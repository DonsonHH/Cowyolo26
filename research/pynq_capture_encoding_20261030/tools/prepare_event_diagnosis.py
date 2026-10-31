from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,ast
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'rot192_event_diagnosis_20261030';OLD=PROJECT/'lowres_event_audit_20261029'
ROOT.mkdir(exist_ok=False)
for name in ['tools','input','protocol']:(ROOT/name).mkdir()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['reference_boxes.json','reference_events.json','reference_admissions.json','zone_counter.py']:
 shutil.copyfile(OLD/'input'/name,ROOT/'input'/name)
e=PROJECT/'pynq_rot192_eval_20261029';cases=[]
for mode in ['FP32','QDQ','actual_O8']:
 folder=e/('board_delivery/results_v2/original' if mode=='actual_O8' else 'delivery/results/quality_v2/original/'+mode)
 if mode=='actual_O8':metrics=next(r['metrics'] for r in load(e/'board_delivery/results_v2/record.json')['scenes'] if r['scene']=='original')
 else:metrics=[r for r in load(e/'delivery/results/quality_v2/video_metrics.json') if r['scene']=='original' and r['mode']==mode]
 selected=next(r for r in metrics if r['counter']=='handoff_events')
 summary=ROOT/'input'/(mode+'_summary.json');summary.write_text(json.dumps([selected],indent=2)+'\n')
 row={'condition':mode,'group':'fixed192rot90seed26_three_numeric_implementations','size':192,'seed':26,
   'raw_file':str((folder/'raw_predictions.json.gz').resolve()),'trace_file':str((folder/'stride5_counter_trace.json.gz').resolve()),
   'summary_file':str(summary.resolve())}
 for kind in ['raw','trace','summary']:row[kind+'_sha256']=sha(Path(row[kind+'_file']))
 cases.append(row)
protocol=load(OLD/'protocol/audit_v1.json');protocol.update({'status':'FROZEN_BEFORE_FIXED_ROT192_IMPLEMENTATION_EVENT_DIAGNOSIS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'caches':cases,'input_sha256':{f.name:sha(f) for f in (ROOT/'input').iterdir() if f.is_file()},
 'reference_boxes_are_development640_model_outputs_not_GT':True,'actual_model_count_regression':[10,11,11],
 'no_new_network_forwards':True,'source_used_for_development':True,'whole_goal_complete':False})
(ROOT/'protocol/audit_v1.json').write_text(json.dumps(protocol,indent=2)+'\n')
text=(OLD/'tools/run_audit.py').read_text(encoding='utf-8');text=text.replace('len(allcases)==54 and casepaths==162 and referencerows==27*2*581','len(allcases)==6 and casepaths==18 and referencerows==3*2*581')
text=text.replace('ALL27_CACHES2_FIXED_IOU_LEVELS162_DIAGNOSTIC_ORACLE_PATHS_COMPLETE','THREE_FIXED_NUMERIC_IMPLEMENTATIONS_SIX_CASES18_REFERENCE_CONDITIONED_PATHS_COMPLETE')
text=text.replace("'cached_conditions':27","'cached_conditions':3").replace("'counter_oracle_paths':162","'counter_oracle_paths':18")
file=ROOT/'tools/run_audit.py';file.write_text(text,encoding='utf-8',newline='\n');ast.parse(text)
verify=(OLD/'tools/verify_independent.py').read_text(encoding='utf-8');index=verify.index('assert checks==54 and oracles==162');verify=verify[:index]
verify+='''assert checks==6 and oracles==18 and rows_checked==3486 and assignments==4296
result={'status':'ALL6_ROT192_IMPLEMENTATION_CASES3486_REFERENCE_ROWS4296_ASSOCIATIONS_AND18_COUNTER_PATHS_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'cases':checks,'reference_case_rows':rows_checked,'assignment_problems':assignments,'oracle_paths':oracles,
 'table':fulltable,'reference_is_independent_GT':False,'new_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
file=ROOT/'results/independent_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\\n')
print(json.dumps(result))
'''
(ROOT/'tools/verify_independent.py').write_text(verify,encoding='utf-8',newline='\n')
(ROOT/'计划与验收.md').write_text('''# 固定192模型未计事件定位

只读已核对的FP32、QDQ和实际O8三组原片缓存，定位11与人工总数12仍不一致的原因。沿用581个开发640框、12条参考轨迹与既定IoU0.5／0.3关联，以及原覆盖／框中心／跟踪确认辅助路径；不把它们称为独立GT。

全部三数值条件均保留。独立复算关联与计数，按源像素查看剩余未对应轨迹及阶段差异，决定下一步应补数据、训练还是改时序。不得用辅助轨迹直接作为身份真值，不为凑12放宽边界或选门限。

本轮无新模型推理、训练或板端动作，服务于固定192性能完成后的算法质量诊断。
''',encoding='utf-8')
print(json.dumps({'phase':str(ROOT),'conditions':3,'cases':6,'oracle_paths':18,'new_model_forwards':0}))
