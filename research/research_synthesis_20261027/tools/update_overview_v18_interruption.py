from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(label,name):return f'[{label}](<{(PROJECT/name).as_posix()}>)'

phase=PROJECT/'identity_trigger_pair_20261030';v=load(phase/'results/interruption_review_v1.json')
assert v['observed_case_counts']==[10,10,8]and not v['fourth_case_terminal_received']and not v['raw_outputs_or_photos_received']
old=load(ROOT/'results/overview_review_20261030_v17.json');main=PROJECT/'研究阶段总结_20261030.md';assert sha(main)==old['document']['sha256']
paths=[main,PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',ROOT/'Review与当前状态.md']
backup=ROOT/'snapshots/overview_v17_before_trigger_access_interruption';backup.mkdir(parents=True,exist_ok=False);snapshots=[]
for p in paths:
 dest=backup/p.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());snapshots.append({'path':str(p),'snapshot':str(dest),'sha256':sha(dest)})
ref=link('实际计数触发对照的部分观察与恢复','identity_trigger_pair_20261030/实际触发对照_部分观察与恢复.md')
latest=f'2026年10月30日最新：{ref}已启动旧—新—新—旧四轮，最后成功串口观察取得前三轮摘要：计数10／10／8、身份任务10／10／8，吞吐4.630／4.770／4.643FPS。第四轮只确认至少350帧进度，累计定时检测调用至少1451；原始raw、照片／特征、第四轮终态尚未取回，不能作为完整四次验收。用户随后确认断电或移动连接；当前COM6无输出、原IP端口超时，停止继续探测与重跑。已冻结本机观察证据和恢复代码，待恢复SD启动／USB后只读检查原目录、boot ID和结果；不加载模型或O8凑终态条件。此前已完成的同90图ARM一致性证据仍保留，整体目标继续。'
for p in paths[1:]:
 s=p.read_text();head,rest=s.split(chr(10),1);rest=rest.lstrip(chr(10));assert rest.startswith('2026年10月30日最新：');rest=rest.replace('2026年10月30日最新：','同日此前已完成的同90图ARM核验：',1)
 extra=' '+link('第18版中断状态复核','research_synthesis_20261027/results/overview_review_20261030_v18_interruption.json')+'。'if p==ROOT/'Review与当前状态.md'else''
 p.write_text(head+chr(10)*2+latest+extra+chr(10)*2+rest,encoding='utf-8')
