"""Integrate verified new identity training, rejection scores and actual ARM evidence."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def link(label,path):return f'[{label}](<{(PROJECT/path).as_posix()}>)'

arm=load(PROJECT/'identity_domain_arm_20261030/results/final_review.json')
assert arm['actual_ARM_measured_forwards']==97 and not arm['whole_goal_complete']
paths=[PROJECT/'研究阶段总结_20261030.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',ROOT/'Review与当前状态.md']
old=load(ROOT/'results/overview_review_20261030_v13.json');assert sha(paths[0])==old['document']['sha256']
backup=ROOT/'snapshots/overview_v13_before_domain_training';backup.mkdir(parents=True,exist_ok=False)
snapshots=[]
for path in paths:
 dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes());snapshots.append({'path':str(path),'snapshot':str(dest),'sha256':sha(dest)})
domain=link('新域三seed配对训练','identity_domain_adapt_20261030/身份域适配配对训练与开发结果.md')
scores=link('拒识分数与校准选择','identity_rejection_scores_20261030/拒识分数对照与校准选择.md')
ncnn=link('630图NCNN一致性','identity_domain_ncnn_20261030/新身份编码器NCNN转换与一致性验证.md')
board=link('新权重97图ARM实机','identity_domain_arm_20261030/新身份候选ARM实机与研究决定.md')
latest=f'2026年10月30日最新：{domain}完成六次同初值、各300更新对照；新Cows训练16ID／457图与既有120ID和未来20候选隔离。主seed26在两个20ID开发组Top-1为54／60、51／60，完整40ID压力为99／120（旧C65／120），但新域阈值下C10／W1／U109，未知FA5／120，自动接受覆盖率仍不足。{scores}比较7模型×3分数，21阈值只用校准选，主方法仍为绝对余弦，未因开发结果换方法。{ncnn}的1260条开发决定一致，240条校准决定中1个浮点端点变化如实保留。{board}完成97正式＋2预热，120检索决定一致，纯网络均值{arm["mean_network_ms"]:.2f}ms、P95 {arm["P95_network_ms"]:.2f}ms；该次没有并发检测。原始包完整取回并独立复算，默认encoder与O8未变。保留未来20ID及03-05至03-11像素，独立逐事件JSON、原12事件永久身份、稳定全链路与现场输入仍待补。'
for path in paths[1:]:
 text=path.read_text();head,rest=text.split('\n',1)
 rest=rest.lstrip('\n');assert rest.startswith('2026年10月30日最新：')
 rest=rest.replace('2026年10月30日最新：','同日此前的身份基线阶段：',1)
 if path==ROOT/'Review与当前状态.md':body=latest+' '+link('第14版总览复核','research_synthesis_20261027/results/overview_review_20261030_v14.json')+'。'
 else:body=latest
 path.write_text(head+'\n\n'+body+'\n\n以下保留此前阶段；旧“当前／下一步”按各阶段证据解释。\n\n'+rest,encoding='utf-8')

path=paths[0];text=path.read_text();a=text.index('**当前结论：');b=text.index('\n\n',a)
text=text[:a]+'**当前结论：检测、计数与身体检索已经在同一PYNQ-Z2运行，固定负载可接近5FPS，但192原片计数仍未恢复人工确认12。新域训练把完整40ID开发Top-1由65／120提高到99／120；固定新阈值下仅正确接受10／120，拒识覆盖仍不足。新权重已通过97图实机一致性核验，网络平均144.12ms，尚未证明可靠自动赋号或与检测并发时稳定5FPS。研究继续围绕独立事件、可靠拒识和明确负载下的系统取舍推进。**'+text[b:]
oldrow='| 外来源身份评价 | Cows2021新540裁剪，C Top-1 65／120 | 新域错误接受21／120、未知误接受20／120；非完整事件 |'
newrow='| 新域身份训练与开发 | 六次配对训练；主候选40ID Top-1 99／120 | 固定新阈值C10／W1／U109、未知FA5／120；非独立完整事件 |\n| 新身份权重实机 | 97图＋2预热、120决定一致，网络144.12ms均值 | 没有并发检测，不构成新全链路5FPS或身份准确率证明 |'
assert text.count(oldrow)==1;text=text.replace(oldrow,newrow)
first=text.index('2026年10月30日最新：');text=text[:first]+latest+'\n\n同日此前身份基线结果（保留原口径）：'+text[first:].replace('2026年10月30日最新：','',1)
text=text.replace('固定身体编码器在Cortex-A9上完成132张图的真实推理','适配前的固定身体编码器在Cortex-A9上完成132张图的真实推理',1)
text=text.replace('新的带作者ID评价已经完成，不能再将','适配前旧C的带作者ID评价已经完成，不能再将',1)
newsection=f'''### 3.8 新域训练改善排序，新权重已经通过实机准入

六次正式训练从同一已上板encoder开始，M分支为MultiCam580图／20ID，C分支为Cows457图／16新ID，各seed26／27／28固定300更新。六个末轮权重共同冻结后才计算校准特征与各自阈值，再统一评价开发／原来源保留集；不按epoch或开发seed择优。正式1800更新、57600训练图像前向，另有丢弃预检2更新／64图及3780评价图像前向。作者原名Identification/Test中的16个未用ID被明确改作本项目训练，不能声称复现原作者测试协议。

| 同一20ID开发图库 | fold0 Top-1／60 | fold1 Top-1／60 |
|---|---:|---:|
| 原C不继续训练 | 42 | 29 |
| M_continue_seed26 | 37 | 33 |
| C_domain_seed26（预先指定主候选） | 54 | 51 |

全部seed及40ID压力、MultiCam保留结果均在{domain}。训练来源、图数和ID数同时改变，对照不归因于单一摄影因素。完整40ID压力下主候选Top-1为99／120、Top-5为119／120；新域阈值0.8707458695890389时C10／W1／U109、未知FA5／120。匹配20ID两组分别C9／W0／U51、C1／W0／U59，未知FA5／120、0／120；未知查询被重复使用，不相加当新样本。排序改善没有自动变成高覆盖的可靠身份找回。

{scores}用既有特征比较绝对余弦、不同牛号间隔和距离比。主seed26在校准组正确接受10／7／9，因此预先规则仍选绝对余弦；虽有开发组间隔／距离比表现较好，也未事后换成主方法。21阈值共同冻结在开发计算前，84条件／13860决定独立复算，未知全0组不认领总体零风险。此前540图及120ID现均属开发材料，未来20候选及保留日期未开启。

{ncnn}保存全部630对特征，1260开发决定一致；校准240决定中1个端点接受变化保留，不移动阈值。630次Torch和630次NCNN正式前向、1次可观测Python追踪单列，转换器内部额外探针未计量，不能给出整个转换精确总前向。

{board}在真实Cortex-A9执行97图＋2预热，97输入hash和120保留决定一致。纯网络平均{arm['mean_network_ms']:.2f}ms、P95 {arm['P95_network_ms']:.2f}ms，7张Cows仅作实现锚点；没有并发O8检测或完整Cows板端准确率测试。新权重在独立目录保留，默认encoder和O8未替换。输入传输中断与采集Path类型错误均保留，已核验前缀续传并修复采集，模型实验只运行一次。

'''
assert text.count('## 4. 数据还需要怎样补')==1;text=text.replace('## 4. 数据还需要怎样补',newsection+'## 4. 数据还需要怎样补',1)
text=text.replace('当前模型暴露高错误接受。余下缺口','适配前旧C暴露高错误接受，后续新域训练改善排序却仍低覆盖。余下缺口',1)
text=text.replace('原MultiCam研究及新Cows2021 540图／120ID评价，已有完整失败结果','原MultiCam研究、Cows540图／120ID开发及新16ID训练，已保留全部取舍',1)
oldstep='2. 公开身份来源核查和540图评价已完成，当前C错误接受仍高；优先冻结按目标图库规模校准／评价的协议，再比较身份训练覆盖与拒识策略，保留新的最终牛号。COLO50图与这次240评价查询不作阈值或seed调参集；94的检测缺口和103的确认损失分别保留。'
newstep='2. 新域六次训练、三种拒识分数和新权重ARM准入已完成；保留主seed26及校准选出的绝对余弦，不因开发结果替换。下一步固定与目标图库规模一致的正式评价和系统负载，模型／方法／阈值冻结后才开启未来20候选。现有Cows120ID和COLO50图均作为已见开发／压力材料，不能再包装成未见最终测试；94检测缺口与103确认损失继续分别保留。'
assert text.count(oldstep)==1;text=text.replace(oldstep,newstep)
oldstep='3. 同负载CPU分配控制现已完成：共享后台接近5FPS且身份最长约2秒，但仍迟到和少计；固定后台CPU1未改善整体取舍，不采用。下一步回到真实通行触发的按需抓拍，明确前台迟到与身份完成要求，保留PNG／NPZ记录开销并逐项计时，不将固定任务当真实触发。'
newstep='3. 同负载CPU分配控制已完成，两个CPU限制策略均未全局采用。新编码器已在板上通过97图实现核验，下一步在独立目录以同模型／同照片负载比较新旧候选，再接回真实通行触发；同时报告前台迟到、计数及后台完成，不把纯网络144.12ms当完整后台等待。'
assert text.count(oldstep)==1;text=text.replace(oldstep,newstep)
a=text.index('本轮新增身份Slurm作业130743');b=text.index('\n\n总体研究目标继续',a)
text=text[:a]+'本轮新域训练六条件1800正式更新、3780评价图像前向及21拒识阈值／84开发条件全部完成并独立复算。训练130777数组与评价130837、转换130863均终态；失败评价130835发生在特征前向前，CRLF提交拒绝与采集Path错误均保留。630图转换、97正式＋2预热实机和全部原始结果完整取回；1260开发决定、240校准决定（含1个端点变化）与板上120决定分别核对。默认encoder和O8未改，板内服务及锁终态核查通过，eth0载波仍0。未来20候选和03-05至03-11像素仍关闭。'+text[b:]
path.write_text(text,encoding='utf-8')
value={'status':'FIVE_ENTRYPOINTS_INTEGRATED_DOMAIN_TRAINING_REJECTION_NCNN_AND97_ARM_WITH_V13_SNAPSHOTS','created_UTC':datetime.now(timezone.utc).isoformat(),
       'previous_files_and_snapshots':snapshots,'current_entrypoints':[{'path':str(p),'sha256':sha(p)}for p in paths],'latest_paragraph':latest,'whole_goal_complete':False}
target=ROOT/'results/entrypoint_update_20261030_v14.json';assert not target.exists();target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':value['status'],'entrypoints':len(paths)},ensure_ascii=False))
