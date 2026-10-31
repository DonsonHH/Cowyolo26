from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,difflib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;PHASE=PROJECT/'input_cost_20261030'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
phase=load(PHASE/'results/final_review.json');previous=load(ROOT/'results/overview_review_20261030_v7.json')
for row in phase['documents']:assert sha(row['path'])==row['sha256']
for row in previous['current_numeric_record_files']:assert sha(row['path'])==row['sha256']
overview=PROJECT/'研究阶段总结_20261030.md';assert sha(overview)==previous['document']['sha256']
latest='''最新完成[高分JPEG取得成本的256条件／138次实机前向诊断](<C:/Users/Donson/Documents/ChatGPT/奶牛/input_cost_20261030/高分输入取得成本与下一步.md>)：O8后未驻留bytes读取42.85ms、预读后3.89ms；readinto为44.37／2.26ms，另冻结为不可变JPEG需约3.82ms，不能只报读取的小幅节省。128个冷条件均有未驻留页与设备读取增加，128个热条件全部驻留且设备增量0，支持存储路径为主要成本。v1缺少进程I/O计数器而0测速／0前向，v2用实际页驻留及整设备统计、没有冒充进程级读盘量；全部raw精确匹配。没有新周期计数或身份运行，原完整5FPS检查仍红、默认不变；下一步在完整计时内验证有界输入生产者与检测重叠，不能把预读成本搬出去。'''
paths=[PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',overview]
folder=ROOT/'evidence/input_cost_entrypoints_before';folder.mkdir(exist_ok=False);updates=[];oldtext=None
for i,f in enumerate(paths):
 before=sha(f);s=f.read_text(encoding='utf-8');backup=folder/(str(i)+'_'+f.name);backup.write_bytes(f.read_bytes())
 marker='最新完成[因果抓拍的六次真实O8／ARM对照]';assert s.count(marker)==1;s=s.replace(marker,latest+'\n\n前一抓拍阶段：[因果抓拍的六次真实O8／ARM对照]',1)
 if f==overview:
  oldtext=backup.read_text(encoding='utf-8')
  marker='本轮还观察到9次计数：'
  extra='''输入取得成本已进一步拆开：16均匀来源、两次反转重复的256读取条件中，冷文件42–45ms、热文件2–4ms；128实际O8前向及8准入／2预热全部raw对应旧实机。页驻留和设备计数支持存储等待解释，readinto后额外不可变复制约3.82ms，不能用较快read调用代替完整队列语义。没有新的周期／身份并发，原5FPS门禁仍红；下一步验证按正式释放时刻取得输入并与计算重叠的有界生产者。[输入成本与作用范围](<C:/Users/Donson/Documents/ChatGPT/奶牛/input_cost_20261030/高分输入取得成本与下一步.md>)

'''
  assert s.count(marker)==1;s=s.replace(marker,extra+marker)
  old='3. 当帧与因果抓拍已实机比较，该JPEG环组合不采用。先拆开高分辨率输入取得、缓存／队列复制、选帧与身份计算，保持这些成本在相应计时范围内；再用固定同事件照片与带永久ID新会话验证收益，对未登记牛保持拒识。'
  new='3. JPEG环组合不采用，输入取得与拷贝诊断现已完成。接下来比较串行读取与有界输入生产者，数据只能在该帧释放后取得，完整释放至计数包含等待／缓存／复制；再用固定同事件照片与带永久ID新会话验证身份收益，对未登记牛保持拒识。'
  assert s.count(old)==1;s=s.replace(old,new)
  marker='本轮因果抓拍父任务、四身份子任务与采集进程均正常终态且PID消失，SSH／Jupyter、原O8 bit及共享锁已重读；服务器130642完成0:0。'
  replacement='前一抓拍阶段父、四身份子任务与采集进程均正常终态且PID消失；当前输入成本v1在0数据时失败、v2完成138次实际O8前向，两个PID均消失，原O8、共享锁、SSH／Jupyter已核查。服务器130642为此前身份参考，完成0:0。'
  assert s.count(marker)==1;s=s.replace(marker,replacement)
 f.write_text(s,encoding='utf-8');updates.append({'path':str(f.resolve()),'before_sha256':before,'after_sha256':sha(f),'before_snapshot':str(backup.resolve())})
updatefile=ROOT/'results/input_cost_entrypoint_updates_20261030.json';assert not updatefile.exists();updatefile.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':updates,'phase_final_review_sha256':sha(PHASE/'results/final_review.json'),'whole_goal_complete':False},indent=2)+'\n',encoding='utf-8')
links=[];text=overview.read_text(encoding='utf-8')
for m in re.finditer(r'\]\(<([^>]+)>\)',text):assert Path(m[1]).exists();links.append(m[1])
review={**previous,'status':'WHOLE_OVERVIEW_MANUAL_CLAIMS_AND_CURRENT_PHASE_NUMBERS_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'document':{'path':str(overview.resolve()),'sha256':sha(overview)},
 'previous_review_preserved':{'path':str((ROOT/'results/overview_review_20261030_v7.json').resolve()),'sha256':sha(ROOT/'results/overview_review_20261030_v7.json')},
 'entrypoint_update_evidence':{'path':str(updatefile.resolve()),'sha256':sha(updatefile)},
 'board_terminal_read':{'path':str((PHASE/'evidence/collection_v2.json').resolve()),'sha256':sha(PHASE/'evidence/collection_v2.json')},
 'current_numeric_record_files':previous['current_numeric_record_files']+[{'path':str((PHASE/'results/final_review.json').resolve()),'sha256':sha(PHASE/'results/final_review.json')}],
 'new_model_forwards':138,'new_model_forward_breakdown':{'actual_O8_measured':128,'actual_O8_qualification':8,'actual_O8_warmup':2},
 'new_board_actions_performed':True,'current_stage_actual_O8_query_forwards':128,'current_stage_actual_identity_query_forwards':0,'current_stage_CPU_Torch_reference_forwards':0,
 'current_stage_read_conditions':256,'new_periodic_counter_or_identity_run':False,'full_periodic_5FPS_target_fixed':False,
 'same_board_execution_scope':'Historical joint evidence retained; current stage O8 and input-cost microbenchmark only.',
 'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False,
 'current_stage_review_topics':['all8groups_and16sources_preserved','128cold_residency_and_device_controls','128hot_cases_zero_device_increment','138actual_O8_parity','v1_missing_kernel_counter_zero_data_preserved','mutable_buffer_freeze_and_pickle_not_IPC','microbench_not_full_periodic_fix','original_feedback_still_red','known_O8_and_services_retained'],
 'local_links_checked':len(links),'local_links':links,
 'overview_changed_lines_manually_reviewed':list(difflib.unified_diff(oldtext.splitlines(),text.splitlines(),lineterm='')),
 'current_review_scope':'whole_existing_overview_with_unchanged_evidence_bindings_plus_input_cost_revisions;assistant_self_review_not_independent_human',
 'current_overview_review_completed_UTC':datetime.now(timezone.utc).isoformat()}
f=ROOT/'results/overview_review_20261030_v8.json';assert not f.exists();f.write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
f=ROOT/'Review与当前状态.md';s=f.read_text(encoding='utf-8');marker='# 研究总览Review与当前状态\n\n';assert s.startswith(marker)
s=s.replace(marker,marker+'2026年10月30日当前输入成本复核：'+latest+' 见[第8版总览复核](<C:/Users/Donson/Documents/ChatGPT/奶牛/research_synthesis_20261027/results/overview_review_20261030_v8.json>)。以下保留此前阶段。\n\n',1);f.write_text(s,encoding='utf-8')
print(json.dumps({'entrypoints':4,'current_total_new_forwards':138,'numeric_bindings':len(review['current_numeric_record_files']),'overview_links':len(links),'whole_goal_complete':False}))