s=main.read_text();a=s.index('**当前结论：');b=s.index(chr(10)*2,a)
s=s[:a]+'**当前进展：同90图的两编码器ARM实现核验已完成，480决定与CPU一致；新模型候选排序好，但仅自动接受3／30查询。实际计数触发对照已启动，前三轮摘要为10／10／8，第四轮终态与原始数据尚未取回。用户确认板卡断电或连接移动，当前先保留证据并等待恢复访问，不认领完整四轮通过。可靠自动找回、稳定全链路5FPS及论文主要贡献仍待验证。**'+s[b:]
needle='2026年10月30日最新：';a=s.index(needle);s=s[:a]+latest+chr(10)*2+'此前已完成的同90图ARM核验：'+s[a:].replace(needle,'',1)
row='| 目前已验证 | 结果与实际范围 | 仍需解决 |';assert s.count(row)==1;s=s.replace(row,'| 当前证据状态 | 结果与实际范围 | 仍需解决 |',1)
needle='| 192检测与计数 |';a=s.index(needle)
s=s[:a]+'| 新实际触发阶段（待核验） | 只取回前三轮摘要10／10／8；第四轮至少350帧 | 恢复SD结果，核对raw／轨迹／照片和第四轮终态 |'+chr(10)+s[a:]
section=f'''### 3.12 实际计数触发对照：部分摘要保留，原始结果待恢复

{ref}沿用192检测器、原O8和同一几何因果选图，高分JPEG每时隙实际读取；按当次通行触发身份，未强制每次做10个任务。旧—新—新—旧四次已由同一父任务启动，当前只取得下列主机观察。没有独立逐事件或永久身份参考。

| 已观察轮次／身份 | 处理／392 | 跳过 | >200ms | FPS | 计数／人工12 | 身份任务摘要 |
|---|---:|---:|---:|---:|---:|---:|
| r1_old | 363 | 29 | 273 | 4.630 | 10 | 10 |
| r1_new | 374 | 18 | 124 | 4.770 | 10 | 10 |
| r2_new | 364 | 28 | 285 | 4.643 | 8 | 8 |

第四轮最后只观察到至少350帧，累计定时检测调用至少1451。新模型第二轮计8的不利摘要保留；原始raw、照片／特征及第四轮终态均未取回，不能用前三轮外推、代码预期或此前固定负载结果补齐，也不能把1451写成本阶段最终前向总数。预备CPU参考与关联重放尚未实际执行，不认领独立复算通过。

用户确认断电／连接移动，具体时刻与SD写入完成未知。本机已保存冻结协议、代码、成功／超时观察和恢复准备。恢复后先读原目录与boot ID；若发生重启，区分原实验O8记录和当前基础overlay，不加载模型或PL来凑“未改变”条件。原始文件尚在与否需要实际读卡证明，不能因失联宣称丢失或完成。

电脑网口最后为DHCP192.168.3.13，与先前直连192.168.2.1不同；不修改当前IP／路由，优先恢复SD启动和PROG-UART USB后走COM6取回。此前已完整核验阶段仍按其证据成立，本阶段保持待验。

'''
needle='## 4. 数据还需要怎样补';assert s.count(needle)==1;s=s.replace(needle,section+needle,1)
oldstep='3. 新旧编码器同照片负载的四次同板对照已完成，未支持默认替换。下一步固定模型与各自图库，接回实际计数触发的因果选图和按需身份任务；保持JPEG／PNG／NPZ边界，分别核查触发照片、前台计数／迟到、后台等待与未解决事件。'
newstep='3. 实际计数触发的四次对照已启动，当前只保存前三轮摘要与第四轮进度，阶段未验收。恢复SD启动／USB后只读检查原任务和boot ID，取回所有已有原始结果；完整保存才做四轮评分，部分保存就报告实际范围，不补跑或替换。实际照片参考、关联重放和后台等待都须取包后验证。';assert s.count(oldstep)==1;s=s.replace(oldstep,newstep)
a=s.index('本轮同90图真实ARM核验完成180正式＋4预热');b=s.index(chr(10)*2+'总体研究目标继续',a)
s=s[:a]+'本轮完成实际触发链路冻结、设备预检与原父任务启动，前三轮摘要及第四轮至少350帧进度已保存。访问中断后用户确认断电／连接移动；串口与原IP无响应，未重启原实验或改网络。离线自审只核对观察文件hash、392时隙摘要算术与恢复边界，不等于原始raw／照片／特征复核。已准备区分新旧boot、不加载模型／O8的只读取回与采集脚本，尚未上板执行。本阶段原始文件、第四轮终态和独立数值／关联复算均待恢复；此前同90图ARM完整核验仍保留。'+s[b:]
main.write_text(s,encoding='utf-8')
v={'status':'FIVE_ENTRYPOINTS_UPDATED_WITH_PARTIAL_ACTUAL_TRIGGER_OBSERVATIONS_AND_ACCESS_RECOVERY_LIMITS','created_UTC':datetime.now(timezone.utc).isoformat(),'previous_files_and_snapshots':snapshots,'current_entrypoints':[{'path':str(p),'sha256':sha(p)}for p in paths],'whole_goal_complete':False}
target=ROOT/'results/entrypoint_update_20261030_v18_interruption.json';assert not target.exists();target.write_bytes(json.dumps(v,ensure_ascii=False,indent=2).encode()+bytes([10]));print(json.dumps({'status':v['status'],'main_report_lines':len(s.splitlines())}))
