from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(label,path):return f'[{label}](<{(PROJECT/path).as_posix()}>)'

study=PROJECT/'identity_final20_20261030';final=load(study/'results/final_review.json');assert final['primary_Top1_C_W_U_FA']==[[22,10,2,18,3],[30,3,0,27,0]]
old=load(ROOT/'results/overview_review_20261030_v15.json');main=PROJECT/'研究阶段总结_20261030.md';assert sha(main)==old['document']['sha256']
paths=[main,PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',ROOT/'Review与当前状态.md'];backup=ROOT/'snapshots/overview_v15_before_final20_evaluation';backup.mkdir(parents=True,exist_ok=False);snapshots=[]
for path in paths:
 dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes());snapshots.append({'path':str(path),'snapshot':str(dest),'sha256':sha(dest)})
ref=link('保留20身份评价与自动接受限制','identity_final20_20261030/保留20身份结果与自动接受限制.md')
latest=f'2026年10月30日最新：{ref}按像素请求前冻结的协议完成10已登记／10未知、90图评价。旧／新编码器Top-1为22／30、30／30；主工作点C／W／U分别10／2／18、3／0／27，未知FA3／30、0／30。新模型只接受3张、来自2个作者ID，不能称可靠自动恢复或总体零风险。90输入、180特征、1200身份分数／480决定及按ID统计均复算，完整原包4,413,444字节已取回。20个保留身份现在已使用，03-05至03-11像素仍隔离；同场景身份组件评价不等于全项目未见像素或原12通行身份真值。本轮180次CPU前向、0训练／0板端；下一步在PYNQ-Z2复核同90图的两模型及全部决定，再接回实际抓拍。'
for path in paths[1:]:
 text=path.read_text();head,rest=text.split('\n',1);rest=rest.lstrip('\n');assert rest.startswith('2026年10月30日最新：');rest=rest.replace('2026年10月30日最新：','同日此前新旧身份同板对照：',1)
 extra=' '+link('第16版总览复核','research_synthesis_20261027/results/overview_review_20261030_v16.json')+'。'if path==ROOT/'Review与当前状态.md'else''
 path.write_text(head+'\n\n'+latest+extra+'\n\n以下保留此前阶段，旧“保留像素仍关闭”等状态按该阶段时间解释。\n\n'+rest,encoding='utf-8')
