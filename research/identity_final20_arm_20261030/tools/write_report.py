from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
v=load(ROOT/'results/independent_verification.json');p=load(ROOT/'protocol/run_v1.json');s=load(ROOT/'delivery/results/record.json')
passed=v['experiment_status']=='BOTH90_ENCODERS180_ARM_FEATURES_AND480_FIXED_DECISIONS_PASS'
lead='两套固定编码器已在真实PYNQ-Z2完成180次正式图像推理及4次预热，480条固定工作点决定与CPU参考一致。'if passed else'两套编码器的实际输出已全部保留，存在未通过的数值、排名或决定关口。'
text=f'''# 同90图PYNQ-Z2身份实现：特征、排名与拒识决定

2026年10月30日。**{lead}** 这核验相同90张已评分照片在ARM上的实现，没有增加新的独立身份测试，也没有检测并发或完整5FPS验证。

## 固定输入与执行

沿用[执行前计划](计划与验收.md)和[固定协议](protocol/run_v1.json)：90张Cows作者身体图，10注册／10未知ID，30张图库、30已登记查询及30未知查询。原CPU模型、身份名单与阈值见[保留20身份评价](../identity_final20_20261030/保留20身份结果与自动接受限制.md)。这些身份已经使用，重复执行不计第二份泛化证据。

旧C与新C_domain_seed26读取各自既有NCNN文件，FP32、单线程，复用已核验的Cortex-A9 VFPv3库。全部90张原JPEG和实际224输入的SHA先于创建网络核对；6份完整输入锚点、两模型全部180份raw／归一化特征、逐图时间及线程mask均保存。板上未导入Torch，不编程PL、不替换O8或默认模型。

## 全部数值与决定

| 核查 | 结果 |
|---|---:|
| 原JPEG与实际输入hash | {v['source_JPEG_and_tensor_hashes_verified']}/90一致 |
| 正式ARM前向／另列预热 | 180／4 |
| 180归一化特征最大绝对差 | {v['maximum_normalized_feature_error']:.9g} |
| 超数值门限图数 | {v['numeric_failed_images']} |
| 120查询Top-1变化 | {v['Top1_changes']} |
| 120查询Top-5顺序变化 | {v['Top5_order_changes']} |
| 完整10ID排名变化（另报） | {v['full_ranking_changes']} |
| 480条固定工作点决定变化 | {v['decision_changes']} |

图库和查询共同使用各自ARM编码器重新计算，没有混用旧／新特征。归一化最大绝对差1e-4、1−dot1e-5沿用既有规则，全部8工作点保持原数值；完整排名变化另报，主门禁为数值、Top-1、Top-5与接受决定。原始浮点值和差异不经舍入、门限放宽或重校准改写。

| 编码器 | 已登记Top-1／30 | 正确C | 误赋号W | 拒绝U | 未知FA／30 |
|---|---:|---:|---:|---:|---:|
'''
for row in v['primary_outcomes']:text+=f"| {row['model']} | {row['known_Top1']} | {row['C']} | {row['W']} | {row['U']} | {row['unknown_FA']} |"+chr(10)
text+='''
主阈值旧C0.8348239883357427、新C0.8304473380979187，均在此前首次像素请求前固定。新模型30／30排名第一正确而自动接受仅3／30的限制仍在；3张接受来自2个作者ID，未知FA0／30不构成总体零风险。本次同图ARM结果不增加牛号数量，也不代表原视频12头的永久身份。

## 设备计时范围

| 编码器（执行顺序） | 测量图数 | tensor→特征均值ms | P95 ms | 最大值ms | 特征最大绝对差 |
|---|---:|---:|---:|---:|---:|
'''
for index,(name,r)in enumerate(v['timings'].items(),1):text+=f"| {index}／{name} | 90 | {r['network_mean_ms']:.2f} | {r['network_P95_ms']:.2f} | {r['network_max_ms']:.2f} | {r['maximum_normalized_ARM_CPU_error']:.9g} |"+chr(10)
text+=f'''
JPEG打开／完整解码／224预处理合计均值{v['JPEG_read_decode_preprocess_mean_ms']:.2f}ms、P95 {v['JPEG_read_decode_preprocess_P95_ms']:.2f}ms。90图先预处理，再旧→新顺序推理；每图完整性SHA读取在计时前发生，因此不称冷文件实验。两网络各2次预热另列，不混入90图均值。

网络计时从已就绪tensor开始，到Python原生编码器返回576维输出；不含相机、JPEG、检测、跟踪、抓拍、检索和完整证据写出。没有交错顺序重复或O8竞争，不能用两均值差证明新旧速度优势，不能换算为完整后台或系统FPS。没有功率、能量或长期稳定性测量。

## 完整结果与设备终态

输入协议SHA为 {s['protocol_sha256']}。结果原包{v['archive_bytes']:,}字节、{v['archive_members']}成员／{v['manifest_files']}清单文件，SHA为 {v['archive_SHA256']}。通过COM6逐块及全包SHA核验，TTY设置恢复；没有改波特率、复位、IP或网络配置。源输入与CPU参考另有本地冻结包绑定，结果包保留全部180份实际原始向量。

[独立复算](results/independent_verification.json)重新读取90张原JPEG，核对tensor、6锚点、180特征的归一化和逐图SHA，再逐ID重算1200分数、120查询排名及480决定，并复算全部时间统计和8组结果。复核新增模型前向0，不由“脚本成功”代替实际数组证据。

[设备终态](delivery/final_board_state.json)及取包后的复查确认本任务进程结束，默认旧encoder、两模型NCNN文件、运行库和O8 SHA保持，锁可用，板内SSH／Jupyter服务正常。eth0载波仍0，当前使用串口，不能称外部网络恢复。全部结果及预先协议保留。

## 研究决定

保持当前两个身份候选和全部阈值，保留新特征排序方向。自动接受覆盖不足、事件身份未知和当前192计数10／人工12是不同的未解决问题。接下来把固定模型接回真实计数触发的因果选图、按需抓拍和后台检索，评价实际照片、前台迟到、任务等待与未解决事件；不能用固定10照片负载取代该链路。

本阶段没有训练或新的独立身份测试，没有现场RFID／相机数据，不改此前CPU结果或默认部署。03-05至03-11保留像素继续关闭。整体论文仍需独立逐事件、可靠事件身份、同通道真实双向及明确系统负载证据。

自审核对输入、权重、实际184次ARM调用、全部原始特征、8工作点、计时范围、归档和设备终态；阶段完成不等于整体研究或发表条件满足。
'''
target=ROOT/'同90图ARM实机一致性与计时范围.md';assert not target.exists();target.write_text(text,encoding='utf-8');print(target)
