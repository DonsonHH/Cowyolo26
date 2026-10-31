from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(label,path):return f'[{label}](<{(PROJECT/path).as_posix()}>)'

directory=PROJECT/'identity_final20_arm_20261030';v=load(directory/'results/final_review.json');assert v['decision_changes']==0 and v['actual_ARM_network_calls']==184
old=load(ROOT/'results/overview_review_20261030_v16.json');main=PROJECT/'研究阶段总结_20261030.md';assert sha(main)==old['document']['sha256']
paths=[main,PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',ROOT/'Review与当前状态.md'];backup=ROOT/'snapshots/overview_v16_before_final20_ARM';backup.mkdir(parents=True,exist_ok=False);snapshots=[]
for p in paths:
 dest=backup/p.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());snapshots.append({'path':str(p),'snapshot':str(dest),'sha256':sha(dest)})
ref=link('同90图两编码器ARM实机核验','identity_final20_arm_20261030/同90图ARM实机一致性与计时范围.md');oldms=v['timings']['old_C']['network_mean_ms'];newms=v['timings']['new_C_domain_seed26']['network_mean_ms']
latest=f'2026年10月30日最新：{ref}已完成180正式＋4预热，90原JPEG／tensor hash、180实际原始特征及480固定决定全部核对。Top-1、Top-5和接受决定与CPU一致，主结果仍旧C22／30及C10／W2／U18／FA3，新C30／30及C3／W0／U27／FA0。纯身份网络均值旧{oldms:.2f}ms、新{newms:.2f}ms，单次旧→新顺序、无检测并发，不认领速度优势或完整5FPS。完整原包已取回并独立复算；两套模型、库、默认encoder及O8未替换。本次是已评分90图的实现复核，不增加独立身份测试；下一步接回真实计数触发抓拍，独立事件与永久身份仍待补。'
for path in paths[1:]:
 s=path.read_text();head,rest=s.split(chr(10),1);rest=rest.lstrip(chr(10));assert rest.startswith('2026年10月30日最新：');rest=rest.replace('2026年10月30日最新：','同日此前保留ID的CPU评价：',1)
 extra=' '+link('第17版总览复核','research_synthesis_20261027/results/overview_review_20261030_v17.json')+'。'if path==ROOT/'Review与当前状态.md'else''
 path.write_text(head+chr(10)*2+latest+extra+chr(10)*2+rest,encoding='utf-8')
s=main.read_text();pos=s.index('2026年10月30日最新：');s=s[:pos]+latest+chr(10)*2+'此前同90图CPU评价：'+s[pos:].replace('2026年10月30日最新：','',1)
row='| 保留ID身份组件CPU评价 | 10注册＋10未知，90图；新Top-1 30／30、旧22／30 | 新主工作点C3／W0／U27、未知FA0／30；低覆盖且非现场全链路 |'
assert s.count(row)==1;s=s.replace(row,'| 保留ID组件与ARM一致性 | 10注册＋10未知、90图；180ARM特征与480决定同CPU | 新Top-1 30／30但C3／W0／U27、FA0／30；仍低覆盖 |',1)
section=f'''### 3.11 同90图ARM完整实现核验已经完成

{ref}冻结同一90JPEG、两模型及全部八工作点，在Cortex-A9运行旧C90图＋2预热、新C90图＋2预热。图库与查询共同使用各自ARM特征，所有90输入hash、180raw／归一化特征、1200身份分数与480决定独立复算，Top-1／Top-5／接受与CPU一致。完整10ID排序变化另存，没有重调阈值。

| 编码器 | 正式图数 | 网络均值ms | P95 ms | CPU归一化特征最大差 |
|---|---:|---:|---:|---:|
'''
for name,r in v['timings'].items():section+=f"| {name} | 90 | {r['network_mean_ms']:.2f} | {r['network_P95_ms']:.2f} | {r['maximum_normalized_ARM_CPU_error']:.9g} |"+chr(10)
section+=f'''
计时从已就绪224tensor到576维特征返回，JPEG解码／预处理另列；先完整处理90图再旧→新顺序运行，无O8检测并发，没有交错重复，不能由均值差认领模型加速或全链路5FPS。CPU评价中的低接受覆盖仍保留，硬件一致性没有增加可可靠自动找回的牛号。

原始包{v['archive_bytes']:,}字节、{v['archive_members']}成员／{v['manifest_files']}清单文件完整取回，全部输入锚点、raw、原始数值和终态保留。父任务与采集结束，默认encoder、两模型／库及O8、锁和板内服务均复查。新模型仍为研究候选，不全局替换。相同90图的CPU与ARM不是两次独立测试，03-05至03-11像素继续关闭。

'''
marker='## 4. 数据还需要怎样补';assert s.count(marker)==1;s=s.replace(marker,section+marker,1)
s=s.replace('下一步将同90图上板只验证实现和数值，不把重复执行算第二个独立测试。','随后同90图ARM实现与数值核验已经完成（见3.11），不把重复执行算第二个独立测试。',1)
oldstep='2. 保留20ID的固定CPU评价已经完成，排序提高而自动接受仍少。保持两编码器、全部阈值和输入不变，下一步对这90图做PYNQ-Z2真实ARM数值与决定核对；任何端点变化如实保留，不改阈值隐藏。已评分20ID不再作为后续改方法的未见证据，03-05至03-11日期继续保留。'
newstep='2. 保留20ID的固定CPU评价及同90图ARM完整核验都已完成，输入、特征、排名与全部决定一致。保持两编码器及阈值，不用完美排名掩盖3／30自动接受覆盖；任何后续方法改动需新独立材料。已评分20ID不再称新方法未见测试，03-05至03-11日期继续保留。';assert s.count(oldstep)==1;s=s.replace(oldstep,newstep)
start=s.index('本轮保留20身份的90图固定评价完成');end=s.index(chr(10)*2+'总体研究目标继续',start)
s=s[:start]+f'本轮同90图真实ARM核验完成180正式＋4预热，CPU参考沿用此前结果，新增CPU前向／训练／PL前向0。90输入、6锚点、180特征、1200ID分数和480决定独立复算通过，Top-1／Top-5／接受与CPU一致。完整原始包和设备终态核查完成，默认两模型／库与O8保持，eth0载波仍0；本轮无检测并发或全链路5FPS测试。此前保留ID的低覆盖结论不变，下一步接回真实通行触发和因果抓拍，独立事件及可靠永久身份仍缺。'+s[end:]
main.write_text(s,encoding='utf-8')
value={'status':'FIVE_ENTRYPOINTS_UPDATED_WITH_SAME90_ARM_CONSISTENCY_AND_V16_SNAPSHOTS','created_UTC':datetime.now(timezone.utc).isoformat(),'previous_files_and_snapshots':snapshots,'current_entrypoints':[{'path':str(p),'sha256':sha(p)}for p in paths],'whole_goal_complete':False};target=ROOT/'results/entrypoint_update_20261030_v17.json';assert not target.exists();target.write_bytes(json.dumps(value,ensure_ascii=False,indent=2).encode()+bytes([10]));print(json.dumps({'status':value['status'],'report_lines':len(s.splitlines())}))
