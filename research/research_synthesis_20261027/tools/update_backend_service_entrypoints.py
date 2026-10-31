from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,difflib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;PHASE=PROJECT/'backend_service_20261030'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
phase=load(PHASE/'results/final_review.json');previous=load(ROOT/'results/overview_review_20261030_v9.json');overview=PROJECT/'研究阶段总结_20261030.md'
assert sha(overview)==previous['document']['sha256']
for r in previous['current_numeric_record_files']:assert sha(r['path'])==r['sha256']
for r in phase['documents']:assert sha(r['path'])==r['sha256']
latest='''最新完成[后台服务四次实机与串口恢复复核](<C:/Users/Donson/Documents/ChatGPT/奶牛/backend_service_20261030/后台服务四次实机结果与取舍.md>)：持续后台最长身份完成2.56／2.19秒，对照暂停组52.51／51.40秒；但吞吐4.617／4.273FPS低于4.821／4.987FPS，四次计数10／9／10／10，故不默认采用。1466实际raw、8598观察／8路径、1568源记录、39照片／输入／真实特征和69次Torch参考已复核；前台边界CPU tick支持后台获得服务。实验后网口NO-CARRIER，原20MB整包仍在板上未本机下载；经串口恢复记录和真实特征，并用解码像素SHA重建／查看全部39图，没有重跑实验。当前串口与板上服务可用、外部SSH未恢复，完整归档待网线接回；下一步需明确服务预算并补独立事件／永久身份。'''
paths=[PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',overview]
snap=ROOT/'evidence/backend_service_entrypoints_before';snap.mkdir(exist_ok=False);updates=[];oldtext=None
for i,f in enumerate(paths):
 before=sha(f);text=f.read_text(encoding='utf-8');backup=snap/(str(i)+'_'+f.name);backup.write_bytes(f.read_bytes())
 if f!=overview:
  marker='最新完成[有界输入四次真实O8／ARM对照]';assert text.count(marker)==1;text=text.replace(marker,latest+'\n\n前一有界输入阶段：[有界输入四次真实O8／ARM对照]',1)
 else:
  oldtext=text
  a='**当前结论：检测、ARM计数和身体身份检索已在同一PYNQ-Z2实际运行。新192模型完整实机原片计数10／人工12、反向3／6；最新有界输入四次也均计10。异步吞吐4.821–4.911FPS，但前台仍迟到、最长身份完成61–79秒，因此保留研究候选，默认未替换。独立事件／永久身份和真实相机／RFID仍待补，现场有效性和论文贡献尚未证明。**'
  b='**当前结论：检测、ARM计数和身体身份检索已在同一PYNQ-Z2运行。新192模型完整实机原片10／人工12、反向3／6；最新调度四次计数10／9／10／10。持续后台将最长身份完成降至2.2–2.6秒，却使吞吐降至4.27–4.62FPS，默认未替换。网口中断后已用串口复核数据，原完整包仍待下载。独立事件／永久身份、真实相机／RFID和稳定前后台性能仍未完成，论文贡献尚未证明。**'
  assert text.count(a)==1;text=text.replace(a,b)
  a='| 有界高分输入 | 异步4.821／4.911，对照串行4.515／4.439FPS | 170／363迟到，后台最长61.17／79.17秒 |'
  b=a+'\n| 后台服务取舍 | 持续后台2.56／2.19秒，暂停52.51／51.40秒 | 持续吞吐4.617／4.273FPS，一轮计数9 |'
  assert text.count(a)==1;text=text.replace(a,b)
  marker='本轮[完整四次实机报告与40张照片]';assert text.count(marker)==1
  text=text.replace(marker,latest+'\n\n前一输入阶段的[完整四次实机报告与40张照片]',1)
  text=text.replace('已自审：1465实际检测输出','已自审：1465实际检测输出',1)
  marker='最新一轮专门检验高分辨率读取能否和检测重叠，四次均有实际身份后台，数据如下。'
  intro='''最新调度对照固定相同有界输入、模型和选择规则，仅切换是否按帧暂停后台。两组均有CPU边界仪器，当前暂停组才是直接基线。四次结果为：

| 轮次 | 后台策略 | 处理／392 | 跳过 | >200ms | FPS | 计数／人工12 | 最长身份完成秒 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 按帧暂停 | 378 | 14 | 191 | 4.821 | 10 | 52.51 |
| 1 | nice10持续 | 362 | 30 | 177 | 4.617 | 9 | 2.56 |
| 2 | nice10持续 | 335 | 57 | 304 | 4.273 | 10 | 2.19 |
| 2 | 按帧暂停 | 391 | 1 | 187 | 4.987 | 10 | 51.40 |

持续后台降低排队，却在两轮都降低吞吐、提高P95，第一轮还少计1次。CPU边界记录支持它在前台期间实际得到CPU；10／9实际触发任务、不同照片与状态不能当完全相同负载。全部39图像素／输入、69次Torch参考及78候选／拒识决定已核验，没有永久身份正确率主张。网口断开后以串口和板端只读审计恢复证据；原包留板待下载，不冒充完整归档完成。[完整调度报告及恢复说明](<C:/Users/Donson/Documents/ChatGPT/奶牛/backend_service_20261030/后台服务四次实机结果与取舍.md>)

'''
  assert text.count(marker)==1;text=text.replace(marker,intro+'前一轮专门检验高分辨率读取能否和检测重叠，四次均有实际身份后台，数据如下。')
  a='3. 有界输入与计算已经实际重叠，吞吐改善但后台仍饥饿。下一步固定同一生产者、模型与选择规则，比较现有空闲门控、低优先级后台或明确服务预算，统计前台截止时间、后台完成与实际队列；再用固定同事件照片和带永久ID新会话验证身份收益。'
  b='3. 全程低优先级后台对照已完成：等待降到约2秒，前台吞吐与一次计数退步，默认不采用。接下来明确前台迟到及身份完成上限，研究有服务预算的后台；以固定作业／照片作调度压力对照，同时保留完整真实触发链路和独立身份评价。'
  assert text.count(a)==1;text=text.replace(a,b)
  marker='同板部署可行性已有真实记录。';start=text.index(marker);end=text.index('\n\n总体研究目标继续',start)
  text=text[:start]+'''同板部署已有真实记录。最新四次后台对照的父任务、四身份子任务、打包及恢复审计进程均终态／消失；串口复核板上ssh／jupyter服务仍活动，网口NO-CARRIER，外部访问未恢复。原root打包时已读取O8状态，当前再次核对磁盘bit文件；非root XRT状态读取失败未冒充成功。1466raw在板端独立核对并回传哈希，本机39图像素／输入／实际特征核验，69次Torch参考及78检索决定一致；原20MB完整包尚未本机下载。恢复没有重跑、复位或修改IP，默认未替换。''' +text[end:]
 f.write_text(text,encoding='utf-8');updates.append({'path':str(f.resolve()),'before_sha256':before,'after_sha256':sha(f),'before_snapshot':str(backup.resolve())})
updatefile=ROOT/'results/backend_service_entrypoint_updates_20261030.json';assert not updatefile.exists();updatefile.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':updates,'phase_final_review_sha256':sha(PHASE/'results/final_review.json'),'original_full_archive_pending':True,'whole_goal_complete':False},indent=2)+'\n',encoding='utf-8')
text=overview.read_text(encoding='utf-8');links=[]
for m in re.finditer(r'\]\(<([^>]+)>\)',text):assert Path(m[1]).exists();links.append(m[1])
review={**previous,'status':'WHOLE_OVERVIEW_MANUAL_CLAIMS_AND_CURRENT_PHASE_NUMBERS_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'document':{'path':str(overview.resolve()),'sha256':sha(overview)},
 'previous_review_preserved':{'path':str((ROOT/'results/overview_review_20261030_v9.json').resolve()),'sha256':sha(ROOT/'results/overview_review_20261030_v9.json')},
 'entrypoint_update_evidence':{'path':str(updatefile.resolve()),'sha256':sha(updatefile)},
 'board_terminal_read':{'path':str((PHASE/'evidence/serial_final_recovery_state03.json').resolve()),'sha256':sha(PHASE/'evidence/serial_final_recovery_state03.json')},
 'current_numeric_record_files':previous['current_numeric_record_files']+[{'path':str((PHASE/'results/final_review.json').resolve()),'sha256':sha(PHASE/'results/final_review.json')}],
 'new_model_forwards':1594,'new_model_forward_breakdown':{'O8_timed':1466,'O8_qualification':8,'O8_warmups':8,'ARM_queries':39,'ARM_warmups':4,'CPU_Torch_queries':39,'CPU_Torch_gallery':30},
 'current_stage_actual_O8_query_forwards':1466,'current_stage_actual_identity_query_forwards':39,'current_stage_CPU_Torch_reference_forwards':69,
 'current_stage_released_producer_source_records':1568,'new_periodic_counter_or_identity_run':True,'full_periodic_5FPS_target_fixed':False,
 'same_board_execution_scope':'Current four real O8/ARM scheduling runs; results recovered via UART plus local source-pixel and numeric binding. Full original archive still on board; local services active, Ethernet no carrier.',
 'current_stage_review_topics':['all4counts10_9_10_10_retained','2second_backend_vs4_27_to4_62FPS_tradeoff','1832childCPU_ticks_not_layer_timing','39pixels_inputs_and69Torch78decisions','raw_onboard_audited_hash_binding_not_local_array_download','all39viewed_reconstructions30filebyte_same9pixel_same','4literalpairs31unmatched','extra_byte_normalization_failure_preserved_existing_gate','NO_CARRIER_not_IP_or_reboot','full_archive_pending_not_complete','unprivileged_XRT_and_sudo_n_failures_preserved'],
 'original_full_archive_downloaded':False,'external_board_services_recovered':False,'current_stage_recovery_new_forwards':0,
 'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False,
 'local_links_checked':len(links),'local_links':links,'overview_changed_lines_manually_reviewed':list(difflib.unified_diff(oldtext.splitlines(),text.splitlines(),lineterm='')),
 'current_review_scope':'Entire current overview with explicit full-archive pending and local-vs-board verification scope;assistant self-review not independent human',
 'current_overview_review_completed_UTC':datetime.now(timezone.utc).isoformat()}
assert sum(review['new_model_forward_breakdown'].values())==1594
f=ROOT/'results/overview_review_20261030_v10.json';assert not f.exists();f.write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
f=ROOT/'Review与当前状态.md';text=f.read_text(encoding='utf-8');marker='# 研究总览Review与当前状态\n\n';assert text.startswith(marker)
text=text.replace(marker,marker+'2026年10月30日当前后台服务复核：'+latest+' 见[第10版复核](<C:/Users/Donson/Documents/ChatGPT/奶牛/research_synthesis_20261027/results/overview_review_20261030_v10.json>)。下方保留此前阶段。\n\n',1);f.write_text(text,encoding='utf-8')
print(json.dumps({'updated_entrypoints':4,'overview_lines':len(overview.read_text(encoding='utf-8').splitlines()),'numeric_bindings':len(review['current_numeric_record_files']),'whole_goal_complete':False,'original_full_archive_pending':True}))
