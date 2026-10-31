from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,difflib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;PHASE=PROJECT/'async_highres_20261030'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
phase=load(PHASE/'results/final_review.json');previous=load(ROOT/'results/overview_review_20261030_v8.json');overview=PROJECT/'研究阶段总结_20261030.md'
assert sha(overview)==previous['document']['sha256']
for row in previous['current_numeric_record_files']:assert sha(row['path'])==row['sha256']
for row in phase['documents']:assert sha(row['path'])==row['sha256']
latest='''最新完成[有界输入四次真实O8／ARM对照](<C:/Users/Donson/Documents/ChatGPT/奶牛/async_highres_20261030/有界输入四次实机结果与下一步.md>)：异步4.821／4.911FPS、串行4.515／4.439FPS，四次计数均10／人工12。1465实际raw、8597观察／8路径、784释放后源读取及40真实身份作业均复算；580时刻实际读取／模型重叠，前台输入等待约63–65→1.4–1.6ms，但模型阶段拉长、异步170／363迟到和61–79秒后台完成仍未解决。70次Torch参考／80检索决定与板端一致，40面板查看，两个接受预测是相同f9790重复图。6字面配对与28未配对保留，完整性预检／页缓存范围明确。保留研究候选、不替换默认；下一步优先同输入下的后台预算与低优先级调度，以及独立通行／永久身份评价。'''
paths=[PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',overview]
snapshot=ROOT/'evidence/async_highres_entrypoints_before';snapshot.mkdir(exist_ok=False);updates=[];oldtext=None
for i,f in enumerate(paths):
 before=sha(f);text=f.read_text(encoding='utf-8');backup=snapshot/(str(i)+'_'+f.name);backup.write_bytes(f.read_bytes())
 if f!=overview:
  mark='最新完成[高分JPEG取得成本的256条件／138次实机前向诊断]';assert text.count(mark)==1;text=text.replace(mark,latest+'\n\n前一输入诊断阶段：[高分JPEG取得成本的256条件／138次实机前向诊断]',1)
 else:
  oldtext=text;section=text.index('## 1. 两个方向可以这样定义')
  opening='''# 奶牛通道计数与耳标异常身份辅助：从想法到实机与论文

更新：2026年10月30日。本文按问题、已有证据、评价和下一步组织；逐次历史实验见[研究进度](<C:/Users/Donson/Documents/ChatGPT/奶牛/研究进度.md>)，原报告及失败记录均保留。

**当前结论：检测、ARM计数和身体身份检索已在同一PYNQ-Z2实际运行。新192模型完整实机原片计数10／人工12、反向3／6；最新有界输入四次也均计10。异步吞吐4.821–4.911FPS，但前台仍迟到、最长身份完成61–79秒，因此保留研究候选，默认未替换。独立事件／永久身份和真实相机／RFID仍待补，现场有效性和论文贡献尚未证明。**

| 目前已验证 | 结果与实际范围 | 仍需解决 |
| --- | --- | --- |
| 192检测与计数 | 同O8完整视频及多次周期回放；新模型10／人工12、旧模型11 | 跨来源质量、入口缺帧、独立事件参考 |
| 两网络同板 | ARM身体网络、真实裁剪／预处理／图库检索已经执行 | 永久身份正确率、未登记牛风险、实际RF关联 |
| 有界高分输入 | 异步4.821／4.911，对照串行4.515／4.439FPS | 170／363迟到，后台最长61.17／79.17秒 |
| 256与320同O8 | 各8向量平均235.55／370.93ms | 尚不能据此承诺含输入／跟踪／后台的5FPS |

本轮[完整四次实机报告与40张照片](<C:/Users/Donson/Documents/ChatGPT/奶牛/async_highres_20261030/有界输入四次实机结果与下一步.md>)已自审：1465实际检测输出、784异步源记录和70次Torch参考均核对。读取与计算实际重叠，前台等待缩短；检测阶段变慢、后台仍饥饿，吞吐改善并未自动变成完整实时或身份收益。低分输入是已就绪回放，计时外完整性检查读过源JPEG；正式周期只用已释放数据，现场双流／曝光编码未证明。

'''
  text=opening+text[section:]
  mark='新mosaic0.5权重已完成两轮顺序反转的6次同板实测'
  insert='''最新一轮专门检验高分辨率读取能否和检测重叠，四次均有实际身份后台，数据如下。表中迟到以已处理时刻为分母，跳过另计；完成时间含当前JPEG等待、选帧及入队。每次仍为392时隙／78.4秒，两个重复不代表独立会话。

| 轮次 | 高分输入 | 处理／392 | 跳过 | >200ms | FPS | 计数／人工12 | 最长身份完成秒 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 串行 | 354 | 38 | 353 | 4.515 | 10 | 76.25 |
| 1 | 有界异步 | 378 | 14 | 170 | 4.821 | 10 | 61.17 |
| 2 | 有界异步 | 385 | 7 | 363 | 4.911 | 10 | 79.17 |
| 2 | 串行 | 348 | 44 | 347 | 4.439 | 10 | 79.08 |

两组均逐帧读取并校验JPEG，异步源会读前台跳过的时隙；不是同读取次数消融。1465实际raw、8597观察、8计数路径、784源记录及40身份任务通过复算，580个时刻真实重叠。输入等待缩到1.4–1.6ms，模型阶段却由143–145ms拉长至166–182ms；不能把等待减少全部算作系统收益。异步只保留为研究候选。两次接受均为相同f9790照片，无永久身份真值。[完整范围和原始数据](<C:/Users/Donson/Documents/ChatGPT/奶牛/async_highres_20261030/有界输入四次实机结果与下一步.md>)

下表保留此前高分照片按需读取的同模型阶段，输入成本和工作负载与本轮不同。

'''
  assert text.count(mark)==1;text=text.replace(mark,insert+'此前，新mosaic0.5权重已完成两轮顺序反转的6次同板实测',1)
  old='3. JPEG环组合不采用，输入取得与拷贝诊断现已完成。接下来比较串行读取与有界输入生产者，数据只能在该帧释放后取得，完整释放至计数包含等待／缓存／复制；再用固定同事件照片与带永久ID新会话验证身份收益，对未登记牛保持拒识。'
  new='3. 有界输入与计算已经实际重叠，吞吐改善但后台仍饥饿。下一步固定同一生产者、模型与选择规则，比较现有空闲门控、低优先级后台或明确服务预算，统计前台截止时间、后台完成与实际队列；再用固定同事件照片和带永久ID新会话验证身份收益。'
  assert text.count(old)==1;text=text.replace(old,new)
  old='下一步验证按正式释放时刻取得输入并与计算重叠的有界生产者。'
  new='后续有界生产者的四次实机现已完成：能真实重叠并缩短等待，但资源竞争及后台等待仍需解决。'
  assert text.count(old)==1;text=text.replace(old,new)
  old='本轮还观察到9次计数：'
  assert text.count(old)==1;text=text.replace(old,'此前一轮还观察到9次计数：')
  start=text.index('同板部署可行性已经从估算推进到实际运行。');end=text.index('\n\n总体研究目标继续',start)
  text=text[:start]+'''同板部署可行性已有真实记录。最新四次有界输入的父任务、四身份子任务、生产线程和采集进程均终态，原O8、锁、SSH与Jupyter已核查；参考作业130643完成0:0。1465实际raw、8597观察、40照片／输入／检索、784源记录和70Torch参考／80检索决定均核对。CRLF首次提交拒绝只作LF修复，未改输入或门限；其余历史失败均留档。默认策略未替换，当前四次10、此前9／10以及旧模型11等结果分别保留。''' +text[end:]
 f.write_text(text,encoding='utf-8');updates.append({'path':str(f.resolve()),'before_sha256':before,'after_sha256':sha(f),'before_snapshot':str(backup.resolve())})
updatefile=ROOT/'results/async_highres_entrypoint_updates_20261030.json';assert not updatefile.exists();updatefile.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':updates,'historical_header_narratives_retained_in_progress_and_previous_snapshot':True,'phase_final_review_sha256':sha(PHASE/'results/final_review.json'),'whole_goal_complete':False},indent=2)+'\n',encoding='utf-8')
text=overview.read_text(encoding='utf-8');links=[]
for m in re.finditer(r'\]\(<([^>]+)>\)',text):assert Path(m[1]).exists();links.append(m[1])
review={**previous,'status':'WHOLE_OVERVIEW_MANUAL_CLAIMS_AND_CURRENT_PHASE_NUMBERS_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'document':{'path':str(overview.resolve()),'sha256':sha(overview)},
 'previous_review_preserved':{'path':str((ROOT/'results/overview_review_20261030_v8.json').resolve()),'sha256':sha(ROOT/'results/overview_review_20261030_v8.json')},
 'entrypoint_update_evidence':{'path':str(updatefile.resolve()),'sha256':sha(updatefile)},
 'board_terminal_read':{'path':str((PHASE/'evidence/final_board_read.json').resolve()),'sha256':sha(PHASE/'evidence/final_board_read.json')},
 'current_numeric_record_files':previous['current_numeric_record_files']+[{'path':str((PHASE/'results/final_review.json').resolve()),'sha256':sha(PHASE/'results/final_review.json')}],
 'new_model_forwards':1595,'new_model_forward_breakdown':{'O8_timed':1465,'O8_qualification':8,'O8_warmups':8,'ARM_queries':40,'ARM_warmups':4,'CPU_Torch_queries':40,'CPU_Torch_gallery':30},
 'new_board_actions_performed':True,'current_stage_actual_O8_query_forwards':1465,'current_stage_actual_identity_query_forwards':40,'current_stage_CPU_Torch_reference_forwards':70,
 'current_stage_read_conditions':None,'current_stage_released_producer_source_records':784,'new_periodic_counter_or_identity_run':True,'full_periodic_5FPS_target_fixed':False,
 'same_board_execution_scope':'Current four actual O8 and ARM runs with release-gated JPEG thread; ready lowres replay, simulated RFID, no live camera or identity accuracy proof.',
 'current_stage_review_topics':['all4count10_not_human12','throughput_improvement_and170_363_late_both_retained','61_79second_backend_wait','784released_reads580positive_overlap','40panels_and70Torch80decisions','6literalpairs28unmatched','preflight_cache_scope','bounded_payload_not_RAM','CRLF_repair_only','default_unchanged','overview_header_simplified_with_history_preserved'],
 'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False,
 'local_links_checked':len(links),'local_links':links,'overview_changed_lines_manually_reviewed':list(difflib.unified_diff(oldtext.splitlines(),text.splitlines(),lineterm='')),
 'current_review_scope':'Entire current overview with clarified current-vs-historical performance and preserved previous numeric bindings;assistant self-review not independent human',
 'current_overview_review_completed_UTC':datetime.now(timezone.utc).isoformat()}
assert sum(review['new_model_forward_breakdown'].values())==1595
f=ROOT/'results/overview_review_20261030_v9.json';assert not f.exists();f.write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
f=ROOT/'Review与当前状态.md';s=f.read_text(encoding='utf-8');mark='# 研究总览Review与当前状态\n\n';assert s.startswith(mark)
s=s.replace(mark,mark+'2026年10月30日当前有界输入复核：'+latest+' 总览当前开头已收紧为状态表，历史叙述保留在进度与快照；见[第9版复核](<C:/Users/Donson/Documents/ChatGPT/奶牛/research_synthesis_20261027/results/overview_review_20261030_v9.json>)。下方保留历史。\n\n',1);f.write_text(s,encoding='utf-8')
print(json.dumps({'updated_entrypoints':4,'overview_lines':len(text.splitlines()),'overview_links':len(links),'numeric_bindings':len(review['current_numeric_record_files']),'new_forwards':1595,'whole_goal_complete':False}))
