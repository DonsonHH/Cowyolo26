from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
link=lambda label,name:f'[{label}](<{(PROJECT/name).as_posix()}>)'
old=load(ROOT/'results/overview_review_20261031_v23_workload.json')
main=PROJECT/'研究阶段总结_20261030.md';assert sha(main)==old['document']['sha256']
trial_path=PROJECT/'pynq_parent_only_workload_20261031/results/final_review_v1.json'
probe_path=PROJECT/'pynq_startup_probe_20261031/results/final_review_v1.json'
trial,probe=load(trial_path),load(probe_path)
assert trial['all8_complete']and trial['actual_timed_O8_forwards']==3115 and probe['actual_ARM_identity_warmups']==4
assert not trial['all_offered_200ms_deadlines_met']and not trial['whole_goal_complete']
paths=[main,PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',
       PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',ROOT/'Review与当前状态.md']
folder=ROOT/'snapshots/overview_v23_before_parent_only_candidate';folder.mkdir(parents=True,exist_ok=False)
before={};copies=[]
for p in paths:
 before[p]=p.read_text(encoding='utf-8');out=folder/p.relative_to(PROJECT);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(p.read_bytes())
 copies.append({'path':str(p),'snapshot':str(out),'sha256':sha(out)})
report=link('精简导入后完整八轮','pynq_parent_only_workload_20261031/精简后台导入_八轮负载与剩余问题.md')
startup=link('四次启动与内存测量','pynq_startup_probe_20261031/后台导入与启动内存_四次测量.md')
review=link('完整八轮自审','pynq_parent_only_workload_20261031/results/final_review_v1.json')
supp=link('论文补充：启动与完整八轮','paper_readiness_20261030/论文补充_启动开销与完整八轮_20261031.md')
latest=('2026年10月31日最新实机进展：'+startup+'确认精简子进程导入后READY约2.36秒，两进程顺次采样PSS合计低37.5–37.9MiB；4次预热raw一致，原40秒超时未重现。'
        +report+'已完成新A/B/C/D/D/C/B/A八轮，双负载D为4.936／4.898FPS、P95 323.42／339.72ms、计数10／9（人工总12）；仍有跳帧和迟到。'
        '3115实际raw、40身份任务及17379观察／16完整关联路径核验，板端3187图前向，启动探针4另计，新增CPU神经参考0。'
        '计9那轮的9个离线raw补回对照仅9515单帧能恢复模型参照10，未恢复人工12，未证明设备调度改进。'
        '新旧初态不同，原5轮失败保留，不把全部性能变化作独立因果归因。'+supp+'保留C10／C11／C12待证据，整体目标继续。')
for p in paths[1:]:
 head,rest=before[p].split('\n',1);rest=rest.lstrip('\n');assert rest.startswith('2026年10月31日最新实机进展：')
 rest=rest.replace('2026年10月31日最新实机进展：','此前五轮失败阶段：',1)
 extra=' '+link('第24版总览复核','research_synthesis_20261027/results/overview_review_20261031_v24_parent_only.json')+'。'if p==ROOT/'Review与当前状态.md'else''
 p.write_text(head+'\n\n'+latest+extra+'\n\n'+rest,encoding='utf-8')
s=before[main];assert s.count('2026年10月31日最新实机进展：')==1
s=s.replace('2026年10月31日最新实机进展：',latest+'\n\n此前五轮失败阶段：',1)
start=s.index('**当前进展：');end=s.index('**',start+2)+2
s=s[:start]+('**当前进展：减少后台重复导入的候选已完整完成八轮，已就绪192输入下双负载约4.90–4.94FPS、身份结果最长约1.82秒；'
              '仍有跳帧／迟到，两次计数10／9而非人工12。全部raw、身份任务、完整关联及离线补帧诊断均已核验；'
              '原失败、低身份覆盖与外来源高误收保留。下一步接回实际触发链路，并做一般性有界输入／调度控制；'
              '独立事件、永久牛号、真实输入、功耗和论文贡献仍待证据。**')+s[end:]
oldrow='| 同负载资源控制：八轮计划失败 | 五轮A/B/C/D/D，3.648–4.885FPS；1748raw、30任务和完整关联通过 | 第6轮READY超时，缺后半重复；启动／换页根因和稳定5FPS未证实 |'
assert s.count(oldrow)==1
s=s.replace(oldrow,'| 精简导入后完整八轮 | 双负载4.936／4.898FPS、P95 323.42／339.72ms、计数10／9；3115raw／40任务通过 | 有跳帧／迟到；低分输入已就绪、固定任务，无独立事件／身份GT |\n'+oldrow,1)
section=f'''### 3.16 后台启动开销与精简导入后的完整八轮

{startup}采用原／精简／精简／原4个新父进程，均保留同一43,352,064字节帧银行、前史和NativeGraph，但不运行检测图或周期负载。原READY16.962／15.416秒，精简2.362／2.367秒；子进程PSS约89.47–89.48降至25.13MiB，父进程PSS也改变，顺次采样两进程合计低37.54／37.87MiB。4个预热raw与旧ARM一致。原40秒超时未重现，不能据组件测量宣告原异常根因已修好。

{report}只将6条前台导入移入main，模型／后台／阈值／数值路径保持。新协议完整运行8次固定工作量，低分帧已就绪，I控制高分JPEG生产，W控制0或10同照片任务。

| 轮次 | I/W | 处理/392 | 跳过 | >200ms | FPS | P95ms | 下行计数/人工12 |
|---|---|---:|---:|---:|---:|---:|---:|
| r1_A | 0/0 | 392 | 0 | 0 | 5.000 | 159.79 | 10 |
| r2_B | 1/0 | 388 | 4 | 200 | 4.949 | 282.99 | 10 |
| r3_C | 0/1 | 389 | 3 | 79 | 4.962 | 294.97 | 10 |
| r4_D | 1/1 | 387 | 5 | 65 | 4.936 | 323.42 | 10 |
| r5_D | 1/1 | 384 | 8 | 144 | 4.898 | 339.72 | 9 |
| r6_C | 0/1 | 391 | 1 | 55 | 4.987 | 287.22 | 10 |
| r7_B | 1/0 | 392 | 0 | 0 | 5.000 | 160.59 | 10 |
| r8_A | 0/0 | 392 | 0 | 0 | 5.000 | 159.51 | 10 |

3115正式检测＋8准入＋16检测预热＋40身份正式＋8身份预热，共3187；启动探针4次另计。1568生产记录、1551前台接收和1394调用重叠案例核验。CPU任务130932完成17379观察／4162跟踪行、16关联／事件路径，ID、事件和坐标实际一致，新增神经前向0。40查询的4次阈值接受是同一固定照片重复，无永久身份正确率。

两次D身份入队至结果最大1813.39／1822.39ms，父进程末VmSwap58.50／60.00MiB；B的两次重复迟到200／0也保留。缓存／换页初态与旧5轮失败不同，不将新旧差值都归因于导入改动。原40秒超时没有在新8轮出现，但唯一根因未证实，真实动态触发与相机／RFID未证明。

r5_D跳过的8帧逐一及全部补回，共9个已有raw的事后重放。仅9515单补回使计9回到模型全输入参照10，其余7个单补回仍9，全补回10；19519观察／18事件状态路径复算，前缀与全补回轨迹符合控制。不是人工12、独立数据或设备已补帧的证据；后续研究一般性有界输入／排队和尾延迟，不做源帧特判。

原包23,913,516字节／223成员与参考包8,573,296字节／60成员均取回并核验；实际PNG已看。当前全部任务PID退出、锁可取得、错误寄存器0、SSH／Jupyter active、boot未变，未发现OOM日志。{review}与{supp}已更新；256／320仍沿用此前向量测试范围，本轮没有复测。

'''
assert s.count('## 4. 数据还需要怎样补')==1;s=s.replace('## 4. 数据还需要怎样补',section+'## 4. 数据还需要怎样补',1)
lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('3. 原实际触发四轮保持完整核验；'):
  lines[i]='3. 原实际触发四轮和旧5轮失败均保留；精简导入候选已完整完成八轮并验收。下一步将同一候选接回实际通行触发链路，继续记录任务数、捕获选择、身份等待和全部不利结果；固定10任务接近5FPS不替代实际触发结论。'
 if line.startswith('4. 历次回放已暴露3／7／8／9／10计数波动'):
  lines[i]='4. 历史固定10照片的CPU／编码器对照与新导入八轮均已核验。9515离线单补回只能将模型参照9恢复10；下一步采用一般性的有界低分输入／调度对照，记录缓存、处理延迟和所有跳过，保留人工12及独立事件参考缺口，不以特判源帧凑总数。'
 if line.startswith('6. ')and'论文草稿v3'in line:
  lines[i]=line+' '+supp+'加入新候选8轮和组件测量，仍非投稿终稿。'
s='\n'.join(lines)+'\n'
needle='## 7. 本轮状态与自审\n\n';assert s.count(needle)==1
s=s.replace(needle,needle+'本轮4次启动测量和完整新8轮已核验，原5轮失败保留。3187＋4板端图前向分开计账，3115raw／40任务、17379观察关联、19519观察离线补帧和实际图表复核通过；没有新增CPU神经前向。'+review+'。双负载近5但有迟到和计数9，整体目标继续。\n\n',1)
main.write_text(s,encoding='utf-8')
diff=[]
for p in paths:diff.extend(difflib.unified_diff(before[p].splitlines(),p.read_text(encoding='utf-8').splitlines(),fromfile=str(p.relative_to(PROJECT))+' v23',tofile=str(p.relative_to(PROJECT))+' v24',n=2))
diff_path=ROOT/'results/overview_diff_20261031_v24_parent_only.txt'
with diff_path.open('x',encoding='utf-8')as f:f.write('\n'.join(diff)+'\n')
paper=PROJECT/'paper_readiness_20261030/论文补充_启动开销与完整八轮_20261031.md'
record={'status':'FIVE_ENTRYPOINTS_UPDATED_STARTUP4_AND_COMPLETE_PARENT_ONLY8_WITH_REMAINING_GAPS',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'previous_files_and_snapshots':copies,
 'current_entrypoints':[{'path':str(p),'sha256':sha(p)}for p in paths],
 'new_documents':[{'path':str(paper),'sha256':sha(paper)}],
 'new_review_sources':[{'path':str(p),'sha256':sha(p)}for p in[trial_path,probe_path]],
 'diff':{'path':str(diff_path),'sha256':sha(diff_path)},'whole_goal_complete':False}
with(ROOT/'results/entrypoint_update_20261031_v24_parent_only.json').open('x',encoding='utf-8')as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'status':record['status'],'main_lines':len(s.splitlines()),'diff_lines':len(diff)}))
