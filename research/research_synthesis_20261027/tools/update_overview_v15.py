from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(label,path):return f'[{label}](<{(PROJECT/path).as_posix()}>)'

v=load(PROJECT/'identity_joint_pair_20261030/results/final_review.json');assert v['actual_ARM_total_forwards']==85 and not v['whole_goal_complete']
old=load(ROOT/'results/overview_review_20261030_v14.json');main=PROJECT/'研究阶段总结_20261030.md';assert sha(main)==old['document']['sha256']
cases=v['cases'];assert [c['identity_model']for c in cases]==['old','new','new','old']
reference=link('新旧身份模型四次同板对照','identity_joint_pair_20261030/新旧身份模型固定负载同板对照.md')
latest=f"2026年10月30日最新：{reference}已完成旧—新—新—旧四次固定10照片负载：旧模型均392／392、5.000FPS，新模型均390／392、4.974FPS，四次均计10／人工12，迟到分别80／69／67／76。后台每次都完成相同10个任务，新模型使用自己重新编码的同一30张图库；旧／新模型主阈值接受各{cases[0]['accepted_predictions']}／{cases[1]['accepted_predictions']}（／10，重复一致），没有永久身份正确率。完整原包、{v['actual_timed_O8_forwards']}份实际raw、40份照片／特征、20配对及四条完整关联重放已复核。新模型不据此默认替换。下一步先执行已固定的20ID组件评价，再接回真实通行触发；当前保留身份像素仍关闭，独立逐事件与现场输入仍待补。"
paths=[main,PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',ROOT/'Review与当前状态.md']
backup=ROOT/'snapshots/overview_v14_before_identity_joint_pair';backup.mkdir(parents=True,exist_ok=False);snapshots=[]
for p in paths:
 dest=backup/p.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());snapshots.append({'path':str(p),'snapshot':str(dest),'sha256':sha(dest)})
for p in paths[1:]:
 s=p.read_text();head,rest=s.split('\n',1);rest=rest.lstrip('\n');assert rest.startswith('2026年10月30日最新：');rest=rest.replace('2026年10月30日最新：','同日此前训练与新模型实现准入：',1)
 extra=' '+link('第15版总览复核','research_synthesis_20261027/results/overview_review_20261030_v15.json')+'。'if p==ROOT/'Review与当前状态.md'else''
 p.write_text(head+'\n\n'+latest+extra+'\n\n'+rest,encoding='utf-8')