s=main.read_text();a=s.index('**当前结论：');b=s.index('\n\n',a)
s=s[:a]+'**当前结论：检测、计数与身体检索已经在同一PYNQ-Z2运行，固定负载接近5FPS，但当前192原片仍计10／人工确认12。最新保留身份组件评价的新编码器Top-1为30／30，固定阈值只正确接受3、拒绝27；未知误接受0／30是本批观察，不代表总体零风险。候选排序方向可保留，可靠自动找回、真实输入下稳定5FPS和论文主要贡献仍需验证。默认模型和部署阈值未替换。**'+s[b:]
row='| 新域身份训练与开发 | 六次配对训练；主候选40ID Top-1 99／120 | 20ID校准阈值下C10／W1／U109、未知FA5／120；非完整事件 |'
assert s.count(row)==1;s=s.replace(row,row+'\n| 保留ID身份组件CPU评价 | 10注册＋10未知，90图；新Top-1 30／30、旧22／30 | 新主工作点C3／W0／U27、未知FA0／30；低覆盖且非现场全链路 |',1)
a=s.index('2026年10月30日最新：');s=s[:a]+latest+'\n\n此前新旧编码器同板对照：'+s[a:].replace('2026年10月30日最新：','',1)
section=f'''### 3.10 保留身份的一次固定评价：排序和自动接受仍有差距

{ref}使用新域训练前已保留的20个Cows身份，10注册／10未知；每牛3查询，注册每牛3参考且至少早7天。主候选与旧C共180次CPU图像前向，无新训练、板端推理或阈值搜索。

| 编码器 | Top-1／30已登记 | 正确C | 误赋号W | 拒绝U | 未知FA／30 |
|---|---:|---:|---:|---:|---:|
| 适配前旧C | 22 | 10 | 2 | 18 | 3 |
| 新域C_seed26 | 30 | 3 | 0 | 27 | 0 |

新模型3张正确接受来自2个作者ID，旧模型3张未知误接受来自同一未知ID。新模型的27张拒识虽然候选第一名正确，仍不能在固定阈值下自动赋号。每组只有10个身份，完美排名／零误收的经验bootstrap区间退化，不代表总体100%正确或零风险；所有八个工作点与按牛配对区间均保留。

![保留20身份主工作点]({(study/'results/figures_v2/final20_primary.png').as_posix()})

该20身份的裁剪文件在模型、方法、阈值和代码冻结后首次取得，Cows命名空间内与16训练／120开发ID互斥；场景相同、部分检测原图已用于项目、跨年物理身份未映射，不能称整项目未见像素或跨牧场测试。90图／180特征、1200ID分数、480决定、8组按ID区间及20配对均复算，完整128成员原包取回；8源样例、23解释案例与统计图已查看。

这20身份现在已见；若再用其结果改方法，不能继续称新方法的最终未见测试。下一步将同90图上板只验证实现和数值，不把重复执行算第二个独立测试。原12通行永久牛号、独立逐事件JSON和同通道真实双向仍未获得。

'''
marker='## 4. 数据还需要怎样补';assert s.count(marker)==1;s=s.replace(marker,section+marker,1)
oldpara=link('20个保留身份的评价与校准协议','identity_final20_20261030/计划与验收.md')+'和'+link('校准冻结结果','identity_final20_20261030/校准冻结结果与像素状态.md')+'现已固定：10已登记／10未知、90图，使用匹配10ID图库的已有校准特征确定主阈值。当前只完成元数据和阈值准备，保留90图尚未请求；新模型两个校准分组的阈值约0.830／0.871，分组不稳定性也已保存。该评价只检验身份组件，不声称整项目像素未见或跨牧场。'
newpara='保留20身份的固定评价已经完成，见'+ref+'。'+link('评价前校准快照','identity_final20_20261030/校准冻结结果与像素状态.md')+'继续保留，主阈值没有因测试结果换到另一个校准分组。身份组件已补保留ID结果；当前缺口是完整事件身份、跨来源和最终方法需要的进一步独立证据。';assert s.count(oldpara)==1;s=s.replace(oldpara,newpara)
s=s.replace('此前540图及120ID现均属开发材料，未来20候选及保留日期未开启。','此前540图及120ID已属开发材料；在该拒识对照阶段未来20ID仍关闭，后续固定一次评价见3.10，03-05至03-11日期继续保留。',1)
s=s.replace('总新增板端前向1665，CPU参考80，训练0；未来20ID与保留日期未开启。','总新增板端前向1665，CPU参考80，训练0；该同板阶段未来20ID尚未开启，后续固定组件评价见3.10。',1)
oldstep='2. 新域训练、拒识分数、ARM准入和新旧同板对照已完成；模型与方法继续冻结。20个保留ID的90图清单及匹配10ID校准阈值已固定，下一步冻结执行代码并按清单核验／运行，不能用保留成绩再选模型或阈值。现有Cows120ID和COLO50图为已见材料；身份组件ID互斥不等于全项目像素未见。'
newstep='2. 保留20ID的固定CPU评价已经完成，排序提高而自动接受仍少。保持两编码器、全部阈值和输入不变，下一步对这90图做PYNQ-Z2真实ARM数值与决定核对；任何端点变化如实保留，不改阈值隐藏。已评分20ID不再作为后续改方法的未见证据，03-05至03-11日期继续保留。';assert s.count(oldstep)==1;s=s.replace(oldstep,newstep)
a=s.index('本轮新旧身份同板四次均已完成');b=s.index('\n\n总体研究目标继续',a)
s=s[:a]+'本轮保留20身份的90图固定评价完成，作业130877为COMPLETED／0:0，180次CPU图像前向、16批调用、无预热／训练／板端操作。原始包128成员／127清单文件、90输入／6tensor锚点、180特征、1200ID分数／480决定、8组区间和20配对均复算通过；8源样例、23案例、修订图已实际查看，原版布局保留。两模型主工作点为旧C10／W2／U18／FA3、新C3／W0／U27／FA0；完整八工作点保留，不调参。保留20ID现在已见，未开启03-05至03-11日期。此前同板实机记录与默认模型保持原阶段状态，本轮未用CPU结果代替板端证明。'+s[b:]
s=s.replace('新的最终身份评价、同通道真实双向和跨来源稳定计数','完整事件身份与进一步独立验证、同通道真实双向和跨来源稳定计数',1)
main.write_text(s,encoding='utf-8')
value={'status':'FIVE_ENTRYPOINTS_UPDATED_WITH_FINAL20_FIXED_TEST_AND_V15_SNAPSHOTS','created_UTC':datetime.now(timezone.utc).isoformat(),'previous_files_and_snapshots':snapshots,'current_entrypoints':[{'path':str(p),'sha256':sha(p)}for p in paths],'whole_goal_complete':False};target=ROOT/'results/entrypoint_update_20261030_v16.json';assert not target.exists();target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':value['status'],'report_lines':len(s.splitlines())}))
