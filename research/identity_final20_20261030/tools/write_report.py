from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
v=load(ROOT/'results/independent_verification.json');s=load(ROOT/'delivery/results/evaluation/summary.json');a=load(ROOT/'results/archive_verification.json');e=load(ROOT/'protocol/execution_v1.json');first=load(ROOT/'evidence/first_final_ID_pixel_request_gate.json');outcomes=load(ROOT/'delivery/results/evaluation/all_outcomes.json');pairs=load(ROOT/'delivery/results/evaluation/paired_ID_differences.json')
assert v['decisions']==480 and v['model_image_forwards']==180
report=f'''# 20个保留身份评价：排序提高，自动接受覆盖率仍低

2026年10月30日。**新域编码器在本次10个已登记身份的30张跨日期查询中，Top-1为30／30；固定主阈值只正确接受3张、拒绝27张。** 旧编码器为Top-1 22／30、正确接受10张、误赋号2张；30张未知查询的误接受旧3、新0。这个结果支持保留新特征的排序方向，仍不支持可靠自动找回牛号或全局替换默认模型。

## 这次检验了什么

沿用[预先计划](计划与验收.md)、[名单与四个10ID校准阈值](protocol/run_v1.json)和[执行冻结](protocol/execution_v1.json)：保留20个Cows作者身份，按此前已存顺序前10个注册、后10个未知，身份没有按结果重选。注册每牛3参考、查询每牛3图，注册日早于查询至少7天，日期均不晚于03-04。输入共90图：30图库、30已登记查询、30未知查询。

主候选仍为预先指定C_domain_seed26末轮权重，比较对象为适配前旧C，绝对余弦＋每ID最高参考分数。两模型均在匹配10ID的既有校准特征上预先选阈值；第一组为主工作点，第二组及历史阈值均作附录，不按最终结果改选。

本次身份在Cows命名空间内，与新域16个训练身份及此前120个开发身份互斥。场景仍相同，部分身份裁剪所对应的检测原图已经被项目使用；跨2020／2023真实物理牛映射未知。这里验证身份组件的保留ID，不称整个项目完全未见像素、跨牧场或端到端通行测试，也不等于复现作者原始训练／测试划分。

## 主工作点的全部结果

| 模型 | 已登记Top-1／30 | 正确接受C／30 | 误赋号W／30 | 拒绝U／30 | 未知误接受FA／30 |
|---|---:|---:|---:|---:|---:|
'''
for r in v['main_outcomes']:report+=f"| {r['model']} | {r['known_Top1']} | {r['C']} | {r['W']} | {r['U']} | {r['unknown_FA']} |\n"
report+='''
新模型的3个正确接受是3张查询，来自作者ID034的2张及ID059的1张，不能写成找回3头不同奶牛或3次完整通行。旧模型3次未知误接受全部来自未知ID026，也不能当成3头独立未知牛。新模型正确接受覆盖为3／30（10%），其余27张虽Top-1正确，仍被原先固定的拒识门限拒绝。

新模型未知误接受0／30、已登记误赋号0／30都只是这批样本的观察。自动接受的3张没有错误，分母仅3，不能宣传“自动识别准确率100%”。主阈值旧0.8348239883357427、新0.8304473380979187，未因新模型全部排序正确而降低；未知样本与注册查询各30张，接受样本错误比例也受这个混合比例影响。

![主结果：候选排名与固定阈值接受](<'''+(ROOT/'results/figures_v2/final20_primary.png').as_posix()+'''>)

图的[SVG源文件](results/figures_v2/final20_primary.svg)可用于后续论文排版。左侧是第一候选正确数，右侧是相同查询的自动接受／拒绝。绘图仅使用已冻结结果，没有新增模型前向；初版图例与脚注重叠，原文件保留，第二版只修布局。

## 全部八个固定工作点

| 模型 | 工作点 | 阈值 | C／W／U | 未知FA／30 |
|---|---|---:|---|---:|
'''
for r in outcomes:report+=f"| {r['model']} | {r['policy']} | {r['threshold']:.9f} | {r['C']}／{r['W']}／{r['U']} | {r['unknown_FA']} |\n"
report+='''
主工作点与其他三个工作点的地位在首次像素请求前已确定。`stability_cal10_fold1`使用另一批10个既有校准身份，`legacy_MultiCam`为原阈值，`prior_cal20`为此前20ID校准阈值；这些结果均保留，没有将附录改成主方法。某些阈值只差最后一位浮点，完整数值在JSON中，不按显示的小数位重新计算。

## 按身份统计与可解释范围

30张已登记查询仅来自10个ID，未知查询也仅10个ID。采用2000次按ID重采样，新旧同ID配对；不把同牛3张图当3个独立身份。主工作点的新减旧结果如下，单位为百分点。

| 指标 | 观察差 | 按ID重采样95%范围 |
|---|---:|---|
'''
labels={'Top1':'Top-1正确','C':'正确接受','W':'误赋号','U':'拒绝','FA':'未知误接受'}
for r in pairs:
 if r['policy']=='primary_cal10_fold0':report+=f"| {labels[r['metric']]} | {r['mean_difference']*100:+.2f} | [{r['percentile95'][0]*100:+.2f}, {r['percentile95'][1]*100:+.2f}] |\n"