s=main.read_text();s=s.replace('尚未证明可靠自动赋号或与检测并发时稳定5FPS。','其后固定照片同板对照的新模型两次均4.974FPS、计数10，尚未证明可靠自动赋号或稳定全链路5FPS。',1)
needle='2026年10月30日最新：';a=s.index(needle);s=s[:a]+latest+'\n\n此前训练与新模型实现准入：'+s[a:].replace(needle,'',1)
oldrow='| 新身份权重实机 | 97图＋2预热、120决定一致，网络144.12ms均值 | 没有并发检测，不构成新全链路5FPS或身份准确率证明 |'
newrow='| 新身份权重实机 | 97图准入后再做四次同板；新模型4.974／4.974FPS、均计10 | 固定10照片负载，仍有迟到／跳过；永久牛号未知 |';assert s.count(oldrow)==1;s=s.replace(oldrow,newrow)
section=f'''### 3.9 新旧身份候选已经完成同一负载的同板对照

{reference}只改变身份编码器与对应重编码图库，固定检测器、照片、框、入队偏移及CPU策略，旧—新—新—旧四次各完成10个身份任务。30张新图库及10张实际照片先在CPU做Torch40／NCNN40参考，再在板上40图＋1预热准入；正式4次共40身份查询＋4预热，所有输入与各自原始特征逐项核对。

| 次序／身份模型 | 处理／392 | 跳过 | >200ms | FPS | 计数／人工12 | 最长身份完成s |
|---|---:|---:|---:|---:|---:|---:|
'''
for c in cases:section+=f"| {c['run']} | {c['processed_frames']} | {c['skipped_slots']} | {c['deadline_misses']} | {c['processed_per_second_over_offered_duration']:.3f} | {c['source_down_count']} | {c['maximum_identity_result_ms']/1000:.3f} |\n"
section+=f'''
新模型的迟到略少，但每次多2跳过，没有改善原片总计数；网络／完成时延、同照片候选和全部次序一并保留。每种只有两次相同源重复，不作显著性推断。接受数是没有永久身份GT的候选输出，不认领真实找回。新模型不据此替换默认；下一步先完成已冻结的身份组件独立评价，再恢复真实通行触发与因果选图。

完整归档、{v['actual_timed_O8_forwards']}实际raw、{v['counter_observation_ticks']}观察时刻、40原照片／输入／特征、20配对和完整四次ByteTrack关联／事件重放均通过；程序复算不代替独立人工真值。O8、默认encoder、父子进程、锁与板内服务终态已核查。总新增板端前向{v['all_new_actual_board_forwards']}，CPU参考80，训练0；未来20ID与保留日期未开启。

'''
assert s.count('## 4. 数据还需要怎样补')==1;s=s.replace('## 4. 数据还需要怎样补',section+'## 4. 数据还需要怎样补',1)
marker='## 4. 数据还需要怎样补\n\n';extra=link('20个保留身份的评价与校准协议','identity_final20_20261030/计划与验收.md')+'和'+link('校准冻结结果','identity_final20_20261030/校准冻结结果与像素状态.md')+'现已固定：10已登记／10未知、90图，使用匹配10ID图库的已有校准特征确定主阈值。当前只完成元数据和阈值准备，保留90图尚未请求；新模型两个校准分组的阈值约0.830／0.871，分组不稳定性也已保存。该评价只检验身份组件，不声称整项目像素未见或跨牧场。\n\n';s=s.replace(marker,marker+extra,1)
oldstep='2. 新域六次训练、三种拒识分数和新权重ARM准入已完成；保留主seed26及校准选出的绝对余弦，不因开发结果替换。下一步固定与目标图库规模一致的正式评价和系统负载，模型／方法／阈值冻结后才开启未来20候选。现有Cows120ID和COLO50图均作为已见开发／压力材料，不能再包装成未见最终测试；94检测缺口与103确认损失继续分别保留。'
newstep='2. 新域训练、拒识分数、ARM准入和新旧同板对照已完成；模型与方法继续冻结。20个保留ID的90图清单及匹配10ID校准阈值已固定，下一步冻结执行代码并按清单核验／运行，不能用保留成绩再选模型或阈值。现有Cows120ID和COLO50图为已见材料；身份组件ID互斥不等于全项目像素未见。';assert s.count(oldstep)==1;s=s.replace(oldstep,newstep)
oldstep='3. 同负载CPU分配控制已完成，两个CPU限制策略均未全局采用。新编码器已在板上通过97图实现核验，下一步在独立目录固定相同检测器和照片负载比较新旧身份候选，再接回真实通行触发；同时报告前台迟到、计数及后台完成，不把纯网络144.12ms当完整后台等待。'
newstep='3. 新旧编码器同照片负载的四次同板对照已完成，未支持默认替换。下一步固定模型与各自图库，接回实际计数触发的因果选图和按需身份任务；保持JPEG／PNG／NPZ边界，分别核查触发照片、前台计数／迟到、后台等待与未解决事件。';assert s.count(oldstep)==1;s=s.replace(oldstep,newstep)
a=s.index('本轮新域训练六条件1800正式更新');b=s.index('\n\n总体研究目标继续',a)
s=s[:a]+f"本轮新旧身份同板四次均已完成，{v['actual_timed_O8_forwards']}定时O8、8资格＋8预热、85ARM身份前向均有原始记录，总板端{v['all_new_actual_board_forwards']}次；CPU参考作业130870完成80前向，关联重放作业{v['tracker_replay_job_id']}新增网络前向0。全部原包完整取回，原JPEG／PNG、输入／特征、20配对及四条完整关联／事件路径复算通过。两种模型均计数10，新模型两次390／392，不认领可靠赋号或稳定全链路5FPS；默认encoder和O8未变。此前训练、拒识和转换结果继续保留，未来20ID和03-05至03-11像素仍关闭。"+s[b:]
main.write_text(s,encoding='utf-8')
out={'status':'FIVE_ENTRYPOINTS_UPDATED_WITH_VERIFIED_IDENTITY_JOINT_PAIR_AND_V14_SNAPSHOTS','created_UTC':datetime.now(timezone.utc).isoformat(),'previous_files_and_snapshots':snapshots,'current_entrypoints':[{'path':str(p),'sha256':sha(p)}for p in paths],'whole_goal_complete':False};p=ROOT/'results/entrypoint_update_20261030_v15.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':out['status'],'report_lines':len(s.splitlines())}))
