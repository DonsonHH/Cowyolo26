from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,difflib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;PHASE=PROJECT/'causal_photo_20261030'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
phase=load(PHASE/'results/final_review.json')
for row in phase['documents']:assert sha(row['path'])==row['sha256']
previous=load(ROOT/'results/overview_review_20261030_v6.json');overview=PROJECT/'研究阶段总结_20261030.md'
assert sha(overview)==previous['document']['sha256']
latest='''最新完成[因果抓拍的六次真实O8／ARM对照](<C:/Users/Donson/Documents/ChatGPT/奶牛/causal_photo_20261030/因果抓拍实机结果与不采用决定.md>)：2309次前台、39次实际身份查询及69次服务器Torch参考均复核。计数10／10／10／10／9／9；两次因果JPEG环为4.834／4.796FPS、253／281帧迟到，最长身份完成74.94／80.89秒，故不采用该组合策略。JPEG读取平均46–48ms、选择约0.23ms；四后台均只接受同一f9790候选，未证明身份收益。59个照片面板全部查看，7字面事件配对与25未配对记录、六帧稳态／七帧瞬时及队列副本均保留。只读删除探针定位特定入口缺帧会使10→9，未修改规则；独立逐事件／永久身份仍待补，下一步优先实际输入取得、缓冲与掉帧稳定性。'''
paths=[PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',overview]
snapshot=ROOT/'evidence/causal_photo_entrypoints_before';snapshot.mkdir(exist_ok=False);updates=[];old_overview=None
for i,f in enumerate(paths):
 before=sha(f);s=f.read_text(encoding='utf-8');backup=snapshot/(str(i)+'_'+f.name);backup.write_bytes(f.read_bytes())
 mark='最新完成[新旧O8的11／10差异诊断]';assert s.count(mark)==1
 s=s.replace(mark,latest+'\n\n前一确认阶段：[新旧O8的11／10差异诊断]',1)
 if f!=overview:s=s.replace('更新：2026年10月29日。','更新：2026年10月30日。',1)
 if f==overview:
  old_overview=backup.read_text(encoding='utf-8')
  old='**当前结论：同一PYNQ-Z2已实际完成新mosaic0.5检测、ARM计数、实时照片处理及身份检索，六次公开回放周期运行平均吞吐范围4.949–5.000FPS。新模型完整实机原片10／人工12、反向3／6；旧模型分别11和1／6，存在质量取舍，未默认替换。永久身份真值、独立通行评价和真实相机／耳标仍缺，论文可继续推进，完整现场效果尚未证明。**'
  new='**当前结论：同一PYNQ-Z2已实际运行YOLO26n检测、ARM计数和身体身份检索。192完整实机原片10／人工12、反向3／6；最新六次周期回放计数为10／10／10／10／9／9。新增因果JPEG缓存吞吐4.796–4.834FPS且最长身份完成80.89秒，未采用；此前约5FPS证据保留为特定就绪输入和运行条件的结果。独立通行／永久身份、真实相机和耳标仍缺，论文可继续推进，现场有效性尚未证明。**'
  assert s.count(old)==1;s=s.replace(old,new)
  old='后台照片还暴露出另一问题：计数完成时才取当帧框，部分身体已经到画面边缘或与邻牛重叠。后续可以研究**只利用当前及过去帧**的质量选择与压缩高分辨率缓冲，比较单帧、固定K帧与因果质量选择；不能用未来帧或真实身份标签参与在线选择。'
  new='后台照片的因果选择现已实际比较：原完整轨迹10事件中7次改选更早照片，边界代理改善，但清晰度有3升4降；实机两组各7次改选仍未新增接受候选。每帧JPEG读取平均46–48ms，远大于约0.23ms几何选择，因果组253／281迟到及75–81秒身份等待不支持采用。全部59面板与未配对记录保留，不能凭几何分数证明身份更正确。[抓拍选择与完整时序代价](<C:/Users/Donson/Documents/ChatGPT/奶牛/causal_photo_20261030/因果抓拍实机结果与不采用决定.md>)\n\n本轮还观察到9次计数：二轮当帧丢失入口段使临时轨迹5只有1次A观察；二轮独占漏9515使21最长只有2次。旧轨迹只删9515的计数探针也从10变9，只删10440仍10；这是事后只读诊断，不是跟踪完整重跑或部署特判。平均接近5FPS仍可能丢掉决定计数的入口证据。'
  assert s.count(old)==1;s=s.replace(old,new)
  old='3. 比较当帧抓拍与因果质量选择，单独测真实检测框造成的身份损失；对未登记牛保持拒识。'
  new='3. 当帧与因果抓拍已实机比较，该JPEG环组合不采用。先拆开高分辨率输入取得、缓存／队列复制、选帧与身份计算，保持这些成本在相应计时范围内；再用固定同事件照片与带永久ID新会话验证收益，对未登记牛保持拒识。'
  assert s.count(old)==1;s=s.replace(old,new)
  old='4. 在同板约5FPS基础上做重复／长时、相同负载的调度实验，明确前台允许迟到和后台允许等待，而不是事后挑最优一次。'
  new='4. 两阶段周期重复已暴露前台9／10波动及后台饥饿。继续掉帧与确认／稳定入口的独立分解、输入代价受控的相同负载和长时实验，明确允许迟到与等待上限，不以少触发任务或事后挑一轮作为优胜。'
  assert s.count(old)==1;s=s.replace(old,new)
  old='前一实机阶段结束时已读取3个父任务和4个身份子任务，均正常终态且PID消失，并记录SSH／Jupyter及O8状态。本轮只读缓存与运行服务器CPU控制，没有新增板端时序或连接状态测量；全局运行环境、跟踪源码与默认模型未替换。'
  new='本轮因果抓拍父任务、四身份子任务与采集进程均正常终态且PID消失，SSH／Jupyter、原O8 bit及共享锁已重读；服务器130642完成0:0。2309实际raw、13007观察、39实际照片／输入／检索、69次Torch参考与59面板均核对。全局运行环境、跟踪源码与默认策略未替换，因果缓存不采用；新计数9／10与旧10等结果全部保留。'
  assert s.count(old)==1;s=s.replace(old,new)
 f.write_text(s,encoding='utf-8');updates.append({'path':str(f.resolve()),'before_sha256':before,'after_sha256':sha(f),'before_snapshot':str(backup.resolve())})
record={'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':updates,'phase_final_review_sha256':sha(PHASE/'results/final_review.json'),'whole_goal_complete':False}
file=ROOT/'results/causal_photo_entrypoint_updates_20261030.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
# Preserve all earlier numeric record bindings, and append this stage only after checking them.
for row in previous['current_numeric_record_files']:assert sha(row['path'])==row['sha256']
links=[];s=overview.read_text(encoding='utf-8')
for match in re.finditer(r'\]\(<([^>]+)>\)',s):assert Path(match[1]).exists();links.append(match[1])
review={**previous,'status':'WHOLE_OVERVIEW_MANUAL_CLAIMS_AND_CURRENT_PHASE_NUMBERS_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'document':{'path':str(overview.resolve()),'sha256':sha(overview)},'previous_review_preserved':{'path':str((ROOT/'results/overview_review_20261030_v6.json').resolve()),'sha256':sha(ROOT/'results/overview_review_20261030_v6.json')},
 'entrypoint_update_evidence':{'path':str(file.resolve()),'sha256':sha(file)},'local_links_checked':len(links),'local_links':links,
 'current_numeric_record_files':previous['current_numeric_record_files']+[{'path':str((PHASE/'results/final_review.json').resolve()),'sha256':sha(PHASE/'results/final_review.json')}],
 'new_training_updates':0,'new_model_forwards':2441,'new_board_actions_performed':True,'current_stage_actual_O8_query_forwards':2309,'current_stage_actual_identity_query_forwards':39,
 'current_stage_CPU_Torch_reference_forwards':69,'new_independent_test':False,'whole_goal_complete':False,
 'overview_changed_lines_manually_reviewed':list(difflib.unified_diff(old_overview.splitlines(),s.splitlines(),lineterm='')),
 'current_stage_review_topics':['all9_or10_counts_preserved','read_io_not_scoring_is_largest_measured_increment','69Torch_reference_not_identity_truth','59panels_viewed','six_vs_seven_ring_and_async_copy','25unmatched_records','single_frame_deletion_diagnostic_not_full_replay','all_own_processes_terminal','current_stage_policy_not_adopted']}
f=ROOT/'results/overview_review_20261030_v7.json';assert not f.exists();f.write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
# Summary file is a mutable entrance, all older phase documents remain frozen.
f=ROOT/'Review与当前状态.md';s=f.read_text(encoding='utf-8');new='2026年10月30日当前综合复核：'+latest+' 本轮自审与总览绑定见[第7版复核记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/research_synthesis_20261027/results/overview_review_20261030_v7.json>)。独立评价、永久身份和真实传感器仍待补；下方为前阶段历史。\n\n'
assert s.startswith('# 研究总览Review与当前状态\n\n');s=s.replace('# 研究总览Review与当前状态\n\n','# 研究总览Review与当前状态\n\n'+new,1);f.write_text(s,encoding='utf-8')
print(json.dumps({'entrypoints_updated':4,'overview_links':len(links),'previous_numeric_bindings_unchanged':True,'whole_goal_complete':False}))