report+='''
这些范围描述本批身份间的变动，样本小、来源同场景，不能外推为任意牧场保证。新模型Top-1全对和零误接受使相应经验bootstrap区间退化为[1,1]、[0,0]；这不是总体100%正确或总体零风险的证据。全部8组按ID结果和20项新旧配对均已复算，见[按身份统计](delivery/results/evaluation/per_ID_intervals.json)与[配对差](delivery/results/evaluation/paired_ID_differences.json)。

作者提供的是已裁好的身体图；没有计入检测、抓拍或通行漏失，M=0只表示本组件90个规定输入齐全。本次没有新的192／256／320检测成绩、真实RFID关联、板端速度或原视频12头的永久身份答案。

## 来源、数值与完整复核

执行冻结时间为'''+e['created_UTC']+'''，首次保留身份像素请求门禁为'''+first['created_UTC']+'''。固定协议SHA为`'''+e['protocol_sha256']+'''`，执行SHA为`'''+s['execution_sha256']+'''`。两套权重、输入名单、四工作点、推理／统计／归档代码均先冻结，未按新像素修改。

90张原JPEG总3,058,770字节，官方大小、CRC、RGB完整解码均通过，全部保留；与此前540张开发和457张训练图没有完全相同的像素重复，90图内也无完全重复。没有用其他照片替换困难样本。来源与作者标签范围见[身份来源核查](../cows2021_identity_intake_20261030/身份来源核查与跨日期评价准入.md)。

CPU Slurm作业130877在cu03完成0:0，耗时7秒，两模型各90图，共180图像前向／16次批调用，无预热、训练或板端前向。所有实际输入hash、6份完整tensor锚点和180份raw／归一化特征保存。报告中的耗时是该CPU作业，不是PYNQ-Z2身份网络速度。

完整原始包为'''+f"{a['archive_bytes']:,}"+'''字节、128成员／127清单文件，SHA为`'''+a['archive_sha256']+'''`，包括全部90张原JPEG，已完整取回并逐项核对。独立程序重算90输入、180原始特征归一化、1200个ID分数、480条决定、8组按ID区间和20项配对，全部通过；复核没有增加模型前向。[完整独立复算](results/independent_verification.json)

8张预先固定源样例及23个事后解释案例已实际查看；解释覆盖全部20个作者ID、新模型全部3个主阈值接受及旧模型全部5个错误接受。这不是60张查询全部逐图人工核对，也不构成新的独立人工身份标注。全部案例：[1](results/retrieval_panels/page1.png) · [2](results/retrieval_panels/page2.png) · [3](results/retrieval_panels/page3.png) · [4](results/retrieval_panels/page4.png) · [5](results/retrieval_panels/page5.png) · [6](results/retrieval_panels/page6.png)。

## 研究决定与下一步

保留新编码器的候选检索方向，默认模型与部署阈值不替换。本次排序收益成立于指定保留ID和10ID图库；正确自动接受由10降至3，说明它尚未解决可靠身份自动找回。候选供人工核对可以作为后续待检验的用途，仍需评价未知牛、人工处理时间和完整事件，不能把这种用途当作已验证结果。

这20个ID的像素与结果现在已经使用；若后续据此改模型或阈值，必须把它们标为已见材料，并另设新证据，不能继续称新方法的未见最终测试。03-05至03-11像素仍未开启。接下来先在PYNQ-Z2对这90图运行两套固定编码器，核对全部检索与拒识决定；出现浮点端点变化要保留，不调整阈值隐藏。再接回真实计数触发的因果抓拍，核对输入、候选和等待。

BLOCKER：整体论文仍缺独立逐事件计数、原视频可靠永久身份对应、同通道真实双向及现场或明确定义回放下的完整系统证据。当前组件结果不能补齐这些分母。

IMPORTANT：保留ID已使用、同场景与跨年身份范围、低覆盖、所有阈值、样本聚类和退化区间均明确；不认领总体零错误、任意牛识别率100%或稳定全链路5FPS。

POLISH：报告、数字、完整归档、源图与案例、统计图布局均已助手自审；原结果与第一版布局保留，程序复算不冒充独立人工评审。
'''
target=ROOT/'保留20身份结果与自动接受限制.md';assert not target.exists();target.write_text(report,encoding='utf-8');print(target)
